-- =============================================================================
-- Quantum Computing Tracker -- Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

-- Table 1: companies
CREATE TABLE IF NOT EXISTS companies (
    company_id        TEXT PRIMARY KEY,
    ticker            TEXT,
    exchange          TEXT,             -- Nasdaq, NYSE, OTC, Private
    company_name      TEXT NOT NULL,
    market_cap_bucket TEXT,             -- nano / micro / small / mid / large / private
    quantum_approach  TEXT,             -- superconducting / trapped_ion / photonic / neutral_atom / topological
    country           TEXT DEFAULT 'US',
    notes             TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_qc_companies_approach ON companies(quantum_approach);

-- Table 2: systems
CREATE TABLE IF NOT EXISTS systems (
    system_id     TEXT PRIMARY KEY,
    company_id    TEXT NOT NULL REFERENCES companies(company_id),
    system_name   TEXT NOT NULL,
    qubit_count   INTEGER,
    qubit_type    TEXT,                 -- transmon / ion / photon / neutral_atom / majorana
    connectivity  TEXT,                 -- heavy-hex / all-to-all / linear / grid / custom
    status        TEXT DEFAULT 'roadmap', -- roadmap / prototype / available / deprecated
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_systems_company ON systems(company_id);
CREATE INDEX IF NOT EXISTS idx_qc_systems_status ON systems(status);
CREATE INDEX IF NOT EXISTS idx_qc_systems_qubits ON systems(qubit_count);

-- Table 3: benchmark_events
CREATE TABLE IF NOT EXISTS benchmark_events (
    benchmark_id      TEXT PRIMARY KEY,
    system_id         TEXT NOT NULL REFERENCES systems(system_id),
    benchmark_type    TEXT NOT NULL,    -- quantum_volume / CLOPS / EPLG / custom
    value             REAL,
    previous_value    REAL,
    event_date        DATE,
    source_url        TEXT,
    source_type       TEXT,            -- SEC / arXiv / PR / company_blog
    source_confidence TEXT,            -- primary / secondary / sponsor
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_benchmarks_system ON benchmark_events(system_id);
CREATE INDEX IF NOT EXISTS idx_qc_benchmarks_type ON benchmark_events(benchmark_type);
CREATE INDEX IF NOT EXISTS idx_qc_benchmarks_date ON benchmark_events(event_date);

-- Table 4: publications
CREATE TABLE IF NOT EXISTS publications (
    publication_id    TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    title             TEXT NOT NULL,
    arxiv_id          TEXT,
    journal           TEXT,
    publication_date  DATE,
    topic_tags        TEXT,            -- comma-separated: error_correction, algorithms, hardware, software
    citation_count    INTEGER DEFAULT 0,
    source_url        TEXT,
    source_confidence TEXT,            -- primary / secondary / sponsor
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_publications_company ON publications(company_id);
CREATE INDEX IF NOT EXISTS idx_qc_publications_date ON publications(publication_date);
CREATE INDEX IF NOT EXISTS idx_qc_publications_arxiv ON publications(arxiv_id);

-- Table 5: patent_filings
CREATE TABLE IF NOT EXISTS patent_filings (
    patent_id         TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    patent_number     TEXT,
    title             TEXT NOT NULL,
    filing_date       DATE,
    grant_date        DATE,
    status            TEXT,            -- pending / granted / abandoned / expired
    source_url        TEXT,
    source_confidence TEXT,            -- primary / secondary / sponsor
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_patents_company ON patent_filings(company_id);
CREATE INDEX IF NOT EXISTS idx_qc_patents_filing_date ON patent_filings(filing_date);
CREATE INDEX IF NOT EXISTS idx_qc_patents_status ON patent_filings(status);

-- Table 6: contract_awards
CREATE TABLE IF NOT EXISTS contract_awards (
    award_id          TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    agency            TEXT,            -- DOD / DOE / NSF / DARPA / IARPA / NASA
    program           TEXT,            -- SBIR / STTR / BAA / contract name
    award_amount_usd  REAL,
    award_date        DATE,
    source_url        TEXT,
    source_confidence TEXT,            -- primary / secondary / sponsor
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_awards_company ON contract_awards(company_id);
CREATE INDEX IF NOT EXISTS idx_qc_awards_agency ON contract_awards(agency);
CREATE INDEX IF NOT EXISTS idx_qc_awards_date ON contract_awards(award_date);

-- Table 7: system_scores
CREATE TABLE IF NOT EXISTS system_scores (
    score_id          TEXT PRIMARY KEY,
    system_id         TEXT NOT NULL REFERENCES systems(system_id),
    qubit_score       REAL CHECK(qubit_score BETWEEN 0 AND 10),
    error_rate_score  REAL CHECK(error_rate_score BETWEEN 0 AND 10),
    ecosystem_score   REAL CHECK(ecosystem_score BETWEEN 0 AND 10),
    funding_score     REAL CHECK(funding_score BETWEEN 0 AND 10),
    overall_score     REAL,
    scored_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qc_scores_system ON system_scores(system_id);
CREATE INDEX IF NOT EXISTS idx_qc_scores_overall ON system_scores(overall_score);

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

CREATE INDEX IF NOT EXISTS idx_qc_financials_cik ON financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_qc_financials_runway ON financials(est_runway_months);

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

CREATE INDEX IF NOT EXISTS idx_qc_insider_cik ON insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_qc_insider_date ON insider_trades(filing_date);

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

CREATE INDEX IF NOT EXISTS idx_qc_history_event ON event_history(event_id);
