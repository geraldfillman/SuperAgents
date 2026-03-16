-- Run history table for dashboard state persistence.
-- Tracks every agent task execution for monitoring and analytics.

CREATE TABLE IF NOT EXISTS run_history (
    run_id           TEXT PRIMARY KEY,
    agent_name       TEXT NOT NULL,
    workflow_name    TEXT NOT NULL,
    task_name        TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    started_at       TIMESTAMP,
    completed_at     TIMESTAMP,
    duration_seconds REAL,
    input_scope      TEXT,            -- JSON array of tickers/assets
    outputs          TEXT,            -- JSON {records_written, files_written}
    findings         TEXT,            -- JSON array per project.md section 10
    blockers         TEXT,            -- JSON array
    next_actions     TEXT,            -- JSON array
    model_used       TEXT,
    model_cost_usd   REAL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_run_history_agent ON run_history(agent_name);
CREATE INDEX IF NOT EXISTS idx_run_history_status ON run_history(status);
CREATE INDEX IF NOT EXISTS idx_run_history_started ON run_history(started_at);
