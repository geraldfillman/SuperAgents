# Dashboard v2 — Data Flow, Presentation & UI Plan

**Date:** 2026-03-16
**Status:** Draft — awaiting review
**Current version:** Dashboard v0.3.0 (Streamlit, 12 pages, file-backed data)

---

## Current State Assessment

### What Works
- 14 sector agents discoverable from `.agent_*` directories
- Crucix signal routing with SQLite-backed SignalStore
- Simulation engine with scenario YAML and MiroFish integration
- Consistent theme system (severity icons, sector colors, CSS)
- `dashboard_data.py` centralizes all data loading with `@st.cache_data`

### Pain Points

| Area | Problem |
|------|---------|
| **Data Flow** | File-coupled — agents write JSON artifacts to disk, dashboard reads them. No event-driven updates. |
| **Data Flow** | Two separate DBs (signals.db in `data/signals/`, signals.db in `data/`). No unified query layer. |
| **Data Flow** | No intermediate processing — raw agent output goes straight to dashboard with minimal transformation. |
| **Presentation** | 12 flat sidebar pages — no hierarchy or grouping in the UI despite the logical 4-group structure. |
| **Presentation** | No cross-page filtering (e.g., filter by sector everywhere, filter by time range). |
| **Presentation** | Charts are minimal — mostly metric cards and tables. |
| **UI Flow** | No "home → drill-down" navigation pattern. Every page is a peer. |
| **UI Flow** | No notification or alert system — findings require manual page visits. |
| **UI Flow** | Settings page exists but doesn't control data refresh, agent scheduling, or alerts. |

---

## Phase 1: Unified Data Layer (Foundation)

**Goal:** Single source of truth for all dashboard data, queryable and event-aware.

### 1.1 — Unified Data Store

Create `src/super_agents/data/unified_store.py`:

```
UnifiedStore (SQLite, single DB file: data/super_agents.db)
├── signals        — from Crucix (migrate from SignalStore)
├── runs           — agent execution history (migrate from JSON files)
├── findings       — cross-sector discoveries (migrate from JSON files)
├── events         — calendar/catalyst events
├── metrics        — LLM usage, cost, token counts
└── agent_status   — last-known state per agent
```

**Key design decisions:**
- Single SQLite WAL-mode database replaces scattered JSON files + two signal DBs
- Every table has `created_at`, `updated_at`, `sector` columns for universal filtering
- JSON payloads stored in TEXT columns (SQLite JSON1 extension for queries)
- Backward-compatible: keep JSON file writers during migration, add DB writers in parallel

### 1.2 — Data Access Layer (DAL)

Create `src/super_agents/data/dal.py`:

```python
class DashboardDAL:
    """Single entry point for all dashboard queries."""

    def fleet_summary() -> FleetSummary
    def agent_detail(name: str) -> AgentDetail
    def runs(sector: str = None, since: str = None, limit: int = 50) -> list[Run]
    def findings(severity: str = None, sector: str = None) -> list[Finding]
    def signals(topic: str = None, sector: str = None) -> list[Signal]
    def risk_summary() -> RiskSummary
    def calendar_events(sector: str = None, month: str = None) -> list[Event]
    def llm_metrics(since: str = None) -> LLMMetrics
```

**Benefits:**
- Dashboard pages become thin — just call DAL methods and render
- Caching moves from per-page `@st.cache_data` to DAL-level with configurable TTL
- Unit-testable without Streamlit
- Same DAL can serve a future REST API or CLI reporting

### 1.3 — Event Bus (Lightweight)

Create `src/super_agents/data/events.py`:

```
EventBus (file-based + optional SQLite)
├── emit(event_type, payload)     — agents call this after completing work
├── subscribe(event_type, handler) — dashboard/alerts listen
└── poll(since) → list[Event]     — for Streamlit polling
```

- Phase 1: Simple file-based (write JSON event to `data/events/` directory)
- Phase 2: SQLite `events` table in UnifiedStore
- Phase 3 (future): Redis pub/sub or SSE for real-time

---

## Phase 2: Data Presentation & Visualization

**Goal:** Transform raw data into actionable intelligence with proper charts and cross-filtering.

### 2.1 — Global Filter Bar

Add a persistent filter sidebar component (`dashboards/components/filters.py`):

```
Global Filters (persisted in st.session_state)
├── Sector selector     — multi-select, applies to ALL pages
├── Time range          — preset (24h, 7d, 30d, custom)
├── Severity filter     — for findings/risk pages
└── Agent filter        — for run history/detail pages
```

Every page reads these filters and passes them to the DAL. No more per-page filtering logic.

### 2.2 — Chart Components Library

Create `dashboards/components/charts.py` with reusable Plotly/Altair charts:

| Chart | Used On | Data Source |
|-------|---------|-------------|
| **Sector Heatmap** | Home, Risk Layer | signal density by sector × time |
| **Run Timeline** | Fleet Overview, Run History | runs over time, colored by status |
| **Finding Severity Treemap** | Findings Board | findings grouped by sector → severity |
| **Signal Flow Sankey** | Crucix Data Hub | source → topic → sector routing |
| **Cost Burn Chart** | LLM Operations | cumulative token cost over time |
| **Agent Activity Sparklines** | Fleet Overview | mini-charts per agent row |
| **Risk Radar** | Risk Layer | spider chart of risk categories |
| **Calendar Heatmap** | Calendars | GitHub-style event density calendar |

