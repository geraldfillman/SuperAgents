-- =============================================================================
-- Cannabis & Psychedelic Therapeutics Tracker -- Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

-- Table 1: companies
CREATE TABLE IF NOT EXISTS companies (
    company_id       TEXT PRIMARY KEY,
    ticker           TEXT NOT NULL,
    exchange         TEXT,            -- Nasdaq, NYSE, CSE, OTCQX, OTCQB, NEO
    company_name     TEXT NOT NULL,
    market_cap_bucket TEXT,           -- nano / micro / small / mid
    segment          TEXT NOT NULL,   -- cannabis_MSO / cannabis_biotech / psychedelic_clinical / psychedelic_wellness
    country          TEXT DEFAULT 'US',
    notes            TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_cp_companies_segment ON companies(segment);

-- Table 2: compounds
CREATE TABLE IF NOT EXISTS compounds (
    compound_id    TEXT PRIMARY KEY,
    company_id     TEXT NOT NULL REFERENCES companies(company_id),
    compound_name  TEXT NOT NULL,
    compound_type  TEXT NOT NULL,     -- psilocybin / MDMA / LSD / DMT / cannabis_derived / synthetic
    indication     TEXT,
    phase          TEXT,              -- preclinical / Phase 1 / Phase 2 / Phase 3 / approved
    dea_schedule   TEXT,              -- I / II / III / IV / V / unscheduled / pending
    status         TEXT DEFAULT 'active',  -- active / discontinued / suspended
    aliases        TEXT,              -- previous names, pipe-separated
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_compounds_company ON compounds(company_id);
CREATE INDEX IF NOT EXISTS idx_cp_compounds_type ON compounds(compound_type);
CREATE INDEX IF NOT EXISTS idx_cp_compounds_phase ON compounds(phase);
CREATE INDEX IF NOT EXISTS idx_cp_compounds_status ON compounds(status);

-- Table 3: clinical_trials
CREATE TABLE IF NOT EXISTS clinical_trials (
    trial_id                     TEXT PRIMARY KEY,
    compound_id                  TEXT NOT NULL REFERENCES compounds(compound_id),
    nct_id                       TEXT UNIQUE,
    phase                        TEXT,
    status                       TEXT,          -- recruiting / active / completed / terminated
    enrollment                   INTEGER,
    start_date                   DATE,
    primary_completion_date      DATE,
    title                        TEXT,
    primary_endpoint             TEXT,
    results_posted               BOOLEAN DEFAULT FALSE,
    source_url                   TEXT,
    source_type                  TEXT,          -- ClinicalTrials.gov / WHO ICTRP / SEC / sponsor
    source_confidence            TEXT,          -- primary / secondary / sponsor
    created_at                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_trials_compound ON clinical_trials(compound_id);
CREATE INDEX IF NOT EXISTS idx_cp_trials_nct ON clinical_trials(nct_id);
CREATE INDEX IF NOT EXISTS idx_cp_trials_status ON clinical_trials(status);
CREATE INDEX IF NOT EXISTS idx_cp_trials_completion ON clinical_trials(primary_completion_date);

-- Table 4: scheduling_events
CREATE TABLE IF NOT EXISTS scheduling_events (
    event_id          TEXT PRIMARY KEY,
    compound_id       TEXT REFERENCES compounds(compound_id),
    event_type        TEXT NOT NULL,   -- scheduling_proposal / scheduling_final / state_decriminalization / state_legalization
    agency            TEXT NOT NULL,   -- DEA / FDA / state
    jurisdiction      TEXT,            -- federal or state abbreviation (e.g. CO, OR, CA)
    event_date        DATE,
    summary           TEXT,
    federal_register_doc_number TEXT,
    source_url        TEXT,
    source_type       TEXT,            -- federal_register / state_legislature / press_release
    source_confidence TEXT,            -- primary / secondary / sponsor
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_sched_compound ON scheduling_events(compound_id);
CREATE INDEX IF NOT EXISTS idx_cp_sched_date ON scheduling_events(event_date);
CREATE INDEX IF NOT EXISTS idx_cp_sched_type ON scheduling_events(event_type);
CREATE INDEX IF NOT EXISTS idx_cp_sched_agency ON scheduling_events(agency);

-- Table 5: state_licenses
CREATE TABLE IF NOT EXISTS state_licenses (
    license_id       TEXT PRIMARY KEY,
    company_id       TEXT NOT NULL REFERENCES companies(company_id),
    state            TEXT NOT NULL,    -- two-letter state code
    license_type     TEXT NOT NULL,    -- cultivation / processing / dispensary / delivery
    status           TEXT DEFAULT 'active',  -- active / pending / expired / revoked
    issued_date      DATE,
    expiry_date      DATE,
    license_number   TEXT,
    source_url       TEXT,
    source_type      TEXT,             -- SEC / state_registry / press_release
    source_confidence TEXT,            -- primary / secondary / sponsor
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_lic_company ON state_licenses(company_id);
CREATE INDEX IF NOT EXISTS idx_cp_lic_state ON state_licenses(state);
CREATE INDEX IF NOT EXISTS idx_cp_lic_type ON state_licenses(license_type);
CREATE INDEX IF NOT EXISTS idx_cp_lic_status ON state_licenses(status);

-- Table 6: compound_scores
CREATE TABLE IF NOT EXISTS compound_scores (
    score_id          TEXT PRIMARY KEY,
    compound_id       TEXT NOT NULL REFERENCES compounds(compound_id),
    clinical_score    REAL CHECK(clinical_score BETWEEN 0 AND 10),
    regulatory_score  REAL CHECK(regulatory_score BETWEEN 0 AND 10),
    market_score      REAL CHECK(market_score BETWEEN 0 AND 10),
    financial_score   REAL CHECK(financial_score BETWEEN 0 AND 10),
    overall_score     REAL CHECK(overall_score BETWEEN 0 AND 10),
    scoring_notes     TEXT,
    scored_by         TEXT DEFAULT 'system',
    scored_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cp_scores_compound ON compound_scores(compound_id);
CREATE INDEX IF NOT EXISTS idx_cp_scores_overall ON compound_scores(overall_score);

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
    source_type TEXT DEFAULT 'SEC',
    source_confidence TEXT DEFAULT 'secondary',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, report_date, form_type)
);

CREATE INDEX IF NOT EXISTS idx_cp_financials_cik ON financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_cp_financials_runway ON financials(est_runway_months);

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
    source_type TEXT DEFAULT 'SEC',
    source_confidence TEXT DEFAULT 'secondary',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, filing_date, insider_name, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_cp_insider_cik ON insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_cp_insider_date ON insider_trades(filing_date);

-- =============================================================================
-- Event history table (never overwrite, always append)
-- =============================================================================
CREATE TABLE IF NOT EXISTS event_history (
    history_id   TEXT PRIMARY KEY,
    event_id     TEXT NOT NULL,
    field_name   TEXT NOT NULL,
    old_value    TEXT,
    new_value    TEXT,
    changed_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by   TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_cp_history_event ON event_history(event_id);
