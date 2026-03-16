-- =============================================================================
-- Commercial Space & Satellite Tracker -- Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

-- Table 1: companies
CREATE TABLE IF NOT EXISTS companies (
    company_id       TEXT PRIMARY KEY,
    ticker           TEXT NOT NULL,
    exchange         TEXT,              -- Nasdaq, NYSE, NYSE American, OTCQB, OTCQX
    company_name     TEXT NOT NULL,
    market_cap_bucket TEXT,             -- nano / micro / small / mid / large
    space_segment    TEXT,              -- launch / satellite / ground_station / space_station
    country          TEXT DEFAULT 'US',
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_space_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_space_companies_segment ON companies(space_segment);

-- Table 2: spacecraft
CREATE TABLE IF NOT EXISTS spacecraft (
    spacecraft_id    TEXT PRIMARY KEY,
    company_id       TEXT NOT NULL REFERENCES companies(company_id),
    name             TEXT NOT NULL,
    spacecraft_type  TEXT,              -- launch_vehicle / satellite / constellation / capsule
    orbit_type       TEXT,              -- LEO / MEO / GEO / SSO / GTO / lunar / interplanetary
    status           TEXT,              -- active / development / retired / destroyed
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spacecraft_company ON spacecraft(company_id);
CREATE INDEX IF NOT EXISTS idx_spacecraft_type ON spacecraft(spacecraft_type);
CREATE INDEX IF NOT EXISTS idx_spacecraft_status ON spacecraft(status);

-- Table 3: launch_events
CREATE TABLE IF NOT EXISTS launch_events (
    launch_id        TEXT PRIMARY KEY,
    spacecraft_id    TEXT NOT NULL REFERENCES spacecraft(spacecraft_id),
    launch_date      DATE,
    launch_site      TEXT,
    payload          TEXT,
    outcome          TEXT,              -- success / failure / partial
    source_url       TEXT,
    source_type      TEXT,              -- LaunchLibrary / SEC / PR / FAA
    source_confidence TEXT,             -- primary / secondary / sponsor
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_launch_spacecraft ON launch_events(spacecraft_id);
CREATE INDEX IF NOT EXISTS idx_launch_date ON launch_events(launch_date);
CREATE INDEX IF NOT EXISTS idx_launch_outcome ON launch_events(outcome);

-- Table 4: spectrum_filings
CREATE TABLE IF NOT EXISTS spectrum_filings (
    filing_id        TEXT PRIMARY KEY,
    company_id       TEXT NOT NULL REFERENCES companies(company_id),
    filing_type      TEXT,              -- IBFS / experimental / modification
    frequency_band   TEXT,              -- Ka / Ku / V / S / L / C
    status           TEXT,              -- pending / granted / denied / withdrawn
    filing_date      DATE,
    source_url       TEXT,
    source_confidence TEXT,             -- primary / secondary / sponsor
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_spectrum_company ON spectrum_filings(company_id);
CREATE INDEX IF NOT EXISTS idx_spectrum_status ON spectrum_filings(status);
CREATE INDEX IF NOT EXISTS idx_spectrum_date ON spectrum_filings(filing_date);

-- Table 5: constellation_status
CREATE TABLE IF NOT EXISTS constellation_status (
    status_id              TEXT PRIMARY KEY,
    spacecraft_id          TEXT NOT NULL REFERENCES spacecraft(spacecraft_id),
    satellites_deployed    INTEGER,
    satellites_operational INTEGER,
    coverage_percent       REAL,
    report_date            DATE,
    source_url             TEXT,
    source_confidence      TEXT,         -- primary / secondary / sponsor
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_constellation_spacecraft ON constellation_status(spacecraft_id);
CREATE INDEX IF NOT EXISTS idx_constellation_date ON constellation_status(report_date);

-- Table 6: contract_awards
CREATE TABLE IF NOT EXISTS contract_awards (
    award_id          TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    agency            TEXT,             -- NASA / DoD / NRO / FAA / SDA / NOAA
    program           TEXT,
    award_amount_usd  REAL,
    award_date        DATE,
    source_url        TEXT,
    source_confidence TEXT,             -- primary / secondary / sponsor
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_contract_company ON contract_awards(company_id);
CREATE INDEX IF NOT EXISTS idx_contract_agency ON contract_awards(agency);
CREATE INDEX IF NOT EXISTS idx_contract_date ON contract_awards(award_date);

-- Table 7: spacecraft_scores
CREATE TABLE IF NOT EXISTS spacecraft_scores (
    score_id            TEXT PRIMARY KEY,
    spacecraft_id       TEXT NOT NULL REFERENCES spacecraft(spacecraft_id),
    launch_score        REAL CHECK(launch_score BETWEEN 0 AND 10),
    constellation_score REAL CHECK(constellation_score BETWEEN 0 AND 10),
    revenue_score       REAL CHECK(revenue_score BETWEEN 0 AND 10),
    financial_score     REAL CHECK(financial_score BETWEEN 0 AND 10),
    overall_score       REAL CHECK(overall_score BETWEEN 0 AND 10),
    scored_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes               TEXT
);

CREATE INDEX IF NOT EXISTS idx_scores_spacecraft ON spacecraft_scores(spacecraft_id);
CREATE INDEX IF NOT EXISTS idx_scores_overall ON spacecraft_scores(overall_score);

-- =============================================================================
-- Event history table (never overwrite, always append)
-- =============================================================================
CREATE TABLE IF NOT EXISTS event_history (
    history_id   TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL,
    table_name   TEXT NOT NULL,
    field_name   TEXT NOT NULL,
    old_value    TEXT,
    new_value    TEXT,
    changed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by   TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_history_event ON event_history(event_id);

-- =============================================================================
-- Financials / Cash Runway
-- =============================================================================
CREATE TABLE IF NOT EXISTS financials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_cik TEXT REFERENCES companies(company_id),
    ticker TEXT,
    report_date DATE NOT NULL,
    form_type TEXT,
    total_cash_and_st_investments_millions REAL,
    quarterly_burn_millions REAL,
    est_runway_months REAL,
    going_concern_flag BOOLEAN DEFAULT FALSE,
    source_url TEXT,
    source_type TEXT,
    source_confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, report_date, form_type)
);

CREATE INDEX IF NOT EXISTS idx_space_financials_cik ON financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_space_financials_runway ON financials(est_runway_months);

-- =============================================================================
-- Insider Trades (Form 4)
-- =============================================================================
CREATE TABLE IF NOT EXISTS insider_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_cik TEXT REFERENCES companies(company_id),
    ticker TEXT,
    filing_date DATE NOT NULL,
    form_type TEXT,
    transaction_type TEXT,        -- Purchase, Sale, Option Exercise
    insider_name TEXT,
    insider_title TEXT,           -- CEO, Director, 10% Owner
    shares_traded INTEGER,
    transaction_value REAL,
    source_url TEXT,
    source_type TEXT,
    source_confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, filing_date, insider_name, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_space_insider_cik ON insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_space_insider_date ON insider_trades(filing_date);
