-- =============================================================================
-- Fintech & Digital Payments Tracker -- Schema
-- =============================================================================
-- Primary unit of analysis: financial product (payment rail, lending product,
-- neobank feature). Every record carries source_url, source_type, and
-- source_confidence for full provenance tracking.

CREATE TABLE IF NOT EXISTS companies (
    company_id   TEXT PRIMARY KEY,
    ticker       TEXT,
    exchange     TEXT,
    company_name TEXT NOT NULL,
    market_cap_bucket TEXT,  -- nano / micro / small / mid / large
    fintech_segment   TEXT CHECK (fintech_segment IN (
        'payments', 'lending', 'banking', 'crypto', 'insurance'
    )),
    country      TEXT DEFAULT 'US'
);

CREATE TABLE IF NOT EXISTS products (
    product_id   TEXT PRIMARY KEY,
    company_id   TEXT NOT NULL REFERENCES companies(company_id),
    product_name TEXT NOT NULL,
    product_type TEXT,  -- payment_rail / lending_product / neobank_feature / crypto_exchange / insuretech
    launch_date  TEXT,
    active       BOOLEAN DEFAULT TRUE,
    target_market TEXT  -- consumer / SMB / enterprise / cross-border
);

CREATE TABLE IF NOT EXISTS licensing_events (
    license_id       TEXT PRIMARY KEY,
    company_id       TEXT NOT NULL REFERENCES companies(company_id),
    license_type     TEXT CHECK (license_type IN (
        'MTL', 'banking_charter', 'broker_dealer', 'crypto'
    )),
    state            TEXT,
    status           TEXT,  -- applied / pending / approved / denied / revoked
    event_date       TEXT,
    source_url       TEXT,
    source_type      TEXT,
    source_confidence TEXT  -- primary / secondary / sponsor
);

CREATE TABLE IF NOT EXISTS partnership_events (
    partnership_id    TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    partner_name      TEXT,
    partnership_type  TEXT,  -- distribution / technology / white_label / co_brand / banking_as_a_service
    announced_date    TEXT,
    source_url        TEXT,
    source_confidence TEXT
);

CREATE TABLE IF NOT EXISTS adoption_metrics (
    metric_id         TEXT PRIMARY KEY,
    product_id        TEXT NOT NULL REFERENCES products(product_id),
    metric_type       TEXT CHECK (metric_type IN (
        'active_users', 'tpv', 'revenue_run_rate', 'merchant_count'
    )),
    value             REAL,
    period            TEXT,  -- e.g. 2025-Q4
    source_url        TEXT,
    source_confidence TEXT
);

CREATE TABLE IF NOT EXISTS enforcement_actions (
    action_id         TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    agency            TEXT CHECK (agency IN (
        'CFPB', 'OCC', 'SEC', 'FinCEN', 'state_AG'
    )),
    action_type       TEXT,  -- consent_order / cease_desist / fine / settlement / investigation
    action_date       TEXT,
    penalty_usd       REAL,
    source_url        TEXT,
    source_confidence TEXT
);

CREATE TABLE IF NOT EXISTS product_scores (
    score_id          TEXT PRIMARY KEY,
    product_id        TEXT NOT NULL REFERENCES products(product_id),
    adoption_score    REAL,  -- 0-10
    licensing_score   REAL,  -- 0-10
    competitive_score REAL,  -- 0-10
    financial_score   REAL,  -- 0-10
    overall_score     REAL,  -- 0-10 weighted composite
    scored_at         TEXT
);
