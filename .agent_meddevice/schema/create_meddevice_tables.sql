-- =============================================================================
-- Medical Device & Diagnostics Tracker -- Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

-- Table 1: companies
CREATE TABLE IF NOT EXISTS companies (
    company_id        TEXT PRIMARY KEY,
    ticker            TEXT NOT NULL,
    exchange          TEXT,              -- Nasdaq, NYSE, NYSE American, OTCQB, OTCQX
    company_name      TEXT NOT NULL,
    market_cap_bucket TEXT,              -- nano / micro / small / mid / large
    device_segment    TEXT,              -- surgical / imaging / diagnostics / digital_health / implants
    country           TEXT DEFAULT 'US',
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_md_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_md_companies_segment ON companies(device_segment);

-- Table 2: devices
CREATE TABLE IF NOT EXISTS devices (
    device_id           TEXT PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(company_id),
    device_name         TEXT NOT NULL,
    device_type         TEXT,            -- therapeutic / diagnostic / combination / SaMD
    product_code        TEXT,            -- FDA 3-letter product code
    classification      TEXT,            -- I / II / III
    regulatory_pathway  TEXT,            -- 510k / PMA / De_Novo / HDE / exempt
    status              TEXT,            -- cleared / approved / pending / withdrawn / recalled
    aliases             TEXT,            -- previous names, pipe-separated
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_md_devices_company ON devices(company_id);
CREATE INDEX IF NOT EXISTS idx_md_devices_classification ON devices(classification);
CREATE INDEX IF NOT EXISTS idx_md_devices_pathway ON devices(regulatory_pathway);
CREATE INDEX IF NOT EXISTS idx_md_devices_status ON devices(status);

-- Table 3: regulatory_events
CREATE TABLE IF NOT EXISTS regulatory_events (
    event_id            TEXT PRIMARY KEY,
    device_id           TEXT NOT NULL REFERENCES devices(device_id),
    event_type          TEXT NOT NULL,   -- 510k_clearance / PMA_approval / De_Novo / recall / warning_letter
    event_date          DATE,
    decision_number     TEXT,            -- K-number, P-number, DEN-number
    summary             TEXT,
    source_url          TEXT,
    source_type         TEXT,            -- FDA / SEC / PR / Federal_Register
    source_confidence   TEXT,            -- primary / secondary / sponsor
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_md_reg_device ON regulatory_events(device_id);
CREATE INDEX IF NOT EXISTS idx_md_reg_date ON regulatory_events(event_date);
CREATE INDEX IF NOT EXISTS idx_md_reg_type ON regulatory_events(event_type);

-- Table 4: reimbursement_events
CREATE TABLE IF NOT EXISTS reimbursement_events (
    reimb_id            TEXT PRIMARY KEY,
    device_id           TEXT NOT NULL REFERENCES devices(device_id),
    event_type          TEXT NOT NULL,   -- CPT_code / HCPCS / coverage_determination / MAC_LCD
    code_or_id          TEXT,            -- CPT code, HCPCS code, NCD/LCD tracking ID
    status              TEXT,            -- proposed / final / active / retired
    effective_date      DATE,
    summary             TEXT,
    source_url          TEXT,
    source_type         TEXT,            -- CMS / SEC / Federal_Register / AMA
    source_confidence   TEXT,            -- primary / secondary / sponsor
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_md_reimb_device ON reimbursement_events(device_id);
CREATE INDEX IF NOT EXISTS idx_md_reimb_type ON reimbursement_events(event_type);
CREATE INDEX IF NOT EXISTS idx_md_reimb_date ON reimbursement_events(effective_date);

-- Table 5: adverse_events
CREATE TABLE IF NOT EXISTS adverse_events (
    ae_id               TEXT PRIMARY KEY,
    device_id           TEXT NOT NULL REFERENCES devices(device_id),
    event_date          DATE,
    event_type          TEXT,            -- malfunction / injury / death / other
    patient_outcome     TEXT,            -- hospitalization / life_threatening / death / other
    mdr_report_key      TEXT,            -- FDA MDR report key
    summary             TEXT,
    source_url          TEXT,
    source_type         TEXT,            -- FDA / manufacturer / user_facility
    source_confidence   TEXT,            -- primary / secondary
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_md_ae_device ON adverse_events(device_id);
CREATE INDEX IF NOT EXISTS idx_md_ae_date ON adverse_events(event_date);
CREATE INDEX IF NOT EXISTS idx_md_ae_type ON adverse_events(event_type);
CREATE INDEX IF NOT EXISTS idx_md_ae_mdr ON adverse_events(mdr_report_key);

-- Table 6: device_scores
CREATE TABLE IF NOT EXISTS device_scores (
    score_id              TEXT PRIMARY KEY,
    device_id             TEXT NOT NULL REFERENCES devices(device_id),
    regulatory_score      REAL CHECK(regulatory_score BETWEEN 0 AND 10),
    reimbursement_score   REAL CHECK(reimbursement_score BETWEEN 0 AND 10),
    safety_score          REAL CHECK(safety_score BETWEEN 0 AND 10),
    financial_score       REAL CHECK(financial_score BETWEEN 0 AND 10),
    overall_score         REAL CHECK(overall_score BETWEEN 0 AND 10),
    scored_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scored_by             TEXT DEFAULT 'agent',
    notes                 TEXT
);

CREATE INDEX IF NOT EXISTS idx_md_scores_device ON device_scores(device_id);
CREATE INDEX IF NOT EXISTS idx_md_scores_overall ON device_scores(overall_score);

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

CREATE INDEX IF NOT EXISTS idx_md_history_event ON event_history(event_id);

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

CREATE INDEX IF NOT EXISTS idx_md_financials_cik ON financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_md_financials_runway ON financials(est_runway_months);

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

CREATE INDEX IF NOT EXISTS idx_md_insider_cik ON insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_md_insider_date ON insider_trades(filing_date);
