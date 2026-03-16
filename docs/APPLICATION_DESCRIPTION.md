# Super_Agents — Application Description & Future Roadmap

Updated: 2026-03-15

---

## Part 1: What Super_Agents Is

### The Problem

Investors, analysts, and intelligence operators tracking emerging sectors — biotech, defense, quantum computing, critical minerals, cybersecurity — face the same challenge: the information that moves markets and decisions is scattered across dozens of government databases, regulatory filings, open-source intelligence feeds, and industry trackers. No single platform aggregates these signals in a structured, auditable, asset-level format.

The typical workflow today involves manually checking SEC EDGAR for filings, openFDA for drug approvals, SAM.gov for contract awards, CISA for vulnerability advisories, and dozens of other sources — then trying to cross-reference findings by hand. Analysts miss signals because they can't monitor everything. When they do catch something, the provenance trail is often lost.

### The Solution

Super_Agents is a **multi-sector, asset-first intelligence framework** that automates the collection, normalization, enrichment, and presentation of high-signal data across 13+ sectors. Instead of tracking companies as monolithic entities, every agent tracks the **specific asset that creates or destroys value** in its sector:

| Sector | Tracked Asset | Example |
|--------|--------------|---------|
| Biotech | The drug product | Keytruda, Ozempic |
| Gaming | The game title | Pragmata, Dota 2 |
| Aerospace | The defense system/program | F-35, SBIR award |
| Rare Earth | The mining project | Mountain Pass, Winu |
| Cybersecurity | The vulnerability/threat | CVE-2026-XXXX, BGP hijack |
| Renewable Energy | The energy project | Solar farm interconnection |
| Quantum | The qubit platform | IonQ trapped-ion roadmap |

This asset-first approach means the system can detect value-changing events — an FDA approval, a CVE added to the Known Exploited Vulnerabilities catalog, a defense contract award — at the individual asset level rather than relying on company-level news that arrives late and with less precision.

### How It Works

#### Data Collection Layer

Each sector agent contains **skills** — focused Python scripts that fetch data from specific public APIs and regulatory databases. Examples:

- `fda_tracker` fetches drug approvals from the openFDA API
- `sam_pipeline_tracker` fetches government contract opportunities from SAM.gov
- `fetch_cisa_advisories` pulls vulnerability data from CISA's KEV catalog
- `fetch_sbir_awards` tracks Small Business Innovation Research grants from USAspending.gov
- `storefront_monitor` captures game metrics from Steam's public API

Every record written by any script carries mandatory provenance:
- `source_url` — the exact URL the data came from
- `source_type` — the type of source (API, filing, registry)
- `source_confidence` — `primary` (official government/regulator), `secondary` (third-party aggregator), or `sponsor` (company self-reported)

#### Processing & Enrichment Layer

Raw data flows through normalization pipelines in `src/super_agents/` that:
- Deduplicate and validate records
- Apply watchlist filters (which assets/companies to track)
- Score findings by severity and relevance
- Cross-reference across sectors (e.g., a rare earth company also appearing in sanctions data)

The planned **Global Risk Layer** will add automatic enrichment for any entity:
- **Sanctions screening** — OFAC SDN + OpenSanctions cross-reference
- **Conflict signals** — GDELT event density + ReliefWeb alerts
- **Weather/environmental** — NASA FIRMS fire data + NOAA space weather
- **Cyber threat** — CISA KEV additions + IODA internet outage detection

#### Presentation Layer

The Streamlit dashboard provides an operator-facing interface with:
- **Fleet Overview** — status cards showing all agents, their health, and last run time
- **Agent Detail** — drill into any agent's skills, scripts, and outputs
- **Findings Board** — cross-agent view of discoveries ranked by severity
- **Calendars** — forward-looking catalyst events (FDA dates, launch windows, patch deadlines)
- **Simulation Engine** — MiroFish-powered scenario runner for cross-sector signal cascades

Every agent run produces **dual outputs**: JSON for automation pipelines and Markdown for human review. These artifacts follow a standardized contract so the dashboard can consume data from any agent without custom wiring.

#### CLI & Multi-Platform Execution

The universal CLI (`python -m super_agents`) supports:
- `list` — discover all agents and their skills
- `run` — execute a specific script with parameters
- `search` — live search across configured agents

