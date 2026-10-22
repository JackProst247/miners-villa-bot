CREATE SCHEMA IF NOT EXISTS bot_v3;
CREATE TABLE IF NOT EXISTS bot_v3.people (
 sid text PRIMARY KEY, paused boolean NOT NULL DEFAULT false,
 epoch bigint NOT NULL DEFAULT 0, form jsonb NOT NULL DEFAULT '{}',
 profile jsonb NOT NULL DEFAULT '{}',
 customer text NOT NULL DEFAULT 'unknown'
);
CREATE TABLE IF NOT EXISTS bot_v3.jobs (
 key text PRIMARY KEY, kind text NOT NULL, sid text NOT NULL,
 payload jsonb NOT NULL, status text NOT NULL DEFAULT 'pending',
 attempts integer NOT NULL DEFAULT 0, available timestamptz NOT NULL DEFAULT now(),
 created timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS jobs_pending ON bot_v3.jobs(status,available);
CREATE TABLE IF NOT EXISTS bot_v3.messages (
 id bigserial PRIMARY KEY, sid text NOT NULL, text text NOT NULL,
 interests jsonb NOT NULL DEFAULT '[]', customer text NOT NULL,
 created timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_dates ON bot_v3.messages(created);
CREATE TABLE IF NOT EXISTS bot_v3.requests (
 id text PRIMARY KEY, sid text NOT NULL, kind text NOT NULL, data jsonb NOT NULL,
 delivered boolean NOT NULL DEFAULT false, completed boolean NOT NULL DEFAULT false,
 taken boolean NOT NULL DEFAULT false,
 created timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS bot_v3.settings (key text PRIMARY KEY, value text NOT NULL);
-- Private schema: never expose client information through Supabase's public API.
REVOKE ALL ON SCHEMA bot_v3 FROM PUBLIC;