### 2.3 — Card Components

Create `dashboards/components/cards.py`:

- **AgentCard** — icon, name, last run, skill count, status badge, sparkline
- **FindingCard** — severity badge, title, sector tag, timestamp, expand for details
- **SignalCard** — source icon, topic, confidence pill, routed-to tags
- **SimulationCard** — scenario name, tick count, alert count, variable sparkline

Cards replace raw tables for the primary views. Tables remain available as a toggle ("Card view | Table view").

### 2.4 — Data Tables with Export

Upgrade all tables to use `st.dataframe` with:
- Column sorting
- CSV/JSON download button
- Row expansion for detail view
- Pagination for large datasets

---

## Phase 3: UI Flow & Navigation

**Goal:** Intuitive navigation hierarchy with a clear home → category → detail drill-down.

### 3.1 — Navigation Restructure

**Current (flat):**
```
Sidebar:
  01 Fleet Overview
  02 Agent Detail
  03 Run History
  04 Findings Board
  05 Crucix Data Hub
  06 Risk Layer
  07 Calendars
  08 Scenario Simulations
  09 Simulation Engine
  10 Cybersecurity
  11 LLM Operations
  12 Settings
```

**Proposed (grouped with hierarchy):**
```
Home (Command Center)
│
├── Monitoring
│   ├── Fleet Overview        — agent grid with cards + sparklines
│   ├── Agent Detail          — drill-down from fleet (not a standalone page)
│   └── Run History           — filterable run log with timeline chart
│
├── Intelligence
│   ├── Findings Board        — severity-grouped cards with treemap
│   ├── Signal Explorer       — Crucix signals with Sankey flow diagram
│   └── Risk Dashboard        — radar chart + sector heatmap + alerts
│
├── Simulations
│   ├── Scenario Builder      — combine scenario simulations + simulation engine
│   └── MiroFish Bundles      — published bundle management
│
├── Operations
│   ├── Cybersecurity         — threat feeds
│   └── LLM Metrics           — cost, tokens, model performance
│
└── Settings
    ├── Agent Configuration
    ├── Crucix Setup
    ├── Alert Rules
    └── Dashboard Preferences
```

**Key changes:**
- **Merge pages 08 + 09** into a single "Simulations" section (scenario builder + engine were split unnecessarily)
- **Agent Detail becomes a drill-down**, not a standalone page — click an agent on Fleet Overview to see its detail
- **Home becomes a Command Center** with KPIs, recent alerts, and quick-action buttons
- **Sidebar groups are collapsible** using Streamlit's native section support

### 3.2 — Command Center (New Home Page)

Replace the current minimal home page with a dense, actionable command center:

