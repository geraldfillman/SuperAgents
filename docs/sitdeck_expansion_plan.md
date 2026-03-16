# Super_Agents × sitdeck.com Expansion Plan
**Date:** 2026-03-15 | **Source:** sitdeck.com data category analysis

---

## Overview

sitdeck.com aggregates 25 data categories across 170+ sources covering financial markets, military posture, aviation, maritime, conflict, cyber, climate, and geopolitical risk. This document maps those categories to Super_Agents architecture, proposes 5 new agents, 3 shared signal enrichment layers, and a Global Risk Layer concept.

---

## Master Mapping

### New Agents (net-new sectors)

| sitdeck Category | New Agent | Priority |
|---|---|---|
| Military & Defense, Aviation & Airspace | `defense_intelligence` | HIGH |
| Maritime & Shipping | `maritime_logistics` | HIGH |
| Conflict & Security, Nuclear & WMD, Terrorism | `conflict_risk` | HIGH |
| Space & Satellites | `space_systems` | MEDIUM |
| Political & Governance, Sanctions & Trade | `geopolitical_risk` | HIGH |
| Seismic, Weather, Climate | Shared `earth_signals` layer | MEDIUM |
| Humanitarian & Refugees, Food & Water Security | `humanitarian_ops` | LOW |

### Skills Added to Existing Agents

| Existing Agent | New Skills |
|---|---|
| `aerospace` | ADS-B military tracker, bomber activity, FAA NAS, NATO posture, carrier groups, defense procurement (Federal Register) |
| `biotech` | openFDA food recalls/drug shortages, CDC wastewater surveillance, WHO disease outbreak news |
| `fintech` | Fear & Greed (Alternative.me), CFTC COT Reports, FRED macro, US Treasury debt, FHFA housing, Fed/ECB/BOJ/PBOC balance sheets, Polymarket/Kalshi/Metaculus prediction markets, semiconductor indices |
| `renewable_energy` | OPEC MOMR production, Baker Hughes rig count, EIA SPR stocks, NOAA CO2/methane, Arctic ice extent, EPA GHGRP |
| `rare_earth` | BIS export controls, OFAC sanctions overlay, ITA tariffs, UN sanctions, OpenSanctions cross-reference |
| `cybersecurity` | Full skill set (see below — currently a stub with no scripts) |

---

## Five New Agents

### 1. `defense_intelligence` 🔴 HIGH PRIORITY

**Asset-first on:** military systems, posture events, flight anomalies (not companies)

**Why high value:** Fills the gap between aerospace company tracking (procurement) and real-time operational signals (exercises, carrier movements, ADS-B anomalies). These are leading indicators for defense procurement cycles.

**10 Skills:**

| Skill | Primary Source | API |
|---|---|---|
| `carrier_group_tracker` | USNI Fleet Tracker | `https://news.usni.org/category/fleet-tracker` (scrape/RSS) |
| `nato_posture_monitor` | NATO Newsroom RSS | `https://www.nato.int/cps/en/natohq/news.htm` |
| `defense_procurement_monitor` | Federal Register | `https://www.federalregister.gov/api/v1/documents.json?conditions[type][]=RULE&conditions[agencies][]=defense-department` |
| `military_exercise_tracker` | DVIDS | `https://www.dvidshub.net/api` |
| `missile_test_tracker` | NTI / Arms Control Wonk | `https://www.nti.org/` (RSS) |
| `adsb_military_monitor` | airplanes.live / adsb.lol | `https://airplanes.live/map-api/` |
| `vip_aircraft_tracker` | adsb.lol | `https://adsb.lol/api/0/callsign/{callsign}` |
| `emergency_squawk_monitor` | adsb.lol squawk filter | `https://adsb.lol/api/0/squawk/7700` |
| `defense_news_monitor` | DoD/CSIS/NATO RSS | `https://www.defense.gov/News/` (RSS) |
| `exercise_calendar` | Aggregated | — |

