-- =============================================================================
-- Biotech Product Tracker — Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

-- Table 1: companies
CREATE TABLE IF NOT EXISTS companies (
    company_id    TEXT PRIMARY KEY,
    ticker        TEXT NOT NULL,
    exchange      TEXT,           -- Nasdaq, NYSE, NYSE American, OTCQB, OTCQX
    company_name  TEXT NOT NULL,
    country       TEXT DEFAULT 'US',
    sector_bucket TEXT,           -- biotech / pharma / medtech / diagnostics
    market_cap_bucket TEXT,       -- nano / micro / small / mid
    lead_focus    TEXT,           -- main disease or modality focus
    notes         TEXT,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies(sector_bucket);

-- Table 2: products
CREATE TABLE IF NOT EXISTS products (
    product_id          TEXT PRIMARY KEY,
    company_id          TEXT NOT NULL REFERENCES companies(company_id),
    product_name        TEXT NOT NULL,
    generic_or_code     TEXT,
    modality            TEXT,     -- small molecule / antibody / cell therapy / device / etc.
    disease_area        TEXT,     -- oncology / rare disease / CNS / etc.
    target_or_mechanism TEXT,
    lead_indication     TEXT,
    secondary_indications TEXT,   -- comma-separated or JSON array
    regulatory_center   TEXT,     -- CDER / CBER / CDRH
    active              BOOLEAN DEFAULT TRUE,
    aliases             TEXT,     -- previous names, pipe-separated
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_company ON products(company_id);
CREATE INDEX IF NOT EXISTS idx_products_disease ON products(disease_area);
CREATE INDEX IF NOT EXISTS idx_products_modality ON products(modality);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(active);

-- Table 3: regulatory_events
CREATE TABLE IF NOT EXISTS regulatory_events (
    event_id                     TEXT PRIMARY KEY,
    product_id                   TEXT NOT NULL REFERENCES products(product_id),
    event_type                   TEXT NOT NULL,   -- approval / submission / adcom / clearance / CRL
    event_date                   DATE,
    jurisdiction                 TEXT DEFAULT 'FDA',
    pathway                      TEXT,            -- NDA / BLA / PMA / 510(k) / De Novo / HDE
    designation_flags            TEXT,            -- priority, fast track, BTD, accelerated, orphan
    source_type                  TEXT,            -- FDA / SEC / PR / ClinicalTrials.gov
    source_url                   TEXT,
    source_confidence            TEXT,            -- primary / secondary / sponsor
    summary                      TEXT,
    next_expected_step           TEXT,
    next_expected_date           DATE,
    official_fda_source_present  BOOLEAN DEFAULT FALSE,
    sponsor_disclosed_target_date DATE,
    created_at                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_product ON regulatory_events(product_id);
CREATE INDEX IF NOT EXISTS idx_events_date ON regulatory_events(event_date);
CREATE INDEX IF NOT EXISTS idx_events_type ON regulatory_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_next_date ON regulatory_events(next_expected_date);

-- Table 4: clinical_trials
CREATE TABLE IF NOT EXISTS clinical_trials (
    trial_id                      TEXT PRIMARY KEY,
    product_id                    TEXT NOT NULL REFERENCES products(product_id),
    nct_id                        TEXT UNIQUE,
    phase                         TEXT,
    status                        TEXT,          -- recruiting / active / completed / terminated
    title                         TEXT,
    indication                    TEXT,
    primary_endpoint              TEXT,
    estimated_primary_completion  DATE,
    estimated_study_completion    DATE,
    topline_expected_window       TEXT,          -- sponsor-estimated timing string
    results_posted                BOOLEAN DEFAULT FALSE,
    source_url                    TEXT,
    created_at                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_trials_product ON clinical_trials(product_id);
CREATE INDEX IF NOT EXISTS idx_trials_nct ON clinical_trials(nct_id);
CREATE INDEX IF NOT EXISTS idx_trials_status ON clinical_trials(status);
CREATE INDEX IF NOT EXISTS idx_trials_completion ON clinical_trials(estimated_primary_completion);

-- Table 5: advisory_meetings
CREATE TABLE IF NOT EXISTS advisory_meetings (
    adcom_id          TEXT PRIMARY KEY,
    product_id        TEXT REFERENCES products(product_id),
    committee_name    TEXT,
    meeting_date      DATE,
    topic             TEXT,
    materials_posted  BOOLEAN DEFAULT FALSE,
    vote_outcome      TEXT,
    source_url        TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_adcom_product ON advisory_meetings(product_id);
CREATE INDEX IF NOT EXISTS idx_adcom_date ON advisory_meetings(meeting_date);

-- Table 6: postmarketing
CREATE TABLE IF NOT EXISTS postmarketing (
    pmr_id               TEXT PRIMARY KEY,
    product_id           TEXT NOT NULL REFERENCES products(product_id),
    approval_context     TEXT,       -- accelerated / standard / supplement
    commitment_type      TEXT,       -- PMR / PMC / postmarket study
    requirement_summary  TEXT,
    deadline             DATE,
    status               TEXT,       -- pending / fulfilled / delayed
    source_url           TEXT,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pmr_product ON postmarketing(product_id);
CREATE INDEX IF NOT EXISTS idx_pmr_status ON postmarketing(status);

-- =============================================================================
-- Product scoring table (linked to products)
-- =============================================================================
CREATE TABLE IF NOT EXISTS product_scores (
    score_id                    TEXT PRIMARY KEY,
    product_id                  TEXT NOT NULL REFERENCES products(product_id),
    evidence_maturity           INTEGER CHECK(evidence_maturity BETWEEN 1 AND 5),
    endpoint_clarity            INTEGER CHECK(endpoint_clarity BETWEEN 1 AND 5),
    trial_design_quality        INTEGER CHECK(trial_design_quality BETWEEN 1 AND 5),
    regulatory_advantage        INTEGER CHECK(regulatory_advantage BETWEEN 1 AND 5),
    unmet_need_severity         INTEGER CHECK(unmet_need_severity BETWEEN 1 AND 5),
    mechanism_plausibility      INTEGER CHECK(mechanism_plausibility BETWEEN 1 AND 5),
    manufacturing_complexity_risk INTEGER CHECK(manufacturing_complexity_risk BETWEEN 1 AND 5),
    safety_uncertainty          INTEGER CHECK(safety_uncertainty BETWEEN 1 AND 5),
    sponsor_disclosure_quality  INTEGER CHECK(sponsor_disclosure_quality BETWEEN 1 AND 5),
    near_term_catalyst_density  INTEGER CHECK(near_term_catalyst_density BETWEEN 1 AND 5),
    composite_score             REAL,
    binary_event_risk           TEXT,   -- Low / Medium / High
    regulatory_visibility       TEXT,
    science_readthrough_value   TEXT,
    crowded_indication_penalty  TEXT,
    approval_path_complexity    TEXT,
    scored_by                   TEXT,
    scored_at                   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes                       TEXT
);

CREATE INDEX IF NOT EXISTS idx_scores_product ON product_scores(product_id);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, report_date, form_type)
);

CREATE INDEX IF NOT EXISTS idx_financials_cik ON financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_financials_runway ON financials(est_runway_months);

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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, filing_date, insider_name, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_insider_cik ON insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_insider_date ON insider_trades(filing_date);

-- =============================================================================
-- Conference Presentations
-- =============================================================================
CREATE TABLE IF NOT EXISTS conference_presentations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT REFERENCES products(product_id),
    keyword_matched TEXT,
    conference_name TEXT NOT NULL,
    conference_date DATE,
    abstract_title TEXT,
    presentation_type TEXT,       -- Poster, Oral, Plenary
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(conference_name, abstract_title)
);

CREATE INDEX IF NOT EXISTS idx_conference_product ON conference_presentations(product_id);
CREATE INDEX IF NOT EXISTS idx_conference_date ON conference_presentations(conference_date);

-- =============================================================================
-- Orange Book Patents
-- =============================================================================
CREATE TABLE IF NOT EXISTS patents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT REFERENCES products(product_id),
    active_ingredient TEXT NOT NULL,
    patent_number TEXT NOT NULL,
    expiration_date DATE,
    exclusivity_code TEXT,
    patent_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, patent_number)
);

CREATE INDEX IF NOT EXISTS idx_patents_product ON patents(product_id);
