-- =============================================================================
-- Gaming Studio Tracker - Database Schema
-- Compatible with PostgreSQL and SQLite
-- =============================================================================

CREATE TABLE IF NOT EXISTS companies (
    company_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    exchange TEXT,
    company_name TEXT NOT NULL,
    country TEXT DEFAULT 'US',
    sector_bucket TEXT,
    market_cap_bucket TEXT,
    lead_focus TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gaming_companies_ticker ON companies(ticker);
CREATE INDEX IF NOT EXISTS idx_gaming_companies_sector ON companies(sector_bucket);

CREATE TABLE IF NOT EXISTS titles (
    title_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(company_id),
    game_title TEXT NOT NULL,
    internal_code_name TEXT,
    genre TEXT,
    engine TEXT,
    publisher TEXT,
    franchise TEXT,
    platforms TEXT,
    business_model TEXT,
    status TEXT,
    active BOOLEAN DEFAULT TRUE,
    aliases TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_titles_company ON titles(company_id);
CREATE INDEX IF NOT EXISTS idx_titles_status ON titles(status);
CREATE INDEX IF NOT EXISTS idx_titles_publisher ON titles(publisher);
CREATE INDEX IF NOT EXISTS idx_titles_active ON titles(active);

CREATE TABLE IF NOT EXISTS release_events (
    event_id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL REFERENCES titles(title_id),
    event_type TEXT NOT NULL,
    event_date DATE,
    expected_release_date DATE,
    platform_scope TEXT,
    source_type TEXT,
    source_url TEXT,
    source_confidence TEXT,
    summary TEXT,
    next_expected_step TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_release_events_title ON release_events(title_id);
CREATE INDEX IF NOT EXISTS idx_release_events_date ON release_events(event_date);
CREATE INDEX IF NOT EXISTS idx_release_events_expected_date ON release_events(expected_release_date);
CREATE INDEX IF NOT EXISTS idx_release_events_type ON release_events(event_type);

CREATE TABLE IF NOT EXISTS publisher_milestones (
    milestone_id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL REFERENCES titles(title_id),
    milestone_type TEXT NOT NULL,
    expected_date DATE,
    achieved_date DATE,
    payment_amount_millions REAL,
    payment_currency TEXT,
    status TEXT,
    source_type TEXT,
    source_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_publisher_milestones_title ON publisher_milestones(title_id);
CREATE INDEX IF NOT EXISTS idx_publisher_milestones_expected ON publisher_milestones(expected_date);

CREATE TABLE IF NOT EXISTS certifications (
    certification_id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL REFERENCES titles(title_id),
    registry_name TEXT NOT NULL,
    territory TEXT,
    rating_or_status TEXT,
    signal_type TEXT,
    signal_date DATE,
    source_url TEXT,
    source_confidence TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_certifications_title ON certifications(title_id);
CREATE INDEX IF NOT EXISTS idx_certifications_signal_date ON certifications(signal_date);

CREATE TABLE IF NOT EXISTS storefront_metrics (
    metric_id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL REFERENCES titles(title_id),
    storefront TEXT NOT NULL,
    steam_app_id TEXT,
    snapshot_date DATE NOT NULL,
    release_date DATE,
    follower_count INTEGER,
    wishlist_rank INTEGER,
    review_count INTEGER,
    review_score_percent REAL,
    tags TEXT,
    source_url TEXT,
    source_confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title_id, storefront, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_storefront_metrics_title ON storefront_metrics(title_id);
CREATE INDEX IF NOT EXISTS idx_storefront_metrics_date ON storefront_metrics(snapshot_date);

CREATE TABLE IF NOT EXISTS engagement_metrics (
    metric_id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL REFERENCES titles(title_id),
    snapshot_date DATE NOT NULL,
    metacritic_score REAL,
    opencritic_score REAL,
    steam_review_score_percent REAL,
    concurrent_players_current INTEGER,
    concurrent_players_peak_24h INTEGER,
    concurrent_players_peak_all_time INTEGER,
    estimated_launch_window_day INTEGER,
    source_url TEXT,
    source_confidence TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(title_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_engagement_metrics_title ON engagement_metrics(title_id);
CREATE INDEX IF NOT EXISTS idx_engagement_metrics_date ON engagement_metrics(snapshot_date);

CREATE TABLE IF NOT EXISTS title_scores (
    score_id TEXT PRIMARY KEY,
    title_id TEXT NOT NULL REFERENCES titles(title_id),
    production_visibility INTEGER CHECK(production_visibility BETWEEN 1 AND 5),
    funding_resilience INTEGER CHECK(funding_resilience BETWEEN 1 AND 5),
    launch_readiness INTEGER CHECK(launch_readiness BETWEEN 1 AND 5),
    storefront_momentum INTEGER CHECK(storefront_momentum BETWEEN 1 AND 5),
    community_quality INTEGER CHECK(community_quality BETWEEN 1 AND 5),
    critic_upside INTEGER CHECK(critic_upside BETWEEN 1 AND 5),
    portfolio_dependence INTEGER CHECK(portfolio_dependence BETWEEN 1 AND 5),
    post_launch_monetization INTEGER CHECK(post_launch_monetization BETWEEN 1 AND 5),
    execution_risk INTEGER CHECK(execution_risk BETWEEN 1 AND 5),
    disclosure_quality INTEGER CHECK(disclosure_quality BETWEEN 1 AND 5),
    composite_score REAL,
    binary_launch_risk TEXT,
    dilution_risk TEXT,
    release_confidence TEXT,
    scored_by TEXT,
    scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_title_scores_title ON title_scores(title_id);

CREATE TABLE IF NOT EXISTS event_history (
    history_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_gaming_history_event ON event_history(event_id);

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

CREATE INDEX IF NOT EXISTS idx_gaming_financials_cik ON financials(company_cik);
CREATE INDEX IF NOT EXISTS idx_gaming_financials_runway ON financials(est_runway_months);

CREATE TABLE IF NOT EXISTS insider_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_cik TEXT REFERENCES companies(company_id),
    ticker TEXT,
    filing_date DATE NOT NULL,
    form_type TEXT,
    transaction_type TEXT,
    insider_name TEXT,
    insider_title TEXT,
    shares_traded INTEGER,
    transaction_value REAL,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(company_cik, filing_date, insider_name, transaction_type)
);

CREATE INDEX IF NOT EXISTS idx_gaming_insider_cik ON insider_trades(company_cik);
CREATE INDEX IF NOT EXISTS idx_gaming_insider_date ON insider_trades(filing_date);
