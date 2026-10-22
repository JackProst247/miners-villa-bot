import os
import json
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

@contextmanager
def db():
    with psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=10,
                         row_factory=dict_row) as connection:
        yield connection

def initialize():
    from pathlib import Path
    with db() as c:
        c.execute(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))

def state(sid):
    with db() as c:
        c.execute('INSERT INTO bot_v3.people(sid) VALUES (%s) ON CONFLICT DO NOTHING', (sid,))
        return c.execute('SELECT * FROM bot_v3.people WHERE sid=%s', (sid,)).fetchone()

def save(sid, form=None, paused=None, customer=None, expected_epoch=None, profile=None):
    state(sid)
    with db() as c:
        current=c.execute('SELECT epoch,paused FROM bot_v3.people WHERE sid=%s FOR UPDATE',(sid,)).fetchone()
        if expected_epoch is not None and (current['epoch']!=expected_epoch or current['paused']): return False
        if form is not None:
            c.execute('UPDATE bot_v3.people SET form=%s::jsonb WHERE sid=%s', (json.dumps(form, ensure_ascii=False), sid))
        if paused is not None:
            c.execute('UPDATE bot_v3.people SET paused=%s, epoch=epoch+1 WHERE sid=%s', (paused, sid))
        if customer:
            c.execute('UPDATE bot_v3.people SET customer=%s WHERE sid=%s', (customer, sid))
        if profile is not None:
            c.execute('UPDATE bot_v3.people SET profile=profile || %s::jsonb WHERE sid=%s',(json.dumps(profile,ensure_ascii=False),sid))
    return True

def enqueue(key, kind, sid, payload):
    with db() as c:
        c.execute('INSERT INTO bot_v3.jobs(key,kind,sid,payload) VALUES(%s,%s,%s,%s::jsonb) ON CONFLICT DO NOTHING',
                  (key,kind,sid,json.dumps(payload,ensure_ascii=False)))

def audit(sid, text, interests, customer):
    with db() as c:
        c.execute('INSERT INTO bot_v3.messages(sid,text,interests,customer) VALUES(%s,%s,%s::jsonb,%s)',
                  (sid,text,json.dumps(interests),customer))

def recent(sid):
    with db() as c:
        rows = c.execute('SELECT text FROM bot_v3.messages WHERE sid=%s ORDER BY id DESC LIMIT 6',(sid,)).fetchall()
        return [r['text'] for r in reversed(rows)]
