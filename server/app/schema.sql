-- Phase 0: minimal schema
-- No partitioning yet — that comes in Phase 1.1

CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    site_id UUID NOT NULL,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    method VARCHAR(10) NOT NULL,
    path TEXT NOT NULL,
    status SMALLINT NOT NULL,
    ua TEXT NOT NULL DEFAULT '',
    ip_hash VARCHAR(64),
    headers JSONB DEFAULT '{}',
    beacon_seen BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_site_ts ON events (site_id, ts DESC);
