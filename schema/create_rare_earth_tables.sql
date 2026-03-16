-- =============================================================================
-- Rare Earth & Critical Minerals Tracker -- Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

-- Table 1: companies
CREATE TABLE IF NOT EXISTS re_companies (
    company_id        TEXT PRIMARY KEY,
    ticker            TEXT NOT NULL,
    exchange          TEXT,            -- Nasdaq, NYSE, NYSE American, OTCQB, OTCQX, TSX, ASX
    company_name      TEXT NOT NULL,
    market_cap_bucket TEXT,            -- nano / micro / small / mid
    primary_commodity TEXT,            -- REE / lithium / cobalt / nickel / graphite / manganese / etc.
    country           TEXT DEFAULT 'US',
    source_url        TEXT,
    source_confidence TEXT,            -- primary / secondary / sponsor
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_companies_ticker ON re_companies(ticker);
CREATE INDEX IF NOT EXISTS idx_re_companies_commodity ON re_companies(primary_commodity);

-- Table 2: projects
CREATE TABLE IF NOT EXISTS re_projects (
    project_id      TEXT PRIMARY KEY,
    company_id      TEXT NOT NULL REFERENCES re_companies(company_id),
    project_name    TEXT NOT NULL,
    commodity_type  TEXT,              -- REE / lithium / cobalt / nickel / graphite / manganese
    stage           TEXT,              -- exploration / PEA / PFS / DFS / construction / production
    jurisdiction    TEXT,              -- US-NV, US-WY, CA-ON, AU-WA, etc.
    latitude        REAL,
    longitude       REAL,
    source_url      TEXT,
    source_confidence TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_projects_company ON re_projects(company_id);
CREATE INDEX IF NOT EXISTS idx_re_projects_commodity ON re_projects(commodity_type);
CREATE INDEX IF NOT EXISTS idx_re_projects_stage ON re_projects(stage);

-- Table 3: resource_estimates
CREATE TABLE IF NOT EXISTS re_resource_estimates (
    estimate_id           TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES re_projects(project_id),
    standard              TEXT,         -- NI_43_101 / JORC / S-K_1300
    category              TEXT,         -- measured / indicated / inferred
    tonnes                REAL,
    grade                 REAL,
    contained_metal_tonnes REAL,
    effective_date        DATE,
    source_url            TEXT,
    source_confidence     TEXT,         -- primary / secondary / sponsor
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_estimates_project ON re_resource_estimates(project_id);
CREATE INDEX IF NOT EXISTS idx_re_estimates_standard ON re_resource_estimates(standard);
CREATE INDEX IF NOT EXISTS idx_re_estimates_category ON re_resource_estimates(category);

-- Table 4: permit_events
CREATE TABLE IF NOT EXISTS re_permit_events (
    permit_id         TEXT PRIMARY KEY,
    project_id        TEXT NOT NULL REFERENCES re_projects(project_id),
    permit_type       TEXT,            -- ROD / EIS / DEIS / water / air
    status            TEXT,            -- pending / approved / denied / withdrawn / comment_period
    agency            TEXT,            -- BLM / EPA / USFS / state agency
    event_date        DATE,
    source_url        TEXT,
    source_confidence TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_permits_project ON re_permit_events(project_id);
CREATE INDEX IF NOT EXISTS idx_re_permits_type ON re_permit_events(permit_type);
CREATE INDEX IF NOT EXISTS idx_re_permits_status ON re_permit_events(status);
CREATE INDEX IF NOT EXISTS idx_re_permits_date ON re_permit_events(event_date);

-- Table 5: offtake_agreements
CREATE TABLE IF NOT EXISTS re_offtake_agreements (
    agreement_id          TEXT PRIMARY KEY,
    project_id            TEXT NOT NULL REFERENCES re_projects(project_id),
    counterparty          TEXT,
    commodity             TEXT,
    volume_tonnes_per_year REAL,
    duration_years        INTEGER,
    announced_date        DATE,
    source_url            TEXT,
    source_confidence     TEXT,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_offtake_project ON re_offtake_agreements(project_id);
CREATE INDEX IF NOT EXISTS idx_re_offtake_counterparty ON re_offtake_agreements(counterparty);

-- Table 6: dpa_awards
CREATE TABLE IF NOT EXISTS re_dpa_awards (
    award_id          TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES re_companies(company_id),
    program           TEXT,            -- Title_III / DPA / CMMC
    award_amount_usd  REAL,
    announced_date    DATE,
    source_url        TEXT,
    source_confidence TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_dpa_company ON re_dpa_awards(company_id);
CREATE INDEX IF NOT EXISTS idx_re_dpa_program ON re_dpa_awards(program);
CREATE INDEX IF NOT EXISTS idx_re_dpa_date ON re_dpa_awards(announced_date);

-- Table 7: project_scores
CREATE TABLE IF NOT EXISTS re_project_scores (
    score_id          TEXT PRIMARY KEY,
    project_id        TEXT NOT NULL REFERENCES re_projects(project_id),
    resource_score    INTEGER CHECK(resource_score BETWEEN 0 AND 10),
    permitting_score  INTEGER CHECK(permitting_score BETWEEN 0 AND 10),
    offtake_score     INTEGER CHECK(offtake_score BETWEEN 0 AND 10),
    financial_score   INTEGER CHECK(financial_score BETWEEN 0 AND 10),
    overall_score     REAL,
    scored_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_re_scores_project ON re_project_scores(project_id);
CREATE INDEX IF NOT EXISTS idx_re_scores_overall ON re_project_scores(overall_score);

-- =============================================================================
-- Event history table (never overwrite, always append)
-- =============================================================================
CREATE TABLE IF NOT EXISTS re_event_history (
    history_id   TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL,
    field_name   TEXT NOT NULL,
    old_value    TEXT,
    new_value    TEXT,
    changed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by   TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_re_history_event ON re_event_history(event_id);

-- =============================================================================
-- Financials / Cash Runway
-- =============================================================================
CREATE TABLE IF NOT EXISTS re_financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_cik TEXT REFERENCES re_companies(company_id),
    ticker TEXT,
    report_date DATE NOT NULL,
    form_type TEXT,
    total_cash_and_st_investments_millions REAL,
    quarterly_burn_millions REAL,
    est_runway_months REAL,
    going_concern_flag BOOLEAN DEFAULT FALSE,
    source_url TEXT,
    source_confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, report_date, form_type)
);

CREATE INDEX IF NOT EXISTS idx_re_financials_cik ON re_financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_re_financials_runway ON re_financials(est_runway_months);

-- =============================================================================
-- Insider Trades (Form 4)
-- =============================================================================
CREATE TABLE IF NOT EXISTS re_insider_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_cik TEXT REFERENCES re_companies(company_id),
    ticker TEXT,
    filing_date DATE NOT NULL,
    form_type TEXT,
    transaction_type TEXT,        -- Purchase, Sale, Option Exercise
    insider_name TEXT,
    insider_title TEXT,           -- CEO, Director, 10% Owner
    shares_traded INTEGER,
    transaction_value REAL,
    source_url TEXT,
    source_confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, filing_date, insider_name, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_re_insider_cik ON re_insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_re_insider_date ON re_insider_trades(filing_date);
