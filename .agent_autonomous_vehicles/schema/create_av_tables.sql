-- =============================================================================
-- Autonomous Vehicles & Robotics Tracker -- Database Schema
-- =============================================================================
-- All tables follow the convention: source_url, source_type, and
-- source_confidence on every record that ingests external data.

-- Companies tracked by the AV/Robotics agent
CREATE TABLE IF NOT EXISTS companies (
    company_id   TEXT PRIMARY KEY,
    ticker       TEXT,
    exchange     TEXT,
    company_name TEXT NOT NULL,
    market_cap_bucket TEXT,          -- nano / micro / small / mid / large
    av_segment   TEXT NOT NULL,      -- robotaxi / trucking / delivery / warehouse / humanoid
    country      TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

-- Vehicle platforms and robotic systems (primary unit of analysis)
CREATE TABLE IF NOT EXISTS platforms (
    platform_id    TEXT PRIMARY KEY,
    company_id     TEXT NOT NULL REFERENCES companies(company_id),
    platform_name  TEXT NOT NULL,
    platform_type  TEXT,             -- av_stack / delivery_robot / humanoid / warehouse_amr / trucking_stack
    autonomy_level TEXT,             -- L2 / L3 / L4 / L5
    sensor_suite   TEXT,             -- e.g. "lidar+camera+radar" or "camera_only"
    status         TEXT NOT NULL,    -- development / testing / limited_commercial / commercial
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now'))
);

-- Testing and deployment permits across jurisdictions
CREATE TABLE IF NOT EXISTS testing_permits (
    permit_id        TEXT PRIMARY KEY,
    platform_id      TEXT NOT NULL REFERENCES platforms(platform_id),
    jurisdiction     TEXT NOT NULL,   -- e.g. "CA", "AZ", "TX", "China-Beijing"
    permit_type      TEXT NOT NULL,   -- testing / driverless_testing / deployment / NHTSA_exemption
    status           TEXT NOT NULL,   -- active / expired / suspended / pending / revoked
    issued_date      TEXT,
    expiry_date      TEXT,
    source_url       TEXT,
    source_type      TEXT,            -- DMV / NHTSA / SEC / press_release
    source_confidence TEXT,           -- primary / secondary / sponsor
    created_at       TEXT DEFAULT (datetime('now')),
    updated_at       TEXT DEFAULT (datetime('now'))
);

-- Safety metrics per platform per reporting period
CREATE TABLE IF NOT EXISTS safety_metrics (
    metric_id         TEXT PRIMARY KEY,
    platform_id       TEXT NOT NULL REFERENCES platforms(platform_id),
    metric_type       TEXT NOT NULL,  -- disengagement_rate / miles_between_incident / crash_report
    value             REAL,
    period            TEXT,           -- e.g. "2025-Q4", "2025-annual"
    miles_driven      REAL,
    source_url        TEXT,
    source_type       TEXT,           -- NHTSA / CA_DMV / SEC / press_release
    source_confidence TEXT,           -- primary / secondary / sponsor
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now'))
);

-- Fleet deployments by city / operational domain
CREATE TABLE IF NOT EXISTS fleet_deployments (
    deployment_id      TEXT PRIMARY KEY,
    platform_id        TEXT NOT NULL REFERENCES platforms(platform_id),
    city               TEXT NOT NULL,
    state              TEXT,
    fleet_size         INTEGER,
    operational_domain TEXT,          -- e.g. "urban_geofenced", "highway_hub_to_hub", "warehouse_floor"
    launch_date        TEXT,
    source_url         TEXT,
    source_type        TEXT,
    source_confidence  TEXT,
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now'))
);

-- Partnership and collaboration events
CREATE TABLE IF NOT EXISTS partnership_events (
    partnership_id    TEXT PRIMARY KEY,
    company_id        TEXT NOT NULL REFERENCES companies(company_id),
    partner_name      TEXT NOT NULL,
    partnership_type  TEXT NOT NULL,  -- OEM / fleet_operator / sensor_supplier / mapping
    announced_date    TEXT,
    source_url        TEXT,
    source_type       TEXT,
    source_confidence TEXT,
    created_at        TEXT DEFAULT (datetime('now')),
    updated_at        TEXT DEFAULT (datetime('now'))
);

-- Composite platform scores
CREATE TABLE IF NOT EXISTS platform_scores (
    score_id          TEXT PRIMARY KEY,
    platform_id       TEXT NOT NULL REFERENCES platforms(platform_id),
    safety_score      REAL,          -- 0-10
    coverage_score    REAL,          -- 0-10
    partnership_score REAL,          -- 0-10
    financial_score   REAL,          -- 0-10
    overall_score     REAL,          -- 0-10 weighted composite
    scored_at         TEXT DEFAULT (datetime('now'))
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_platforms_company    ON platforms(company_id);
CREATE INDEX IF NOT EXISTS idx_permits_platform     ON testing_permits(platform_id);
CREATE INDEX IF NOT EXISTS idx_permits_jurisdiction ON testing_permits(jurisdiction);
CREATE INDEX IF NOT EXISTS idx_safety_platform      ON safety_metrics(platform_id);
CREATE INDEX IF NOT EXISTS idx_fleet_platform       ON fleet_deployments(platform_id);
CREATE INDEX IF NOT EXISTS idx_partnerships_company ON partnership_events(company_id);
CREATE INDEX IF NOT EXISTS idx_scores_platform      ON platform_scores(platform_id);
