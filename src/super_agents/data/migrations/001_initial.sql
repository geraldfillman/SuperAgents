-- 001_initial.sql
-- Unified store initial schema for Super_Agents dashboard

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ---------------------------------------------------------------------------
-- signals — from Crucix data hub (migrated from SignalStore)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS signals (
    signal_id   TEXT PRIMARY KEY,
    source      TEXT NOT NULL,
    topic       TEXT NOT NULL,
    payload     TEXT NOT NULL DEFAULT '{}',
    timestamp   TEXT NOT NULL,
    confidence  TEXT NOT NULL DEFAULT 'secondary',
    sectors     TEXT NOT NULL DEFAULT '[]',
    processed   INTEGER NOT NULL DEFAULT 0,
    sector      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_signals_topic     ON signals(topic);
CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);
CREATE INDEX IF NOT EXISTS idx_signals_processed ON signals(processed);
CREATE INDEX IF NOT EXISTS idx_signals_sector    ON signals(sector);

-- ---------------------------------------------------------------------------
-- runs — agent execution history (migrated from JSON files in data/runs/)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    agent        TEXT NOT NULL,
    skill        TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'unknown',
    started_at   TEXT,
    completed_at TEXT,
    duration_sec REAL,
    record_count INTEGER DEFAULT 0,
    error        TEXT,
    payload      TEXT NOT NULL DEFAULT '{}',
    sector       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_runs_agent      ON runs(agent);
CREATE INDEX IF NOT EXISTS idx_runs_status     ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_sector     ON runs(sector);

-- ---------------------------------------------------------------------------
-- findings — cross-sector discoveries
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings (
    finding_id   TEXT PRIMARY KEY,
    agent        TEXT NOT NULL,
    title        TEXT NOT NULL DEFAULT '',
    summary      TEXT NOT NULL DEFAULT '',
    severity     TEXT NOT NULL DEFAULT 'info',
    finding_time TEXT NOT NULL,
    source_url   TEXT,
    source_type  TEXT,
    confidence   TEXT NOT NULL DEFAULT 'secondary',
    payload      TEXT NOT NULL DEFAULT '{}',
    sector       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_agent        ON findings(agent);
CREATE INDEX IF NOT EXISTS idx_findings_severity     ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_finding_time ON findings(finding_time);
CREATE INDEX IF NOT EXISTS idx_findings_sector       ON findings(sector);

-- ---------------------------------------------------------------------------
-- events — calendar / catalyst events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    agent       TEXT NOT NULL DEFAULT '',
    event_type  TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    event_date  TEXT,
    payload     TEXT NOT NULL DEFAULT '{}',
    sector      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_event_date ON events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_sector     ON events(sector);

-- ---------------------------------------------------------------------------
-- metrics — LLM usage, cost, token counts
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS metrics (
    metric_id    TEXT PRIMARY KEY,
    agent        TEXT NOT NULL DEFAULT '',
    model        TEXT NOT NULL DEFAULT '',
    prompt_tokens   INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost_usd     REAL DEFAULT 0.0,
    run_id       TEXT,
    recorded_at  TEXT NOT NULL,
    payload      TEXT NOT NULL DEFAULT '{}',
    sector       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_metrics_agent       ON metrics(agent);
CREATE INDEX IF NOT EXISTS idx_metrics_model       ON metrics(model);
CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON metrics(recorded_at);
CREATE INDEX IF NOT EXISTS idx_metrics_sector      ON metrics(sector);

-- ---------------------------------------------------------------------------
-- agent_status — last-known state per agent
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS agent_status (
    agent        TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'unknown',
    last_run_id  TEXT,
    last_run_at  TEXT,
    last_error   TEXT,
    skill_count  INTEGER DEFAULT 0,
    run_count    INTEGER DEFAULT 0,
    payload      TEXT NOT NULL DEFAULT '{}',
    sector       TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_agent_status_sector ON agent_status(sector);

-- ---------------------------------------------------------------------------
-- schema_migrations — track applied migrations
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     TEXT PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_migrations (version) VALUES ('001_initial');
