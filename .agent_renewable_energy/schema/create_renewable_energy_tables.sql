-- =============================================================================
-- Renewable Energy & Battery Tech Tracker -- Database Schema
-- =============================================================================
-- Compatible with PostgreSQL and SQLite.
-- Every record carries source_url, source_type, and source_confidence.

-- ---------------------------------------------------------------------------
-- companies
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    company_id   TEXT PRIMARY KEY,
    ticker       TEXT,
    exchange     TEXT,
    company_name TEXT NOT NULL,
    market_cap_bucket TEXT,   -- nano / micro / small / mid / large
    energy_type  TEXT,        -- solar / wind / battery / storage / multi
    country      TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- energy_projects
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS energy_projects (
    project_id    TEXT PRIMARY KEY,
    company_id    TEXT NOT NULL REFERENCES companies(company_id),
    project_name  TEXT NOT NULL,
    project_type  TEXT NOT NULL,   -- solar / wind / battery / storage
    capacity_mw   REAL,
    location_state TEXT,
    latitude      REAL,
    longitude     REAL,
    stage         TEXT,            -- development / construction / operational
    expected_cod  TEXT,            -- DATE as TEXT for SQLite compatibility
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- interconnection_events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS interconnection_events (
    event_id          TEXT PRIMARY KEY,
    project_id        TEXT NOT NULL REFERENCES energy_projects(project_id),
    queue_id          TEXT,
    iso_region        TEXT,        -- PJM / MISO / CAISO / ERCOT / SPP / NYISO / ISONE
    status            TEXT,
    milestone_date    TEXT,        -- DATE as TEXT for SQLite compatibility
    source_url        TEXT,
    source_type       TEXT,
    source_confidence TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- ppa_agreements
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ppa_agreements (
    ppa_id          TEXT PRIMARY KEY,
    project_id      TEXT NOT NULL REFERENCES energy_projects(project_id),
    offtaker        TEXT,
    contract_type   TEXT,         -- physical / virtual / sleeved
    price_per_mwh   REAL,
    duration_years  INTEGER,
    announced_date  TEXT,         -- DATE as TEXT for SQLite compatibility
    source_url      TEXT,
    source_confidence TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- ira_credits
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ira_credits (
    credit_id            TEXT PRIMARY KEY,
    project_id           TEXT NOT NULL REFERENCES energy_projects(project_id),
    credit_type          TEXT,    -- ITC / PTC / 45X / 45V / 48C
    estimated_value_usd  REAL,
    certification_status TEXT,
    source_url           TEXT,
    source_confidence    TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- doe_loans
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doe_loans (
    loan_id        TEXT PRIMARY KEY,
    company_id     TEXT NOT NULL REFERENCES companies(company_id),
    program        TEXT,          -- LPO / ATVM / Title_XVII
    amount_usd     REAL,
    status         TEXT,
    announced_date TEXT,          -- DATE as TEXT for SQLite compatibility
    source_url     TEXT,
    source_confidence TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- project_scores
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS project_scores (
    score_id              TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES energy_projects(project_id),
    interconnection_score REAL,
    offtake_score         REAL,
    credit_score          REAL,
    financial_score       REAL,
    overall_score         REAL,
    scored_at             TEXT DEFAULT (datetime('now'))
);