The same commands work across Claude Code, OpenAI Codex, and Google Gemini CLI, making the framework LLM-agnostic for operator interaction.

### Current Scale

| Metric | Count |
|--------|-------|
| Sector agents | 13 (8 runnable, 5 stub/planned) |
| Total skills | 61+ across all agents |
| Total scripts | 77+ runnable Python scripts |
| Public APIs integrated | 30+ (SEC EDGAR, openFDA, SAM.gov, CISA, Steam, arXiv, USPTO, FRED, etc.) |
| Dashboard pages | 7 live + 6 planned |
| Agent blueprints | 5 completed sector designs |
| Test suites | 33+ tests (security + CLI discovery) |

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Core language | Python | ETL, skills, workflows, CLI |
| Data storage | SQLite (local) → PostgreSQL (production) | Structured asset and findings data |
| Dashboard | Streamlit multipage | Operator-facing UI |
| Agent architecture | MCP servers | Agent communication and orchestration |
| Configuration | YAML per agent | Sector-specific settings and metadata |
| LLM routing | LiteLLM | Model-agnostic AI-assisted extraction |
| Observability | Langfuse | Token usage, cost tracking, trace analysis |
| Simulation | MiroFish | Cross-sector scenario modeling |
| Output formats | JSON + Markdown + HTML | Automation, human review, reporting |

---

## Part 2: What Makes This Different

### 1. Asset-First, Not Company-First

Most financial and intelligence platforms organize data by company ticker or entity name. Super_Agents inverts this: the tracked unit is the drug, the title, the mine, the vulnerability. A single company may have dozens of tracked assets, each with its own lifecycle, regulatory milestones, and risk profile. This granularity catches signals that company-level monitoring misses entirely — a Phase 3 drug failure doesn't move the parent company's stock until the market digests it, but the asset-level event is detectable immediately.

### 2. Source Provenance as a First-Class Citizen

Every record in the system has a verifiable chain back to its source. This isn't metadata bolted on after the fact — it's a mandatory schema requirement enforced at the skill level. When an analyst sees a finding, they can click through to the exact government filing, regulatory database entry, or API response that produced it. This makes the system auditable in a way that LLM-summarized intelligence feeds are not.

### 3. Sector-Specific Skills, Shared Platform

Each agent is specialized for its sector's unique data sources and regulatory landscape, but all agents share the same platform infrastructure: CLI discovery, artifact contracts, run summaries, status reporting, and dashboard integration. This means adding a new sector doesn't require rebuilding the platform — just answering 10 design questions, writing a blueprint, and implementing the sector-specific skills.

### 4. Pilot-First, Noise-Second

The project enforces a deliberate scaling pattern: start with 3-5 companies, exercise every skill on that small set, tighten noisy extraction rules, and only then expand coverage. This prevents the common failure mode of intelligence platforms — wide coverage with so much noise that analysts stop trusting the output.

### 5. Dual-Output Architecture

JSON for machines, Markdown for humans, on every run. This means the same agent output can feed a downstream automation pipeline (trading signals, alerting systems, report generators) and also be read directly by an analyst without any additional tooling.

---

## Part 3: Future Roadmap

### Near Term (Weeks 1-3): Stabilize the Core

**Goal:** Make the existing platform reliable and self-consistent before expanding.

#### Phase 0 — Documentation Realignment
- Sync task boards with actual repo state (cybersecurity and risk layer have progressed beyond what docs claim)
- Establish EXECUTION_PLAN.md as the active sequencing document
- Remove false "not built yet" claims from planning docs

#### Phase 1 — Cybersecurity MVP Hardening
- Expand beyond KEV-only basics to include NVD CVE scoring, IODA outage detection, BGP alert monitoring
- Define stable artifact set for cyber outputs
- Achieve end-to-end CLI-to-dashboard workflow with saved artifacts
- Full test coverage for implemented cyber modules

#### Phase 2 — Risk Layer Backend Integration
- Implement `src/super_agents/common/risk_layer/` with real data sources
- Replace all mock data in the Risk Layer dashboard page
- Wire the reusable risk badge component to live `get_risk_context()` calls
- Graceful degradation when individual sources are unavailable