```
┌─────────────────────────────────────────────────────────┐
│  SUPER AGENTS — Command Center                          │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│ 14       │ 3        │ 7        │ 2        │ Crucix:     │
│ Agents   │ Running  │ Findings │ Alerts   │ Active      │
│ Active   │ Now      │ Today    │ Critical │ 27 sources  │
├──────────┴──────────┴──────────┴──────────┴─────────────┤
│                                                         │
│  [Recent Alerts]              [Signal Flow (24h)]       │
│  ┌─ CRITICAL: Rare earth...   ┌─ Sankey: sources →     │
│  ├─ HIGH: FDA approval...     │  sectors (mini)        │
│  └─ MEDIUM: Cyber vuln...     └────────────────────────│
│                                                         │
│  [Sector Status Grid]                                   │
│  ┌──────┬──────┬──────┬──────┐                         │
│  │ Bio  │ Fin  │ Cyber│ Aero │  (colored by health)   │
│  │ ● OK │ ● OK │ ●WARN│ ● OK │                         │
│  └──────┴──────┴──────┴──────┘                         │
│                                                         │
│  [Latest Runs]                [Upcoming Catalysts]      │
│  agent   | skill   | status  date  | event | sector    │
│  biotech | fda     | ✓ pass  03/17 | PDUFA | biotech   │
│  gaming  | steam   | ✓ pass  03/18 | GDC   | gaming    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.3 — Drill-Down Navigation Pattern

Implement consistent drill-down using `st.session_state`:

```
Fleet Overview → click agent card → Agent Detail (filtered)
Findings Board → click finding → Finding Detail (inline expander)
Signal Explorer → click source → Source Detail + signal history
Risk Dashboard → click sector → Sector Risk Breakdown
Run History → click run → Run Detail with logs + artifacts
```

Each drill-down sets `st.session_state["selected_*"]` and the target page reads it.

### 3.4 — Alert & Notification System

Create `dashboards/components/alerts.py`:

- **Alert Bar** — persistent banner at top of every page showing critical findings
- **Alert Rules** — configurable in Settings (e.g., "notify if finding severity >= HIGH in sector biotech")
- **Alert History** — viewable log of all triggered alerts
- Phase 1: Visual alerts in dashboard
- Phase 2: Email/Slack notifications via webhook (future)

---

## Phase 4: Data Flow Optimization

**Goal:** Reduce latency between agent execution and dashboard visibility.

### 4.1 — Agent Output Pipeline

```
Current:  Agent → write JSON to disk → dashboard reads file on page load
Proposed: Agent → write to UnifiedStore DB → emit event → dashboard polls events
```

Update agent skill scripts to call:
```python
from super_agents.data.unified_store import store
store.save_run(run_result)
store.save_findings(findings)
events.emit("run_completed", {"agent": name, "run_id": id})
```

### 4.2 — Crucix → Store Pipeline

```
Current:  Crucix sweep → signals.db (standalone) → dashboard reads separate DB
Proposed: Crucix sweep → bridge.py → UnifiedStore.signals table → event emitted
```

The bridge already exists (`src/super_agents/integrations/crucix/bridge.py`). Update it to write to UnifiedStore instead of the standalone signal DB.

### 4.3 — Caching Strategy

```
Layer 1: SQLite WAL mode (fast concurrent reads)
Layer 2: DAL-level in-memory cache (configurable TTL per query type)
Layer 3: Streamlit @st.cache_data on page-level transformations only
```

Remove the current pattern of caching raw data loading in `dashboard_data.py` — that moves to the DAL.

---

## Implementation Order

| Phase | Effort | Priority | Dependencies |
|-------|--------|----------|--------------|
| **1.1** Unified Store schema | Medium | P0 | None |
| **1.2** DAL | Medium | P0 | 1.1 |
| **3.1** Navigation restructure | Small | P0 | None (can parallel with 1.x) |
| **3.2** Command Center home | Medium | P1 | 1.2 (needs DAL queries) |
| **2.1** Global filter bar | Small | P1 | 1.2 |
| **2.2** Chart components | Medium | P1 | 1.2 |
| **2.3** Card components | Small | P1 | None |
| **3.3** Drill-down navigation | Small | P1 | 3.1 |
| **4.1** Agent output pipeline | Medium | P2 | 1.1 |
| **4.2** Crucix pipeline update | Small | P2 | 1.1 |
| **2.4** Data tables with export | Small | P2 | 1.2 |
| **3.4** Alert system | Medium | P2 | 1.2, 2.1 |
| **1.3** Event bus | Medium | P3 | 1.1 |
| **4.3** Caching optimization | Small | P3 | 1.2 |

### Suggested Sprint Plan

**Sprint 1 (Foundation):** 1.1 + 1.2 + 3.1 — Unified store, DAL, and nav restructure
**Sprint 2 (Visual):** 3.2 + 2.1 + 2.2 + 2.3 — Command center, filters, charts, cards
**Sprint 3 (Flow):** 3.3 + 4.1 + 4.2 + 2.4 — Drill-downs, pipeline updates, export
**Sprint 4 (Polish):** 3.4 + 1.3 + 4.3 — Alerts, event bus, caching

---

## File Structure (New/Modified)

```
src/super_agents/data/              # NEW — unified data layer
├── __init__.py
├── unified_store.py                # SQLite unified DB
├── dal.py                          # Dashboard Access Layer
├── events.py                       # Lightweight event bus
└── migrations/                     # Schema migrations
    └── 001_initial.sql

dashboards/
├── app.py                          # UPDATE — Command Center home
├── dashboard_data.py               # UPDATE — thin wrapper around DAL
├── components/
│   ├── theme.py                    # UPDATE — add nav group support
│   ├── filters.py                  # NEW — global filter bar
│   ├── charts.py                   # NEW — reusable chart library
│   ├── cards.py                    # NEW — agent/finding/signal cards
│   ├── alerts.py                   # NEW — alert bar + rules
│   ├── empty_state.py              # KEEP
│   └── risk_badge.py               # KEEP
├── pages/
│   ├── 01_Fleet_Overview.py        # UPDATE — card grid + sparklines
│   ├── 02_Agent_Detail.py          # UPDATE — drill-down target
│   ├── 03_Run_History.py           # UPDATE — timeline chart
│   ├── 04_Findings_Board.py        # UPDATE — treemap + cards
│   ├── 05_Signal_Explorer.py       # RENAME from Crucix_Data_Hub — Sankey
│   ├── 06_Risk_Dashboard.py        # RENAME from Risk_Layer — radar
│   ├── 07_Calendars.py             # UPDATE — heatmap calendar
│   ├── 08_Simulations.py           # MERGE 08+09 into one page
│   ├── 09_Cybersecurity.py         # RENUMBER from 10
│   ├── 10_LLM_Metrics.py           # RENUMBER from 11
│   └── 11_Settings.py              # RENUMBER from 12, add alert config
```

---

## Technical Notes

- **No new dependencies required** for Phase 1-2 (SQLite, Plotly already available via Streamlit)
- **Plotly** preferred over Altair for charts (better interactivity, Sankey support)
- **Backward compatibility**: JSON file writers remain active during migration; remove after validation
- **Testing**: DAL is unit-testable without Streamlit; chart components testable with snapshot tests