**Schema tables:** `military_systems`, `posture_events`, `procurement_notices`, `flight_anomalies`, `exercise_records`

---

### 2. `geopolitical_risk` 🔴 HIGH PRIORITY

**Asset-first on:** policy instruments, sanctions entries, jurisdictions

**Why high value:** Sanctions and export controls gate operations for `rare_earth`, `fintech`, and `aerospace`. This is the regulatory intelligence backbone for the entire framework — every other agent can query it to check "is this entity/country under sanctions?"

**10 Skills:**

| Skill | Primary Source | API |
|---|---|---|
| `sanctions_monitor` | OFAC / OpenSanctions | `https://ofac.treasury.gov/` + `https://api.opensanctions.org/match/default` |
| `export_control_tracker` | BIS / Federal Register | `https://www.bis.doc.gov/` |
| `tariff_monitor` | ITA / Federal Register | `https://api.trade.gov/` |
| `un_sanctions_tracker` | UN SC Consolidated List | `https://scsanctions.un.org/resources/xml/en/consolidated.xml` |
| `executive_order_monitor` | Federal Register | `https://www.federalregister.gov/api/v1/documents.json?conditions[type][]=PRESDOCU` |
| `election_tracker` | Wikipedia / Google Civic API | `https://en.wikipedia.org/wiki/Wikipedia:Current_events` |
| `travel_advisory_monitor` | US State Dept | `https://travel.state.gov/content/travel/en/traveladvisories/` |
| `unsc_session_tracker` | UN SC API | `https://api.un.org/` |
| `icc_icj_monitor` | ICC / ICJ RSS | `https://www.icc-cpi.int/news` (RSS) |
| `geopolitical_calendar` | Aggregated | — |

---

### 3. `maritime_logistics` 🔴 HIGH PRIORITY

**Asset-first on:** vessels, routes, chokepoints, cables

**Why high value:** Maritime chokepoints (Strait of Hormuz, Suez, Taiwan Strait) are single points of failure for global trade. Feeds `fintech` (shipping ETFs), `rare_earth` (mineral transport), and `conflict_risk` (naval blockades).

**9 Skills:**

| Skill | Primary Source | API |
|---|---|---|
| `fleet_position_tracker` | USNI Fleet Tracker | RSS/scrape |
| `maritime_safety_monitor` | NGA Maritime Safety | `https://msi.nga.mil/api/publications/query` |
| `piracy_alert_monitor` | NGA ASAM | `https://msi.nga.mil/api/publications/query?type=ASAM` |
| `chokepoint_monitor` | ReliefWeb + GDELT | Composite |
| `submarine_cable_monitor` | TeleGeography | `https://www.submarinecablemap.com/api/v3/` |
| `port_disruption_monitor` | HDX/WFP + USCG | `https://data.humdata.org/api/` |
| `shipping_market_monitor` | Yahoo Finance ETFs | BDRY, SBLK, ZIM + Flexport OTI |
| `uscg_alert_monitor` | USCG Newsroom | `https://www.news.uscg.mil/Press-Releases/` (RSS) |
| `maritime_calendar` | Aggregated | — |

---

### 4. `conflict_risk` 🟡 MEDIUM-HIGH PRIORITY

**Asset-first on:** conflict events, weapons systems, CBRN incidents

**Why high value:** Cross-sector early-warning layer. Nuclear risk, arms embargoes, and airstrike events enrich every other agent that tracks physical assets.

**10 Skills:** arms_embargo_tracker, airstrike_monitor, cbrn_alert_monitor, nuclear_risk_tracker, sanctions_enforcement_tracker, protest_unrest_monitor (GDELT), siege_blockade_monitor (ReliefWeb), satellite_fire_monitor (NASA FIRMS), terrorism_tracker (GDELT), conflict_calendar

---

### 5. `space_systems` 🟡 MEDIUM PRIORITY

**Asset-first on:** missions, satellite names, orbital regimes