#### Phase 3 — Shared Contract & Regression Hardening
- Formalize the dashboard artifact contract schema in `docs/architecture.md`
- Add regression tests for all shared surfaces (`dashboard_data.py`, `status.py`, `run_summary.py`)
- Mark partial and mock-driven pages with explicit data-state indicators

### Medium Term (Weeks 4-8): Controlled Expansion

**Goal:** Add high-value sector agents in matched backend/frontend pairs.

#### Wave 1 — Geopolitical Risk Agent
- Sanctions monitoring (OFAC + OpenSanctions), export control tracking (BIS), executive order monitoring (Federal Register)
- Election tracking (Google Civic API), travel advisory mapping (State Department)
- UN Security Council session tracking, ICC/ICJ monitoring
- Directly enriches rare_earth, fintech, and aerospace agents via sanctions cross-reference

#### Wave 2 — Defense Intelligence Agent
- Carrier group tracking (USNI Fleet Tracker), military exercise monitoring (NATO RSS, DVIDS)
- ADS-B military aircraft monitoring (airplanes.live, adsb.lol)
- Defense procurement tracking (Federal Register), missile test monitoring
- Directly enriches aerospace agent with defense posture signals

#### Wave 3 — Maritime Logistics Agent
- Fleet position tracking, chokepoint monitoring (Hormuz, Suez, Taiwan Strait, Malacca)
- Piracy/ASAM alerts (NGA Maritime Safety Information), submarine cable status (TeleGeography)
- Shipping market indicators (BDRY, SBLK, ZIM ETFs via Yahoo Finance)
- Directly enriches rare_earth (supply chain) and renewable_energy (offshore logistics)

#### Wave 4 — Conflict Risk Agent
- Active conflict zone mapping via GDELT event density
- Arms embargo tracking (SIPRI), CBRN alert monitoring (OPCW, IAEA)
- Nuclear risk indicators (Bulletin of Atomic Scientists), satellite fire alerts (NASA FIRMS)
- Cross-references with geopolitical_risk and defense_intelligence for multi-source validation

#### Shared Enrichment Infrastructure (runs parallel to waves)
- `gdelt_fetcher.py` — GDELT event API for conflict, geopolitical, and sentiment signals
- `sanctions_check.py` — OFAC SDN + OpenSanctions entity screening
- `earth_obs_fetcher.py` — NASA FIRMS fires, NOAA space weather, NWS severe weather

### Long Term (Months 3-6): Platform Maturity

**Goal:** Transform from a collection of scripts into a production intelligence platform.

#### Production Data Layer
- Migrate from SQLite to PostgreSQL for concurrent access and scalability
- Implement proper schema migrations with version tracking
- Add data retention policies and archival workflows
- Time-series optimizations for high-frequency signals (market data, ADS-B, weather)

#### Workflow Orchestration
- Move from ad-hoc CLI runs to scheduled workflow execution (Prefect or Airflow)
- Daily/weekly/monthly cadence per agent (as defined in existing workflow docs)
- Dependency-aware execution: run enrichment modules before agents that consume them
- Failure recovery: retry with backoff, partial-run resumption, dead-letter queues

#### Alerting & Notification System
- Real-time alerts when findings exceed severity thresholds
- Configurable channels: email (SMTP already scaffolded), Slack, webhook
- Alert deduplication and cooldown windows to prevent alert fatigue
- Escalation rules: sanctions hits → immediate, routine findings → daily digest

#### Cross-Sector Correlation Engine
- Automatic detection when the same entity appears across multiple sectors
- Example: a rare earth mining company also flagged in OFAC sanctions, with a defense contract in SAM.gov and a stock offering in SEC EDGAR — all correlated into a single entity view
- Graph-based entity resolution across agent outputs
- Temporal correlation: detect when events cluster in time across sectors

#### API Layer
- RESTful API exposing agent outputs, findings, and risk context
- Authentication and rate limiting for multi-user access
- Webhook subscriptions for downstream consumers (trading systems, dashboards, reports)
- OpenAPI spec for third-party integration

#### Advanced Analytics
- Trend detection: identify acceleration/deceleration in sector activity
- Anomaly detection: flag unusual patterns in agent outputs (sudden spike in CVEs for one vendor, abnormal contract award clustering)
- Predictive signals: combine historical patterns with forward-looking catalysts
- Confidence scoring: machine-learned confidence adjustments based on source reliability history

