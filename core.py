"""Pure conversation rules. No credentials, network, or database side effects."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Ulaanbaatar')
PHONES = '9430-7017, 9431-7017, 9434-7017'
KINDS = {
    'email': 'И-мэйл бүртгүүлэх', 'engineer': 'Инженертэй уулзах',
    'viewing': 'Байр үзэх', 'barter': 'Бартерын санал',
    'human': 'Ажилтантай харилцах', 'complaint': 'Гомдол',
    'progress': 'Барилгын явц тодруулах', 'services': 'Үйлчилгээний талбай',
    'contract': 'Гэрээ / захиалга',
}
QUESTIONS = {
    'name': 'Гэрээ байгуулсан хүний овог, нэрийг бичнэ үү.',
    'phone': 'Гэрээнд бүртгэлтэй утасны дугаараа бичнэ үү.',
    'email': 'Бүртгүүлэх и-мэйл хаягаа бичнэ үү.',
    'contract': 'Гэрээний дугаараа бичээрэй. Санахгүй бол «санахгүй» гэж бичиж болно.',
    'details': 'Хүсэлтээ товч тайлбарлаж өгнө үү.',
    'time': 'Танд боломжтой өдөр, цагаа бичээрэй. Тодорхойгүй бол «тохиролцоно» гэж бичиж болно.',
}

def norm(text):
    return re.sub(r'\s+', ' ', text.lower().replace('ү', 'у').replace('ө', 'о')).strip()

def has(text, words):
    return any(norm(w) in norm(text) for w in words)

def classify(text):
    if has(text, ['и-мэйл', 'имэйл', 'мэйл', 'email', 'e-mail', 'mail хаяг']): return 'email'
    if has(text, ['инженер', 'injener', 'өрөөний хуваалт', 'хана өөрчл']): return 'engineer'
    if has(text, ['гомдол', 'gomdol']): return 'complaint'
    if has(text, ['ажилтантай', 'админ', 'менежертэй', 'huntei', 'ajiltan', 'admin', 'managertei']): return 'human'
    if has(text, ['дулаан', 'дотор засал', 'барилгын явц', 'шатандаа', 'шатанда', 'shatand', 'ашиглалт', 'hezee ashiglalt']): return 'progress'
    if has(text, ['бартер', 'barter', 'машинаа өг', 'байраа өг', 'оролцуул']): return 'barter'
    if has(text, ['үйлчилгээний талбай', 'uilchilgeenii talbai']): return 'services'
    if has(text, ['очиж үз', 'үзэж болох', 'үзэх', 'ochij', 'ochih', 'уулзалт']): return 'viewing'
    if has(text, ['гэрээ байгуул', 'захиалга өг', 'захиалмаар']): return 'contract'
    return 'general'

def tags(text):
    interests = []
    if has(text, ['мульт', 'mult', 'мулт']): interests.append('mult')
    if has(text, ['таун', 'town', 'taun']): interests.append('town')
    if has(text, ['үйлчилгээний талбай', 'uilchilgeenii talbai']): interests.append('services')
    if has(text, ['захиалагч', 'гэрээтэй', 'гэрээ байгуулсан', 'захиалсан']): customer = 'existing'
    elif interests: customer = 'prospect'
    else: customer = 'unknown'
    return interests, customer

def email_value(text):
    value = text.strip()
    return value if len(value) <= 254 and re.fullmatch(r'[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+', value) else None

def phone_value(text):
    value = re.sub(r'[\s()-]', '', text.strip())
    value = re.sub(r'^\+976', '', value)
    return value if re.fullmatch(r'[689]\d{7}', value) else None

def collect(form, text):
    """Returns updated form and next question, or None when complete."""
    form = dict(form)
    fields = dict(form.get('fields', {}))
    step = form.get('step')
    if step:
        value = text.strip()
        if step == 'email':
            value = email_value(text)
            if not value: return form, 'И-мэйл хаягийн бичлэгийг шалгаад дахин бичээрэй. Жишээ: name@example.com'
        elif step == 'phone':
            value = phone_value(text)
            if not value and form['kind'] != 'email' and has(text,['өгөхгүй','боломжгүй','чатаар','байхгүй']):
                value = 'Дугаар өгөөгүй — чатаар холбогдоно'
            if not value: return form, 'Утасны дугаар дутуу эсвэл буруу бичигдсэн байна. Монголын 8 оронтой дугаараа дахин бичээрэй.'
        elif step == 'name' and (len(value.split()) < 2 or any(c.isdigit() for c in value)):
            return form, 'Гэрээ байгуулсан хүний овог болон нэрийг хамт бичээрэй.'
        elif step == 'contract' and has(value, ['санахгүй', 'мэдэхгүй', 'байхгүй', 'sanahgui', 'medehgui']):
            value = 'Санахгүй — овог нэр, утсаар тулгаж шалгана'
        if not value or len(value) > 1500: return form, 'Мэдээллээ 1500 тэмдэгтээс богино бичээрэй.'
        fields[step] = value
    order = ['name', 'phone', 'email', 'contract'] if form['kind'] == 'email' else ['phone']
    if form['kind'] in ('viewing', 'engineer'): order += ['time']
    for field in order:
        if not fields.get(field):
            return {**form, 'fields': fields, 'step': field}, QUESTIONS[field] if field != 'phone' or form['kind'] == 'email' else 'Холбогдох утасны дугаараа бичнэ үү.'
    return {**form, 'fields': fields, 'step': None}, None

def delivered_text(kind, now=None):
    now = (now or datetime.now(TZ)).astimezone(TZ)
    text = 'Таны ' + KINDS[kind].lower() + ' хүсэлтийг хариуцсан ажилтанд дамжууллаа.'
    if not 9 <= now.hour < 18:
        text += ' Манай ажилтнууд өдөр бүр 09:00–18:00 цагт ажилладаг тул дараагийн ажлын цагаар хариу өгнө.'
    elif kind in ('engineer', 'viewing'):
        text += ' Уулзалтын цагийг ажилтан тантай тохирно.'
    return text

def report_window(now):
    end = now.astimezone(TZ).replace(hour=18, minute=0, second=0, microsecond=0)
    if now < end: end -= timedelta(days=1)
    return end - timedelta(days=1), end

def safe_answer(text, knowledge):
    """Approved facts only; no model-generated commercial promises."""
    if has(text, ['утас', 'дугаар', 'holboo', 'contact']): return f'Борлуулалтын утас: {PHONES}. Өдөр бүр 09:00–18:00 цагт ажиллана.'
    if has(text, ['үнэ', 'une', 'үлдсэн', 'үлдэгдэл', 'uldsen', 'uld egdel']):
        return 'Одоогийн үнэ, үлдэгдлийг ажилтнаар шалгуулж өгье. «Ажилтантай холбогдох» гэж бичээрэй.'
    if has(text, ['байршил', 'хаана', 'hayag', 'bairshil']): return knowledge['location']
    if has(text, ['сайн', 'snu', 'hello', 'hi']) and len(text) < 35:
        return 'Сайн байна уу! Би Miners Villa-ийн цахим туслах Мина. Та шинэ байр сонирхож байна уу, эсвэл захиалсан байрныхаа талаар лавлах уу?'
    if has(text, ['мульт', 'mult', 'мулт', 'таун', 'town', 'taun', 'загвар', 'сонголт']):
        return knowledge['models']
    if has(text, ['баярлалаа', 'bayarlalaa']): return 'Баярлалаа. Өөр тодруулах зүйл байвал бичээрэй.'
    return 'Таны асуултыг зөв ойлгохын тулд арай дэлгэрэнгүй бичиж өгнө үү. Хэрэв ажилтнаар тодруулах бол «ажилтантай холбогдох» гэж бичээрэй.'