**Why high value:** GPS denial affects `autonomous_vehicles`; space weather affects `cybersecurity`; launch cadence affects `aerospace` valuation.

**10 Skills:** launch_tracker (Launch Library 2), satellite_catalog_monitor (CelesTrak), space_weather_monitor (NOAA SWPC), gps_gnss_monitor, debris_conjunction_tracker (SOCRATES), iss_position_tracker, asteroid_monitor (NASA CNEOS), satnogs_monitor, earth_observation_monitor (Sentinel-2), space_calendar

---

## Three Signal Enrichment Patterns

### Pattern 1: GDELT Temporal Events
**Adds value to:** aerospace, conflict_risk, fintech, rare_earth, maritime_logistics

GDELT emits structured events (actor, action, location, tone, Goldstein scale) every 15 minutes.

```python
# Proposed shared module: src/super_agents/common/gdelt_fetcher.py
fetch_gdelt_events(actor=None, country=None, event_type=None, days=7) -> list[dict]
```
**API:** `https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&format=json`

---

### Pattern 2: OFAC/OpenSanctions Cross-Reference
**Adds value to:** rare_earth, fintech, aerospace, geopolitical_risk, maritime_logistics

Every watchlist entity can be screened against OFAC SDN + OpenSanctions in a single call.

```python
# Proposed shared module: src/super_agents/common/sanctions_check.py
is_sanctioned(entity_name: str, country: str | None = None) -> SanctionsResult
```
**APIs:** OFAC SDN XML + `https://api.opensanctions.org/match/default`

---

### Pattern 3: NOAA/NASA Earth Observation
**Adds value to:** rare_earth (mine fires), renewable_energy (solar/wind disruption), conflict_risk (fire correlation), humanitarian_ops (disaster early warning)

```python
# Proposed shared module: src/super_agents/common/earth_obs_fetcher.py
fetch_firms_fires(bbox: tuple, days: int = 1) -> list[dict]  # NASA FIRMS
fetch_space_weather_alerts() -> list[dict]                    # NOAA SWPC
fetch_severe_weather_alerts(region: str) -> list[dict]        # NWS API
```

---

## Global Risk Layer

A queryable shared library that any sector agent imports to context-enrich its findings.

```
src/super_agents/common/risk_layer/
    __init__.py           # get_risk_context(entity_name, country_code) -> RiskContext
    sanctions.py          # OFAC + OpenSanctions
    conflict.py           # GDELT + ReliefWeb active conflict zones
    weather.py            # NWS alerts + NASA FIRMS fires
    cyber.py              # CISA KEV + IODA internet outages
    schema.py             # RiskContext frozen dataclass
```

**Usage pattern:**
```python
from super_agents.common.risk_layer import get_risk_context

ctx = get_risk_context(entity_name="VALE S.A.", country_code="BR")
if ctx.sanctions_hit:
    finding["severity"] = "critical"
if ctx.active_conflict_nearby:
    finding["severity"] = max(finding["severity"], "high")
```

**Data sources per module:**

| Module | API | Refresh |
|---|---|---|
| `sanctions.py` | OFAC SDN XML + OpenSanctions | Daily |
| `conflict.py` | GDELT + ReliefWeb | Hourly |
| `weather.py` | NWS `api.weather.gov/alerts/active` + NASA FIRMS | 6 hrs |
| `cyber.py` | CISA KEV JSON + IODA API | 4 hrs |

---

## Cybersecurity Agent — Complete Skill Design

The `.agent_cybersecurity/` stub currently has `config.yaml` but **no scripts**. This is the highest ROI next step — 11 runnable skills, all open APIs, no authentication required for most.

**11 Skills:**