### Visionary (6-12 Months): Intelligence Network

**Goal:** Evolve from a single-operator tool into a networked intelligence capability.

#### Multi-Operator Support
- Role-based access: operator (full control), analyst (read + query), viewer (dashboard only)
- Audit trail: who ran what, when, and what they saw
- Shared annotations: analysts can tag findings with context that persists across sessions

#### MiroFish Simulation Expansion
- Pre-built scenario templates: "What if China restricts rare earth exports?", "What if a major CVE hits critical infrastructure?"
- Cross-sector cascade modeling: trace how a single event propagates through interconnected sectors
- Historical backtesting: run scenarios against past data to validate signal quality
- Monte Carlo simulation: probabilistic outcome ranges for complex multi-factor scenarios

#### Natural Language Intelligence Interface
- Ask questions in plain language: "Which biotech companies have FDA catalysts in the next 90 days and are also burning cash?"
- LLM-powered query translation to structured agent searches
- Conversational drill-down: "Tell me more about that company's insider trading activity"
- Report generation: "Write me a weekly briefing on defense procurement trends"

#### Data Marketplace
- Curated data feeds by sector for downstream consumers
- Structured exports: CSV, Parquet, JSON-LD for knowledge graph integration
- Embeddable widgets for third-party dashboards
- API-first distribution for fintech platforms, risk vendors, and research tools

#### Federated Agent Network
- Connect Super_Agents instances across organizations (with access controls)
- Shared enrichment: one instance's rare earth findings can enrich another's defense analysis
- Collaborative watchlists: sector specialists contribute and curate asset universes together
- Distributed collection: agents running in different regions for geographic coverage and redundancy

---

## Part 4: Competitive Landscape & Positioning

### What Exists Today

| Category | Examples | Super_Agents Differentiator |
|----------|---------|---------------------------|
| Financial terminals | Bloomberg, Refinitiv | Asset-level granularity vs. company-level; open-source data vs. proprietary feeds; auditable provenance |
| OSINT platforms | Recorded Future, Maltego | Multi-sector coverage vs. single-domain focus; structured output vs. graph-only; dual JSON+Markdown output |
| Government data aggregators | USAspending, FPDS | Cross-sector correlation vs. single-source views; enrichment layer vs. raw data |
| LLM research tools | Perplexity, ChatGPT browse | Structured, repeatable extraction vs. one-shot answers; source confidence scoring vs. citation links |
| Threat intelligence | CrowdStrike, Mandiant | Broader scope (cyber + financial + geopolitical) vs. cyber-only; asset-first vs. indicator-first |

### Target Users

| User Type | Primary Value | Key Workflows |
|-----------|--------------|---------------|
| **Investment analysts** | Asset-level catalyst tracking, financial runway monitoring, insider activity detection | Daily FDA/SEC/contract scans, catalyst calendar review, cross-sector entity correlation |
| **Intelligence analysts** | Multi-source OSINT aggregation with provenance | Sanctions screening, conflict monitoring, defense procurement tracking |
| **Risk managers** | Automated risk scoring with auditable sources | Global Risk Layer queries, sanctions cross-reference, supply chain disruption alerts |
| **Policy researchers** | Regulatory tracking across agencies | Executive order monitoring, export control changes, FERC/DOE policy tracking |
| **Security operations** | Vulnerability prioritization with context | CISA KEV monitoring, BGP anomaly detection, patch calendar management |

---

## Part 5: Key Metrics for Success

### Platform Health
- **Agent coverage**: % of planned agents at OPERATIONAL status
- **Source uptime**: % of API integrations returning valid data on scheduled runs
- **Artifact freshness**: time since last successful artifact write per agent
- **Test coverage**: % of modules with automated tests (target: 80%+)

### Intelligence Quality
- **Signal-to-noise ratio**: actionable findings per total findings generated
- **Source diversity**: number of independent sources confirming each finding
- **Provenance completeness**: % of records with all three provenance fields populated
- **False positive rate**: findings that were later retracted or corrected

### Operator Efficiency
- **Time to insight**: minutes from event occurrence to dashboard visibility
- **Cross-sector correlation rate**: % of findings that connect to activity in another sector
- **Alert precision**: % of alerts that required operator action
- **Coverage gap detection**: sectors/assets with stale or missing data flagged automatically