| Skill | Scripts | Source | Auth |
|---|---|---|---|
| `cisa_advisory_tracker` | `fetch_cisa_advisories` | CISA RSS | None |
| `kev_catalog_monitor` | `fetch_kev_catalog`, `detect_kev_additions` | CISA KEV JSON | None |
| `nvd_cve_tracker` | `fetch_nvd_cves`, `score_cve_exposure` | NIST NVD API v2 | Optional API key |
| `ics_cert_monitor` | `fetch_ics_advisories` | ICS-CERT RSS | None |
| `internet_outage_monitor` | `fetch_ioda_outages`, `detect_outage_anomalies` | IODA API | None |
| `bgp_hijack_monitor` | `fetch_ripe_bgp_alerts` | RIPE Stat API | None |
| `censorship_monitor` | `fetch_ooni_measurements` | OONI API | None |
| `cloudflare_radar_monitor` | `fetch_ddos_signals`, `fetch_traffic_anomalies` | Cloudflare Radar API | Free API token |
| `grid_monitor` | `fetch_ercot_grid_status` | ERCOT API | None |
| `vulnerability_calendar` | `build_patch_calendar` | Aggregated | — |
| `data_quality` | `audit_stale_records` | Internal | — |

**Key API URLs:**
- CISA KEV: `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json`
- NIST NVD: `https://services.nvd.nist.gov/rest/json/cves/2.0`
- IODA: `https://ioda.inetintel.cc.gatech.edu/api/v2/signals/raw`
- RIPE: `https://stat.ripe.net/data/bgp-updates/data.json`
- OONI: `https://api.ooni.io/api/v1/measurements`
- Cloudflare Radar: `https://api.cloudflare.com/client/v4/radar/`
- ERCOT: `https://www.ercot.com/api/1/services/read/`

**Package layout:**
```
src/super_agents/cybersecurity/
    __init__.py
    watchlist.py      # CVE IDs, ASNs, critical infra system names
    paths.py
    io_utils.py
    cisa.py           # fetch_cisa_advisories(), fetch_kev_catalog()
    nvd.py            # fetch_nvd_cves(), score_cve_exposure()
    ics_cert.py       # fetch_ics_advisories()
    ioda.py           # fetch_ioda_outages(), detect_outage_anomalies()
    ripe.py           # fetch_ripe_bgp_alerts()
    ooni.py           # fetch_ooni_measurements()
    cloudflare_radar.py
    grid.py           # fetch_ercot_grid_status()
    calendar.py       # build_patch_calendar()
    dashboard.py
```

---

## Implementation Sequencing

```
Phase 1 — Shared Signal Infrastructure (Week 1-2)
  1. src/super_agents/common/gdelt_fetcher.py
  2. src/super_agents/common/sanctions_check.py
  3. src/super_agents/common/earth_obs_fetcher.py
  4. src/super_agents/common/risk_layer/ (4 modules)

Phase 2 — Cybersecurity Agent (Week 2-3, highest ROI)
  5. src/super_agents/cybersecurity/ package (11 modules)
  6. .agent_cybersecurity/ skill scripts (14 scripts)
  7. data/seeds/cybersecurity_*_watchlist.csv

Phase 3 — New High-Value Agents (Week 3-5)
  8. defense_intelligence agent
  9. geopolitical_risk agent
  10. maritime_logistics agent

Phase 4 — Existing Agent Enrichment (Week 5-6)
  11. aerospace: +6 skills (ADS-B military, NATO, carrier groups)
  12. fintech: +6 skills (Fear & Greed, FRED, CFTC, Fed balance sheets, prediction markets)
  13. rare_earth: +3 skills (BIS, OFAC overlay, UN sanctions)

Phase 5 — Remaining New Agents (Week 7+)
  14. conflict_risk agent
  15. space_systems agent
```

---

## Reference Files for Implementation

| Pattern to follow | File |
|---|---|
| API fetcher with pagination | `src/super_agents/aerospace/usaspending.py` |
| Run summary writer | `src/super_agents/common/run_summary.py` |
| Path resolver | `src/super_agents/common/paths.py` |
| Watchlist frozen dataclass + CSV | `src/super_agents/aerospace/watchlist.py` |
| Sector `__init__.py` export pattern | `src/super_agents/biotech/__init__.py` |
