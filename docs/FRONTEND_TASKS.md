# Frontend Tasks

Updated: 2026-03-15

## Frontend Lane Ownership

Use this board for frontend-only work that can run in parallel with backend execution.

- Primary ownership: `dashboards/pages/`, `dashboards/components/`, page filters, charts, tables, navigation, and operator workflow.
- Do not use this board for ingestion scripts, sector packages, API fetchers, or artifact-writer logic under `src/super_agents/` and `.agent_*/`.
- Coordinate before editing shared integration files: `dashboards/dashboard_data.py`, `src/super_agents/common/status.py`, `src/super_agents/common/run_summary.py`, and `docs/architecture.md`.
- Frontend handoff rule: consume backend artifacts; if a required field does not exist, add a backend task instead of inventing page-local data shapes.

## Current Frontend Baseline

Verified from the live repo:

- There are 9 Streamlit pages under `dashboards/pages/`
- `dashboards/components/risk_badge.py` exists
- `dashboards/pages/8_Cybersecurity.py` exists
- `dashboards/pages/13_Risk_Layer.py` exists
- `dashboards/pages/4_Findings_Board.py` already imports and uses `render_risk_badge()`
- `dashboards/dashboard_data.py` discovers runnable agents dynamically from `.agent_*`

## Completed Or Verified

- [x] Core dashboard pages are live:
  - `1_Fleet_Overview.py`
  - `2_Agent_Detail.py`
  - `3_Run_History.py`
  - `4_Findings_Board.py`
  - `5_Calendars.py`
  - `6_LLM_Operations.py`
  - `7_Simulation_Engine.py`
- [x] Cybersecurity page exists:
  - `8_Cybersecurity.py`
- [x] Global risk page exists:
  - `13_Risk_Layer.py`
- [x] Reusable risk badge component exists:
  - `dashboards/components/risk_badge.py`

## Current Page Status

| Surface | Status | Next action |
|---|---|---|
| Fleet Overview | Live | Make partial and missing-artifact states clearer |
| Agent Detail | Live | Expose uneven artifact coverage more clearly |
| Run History | Live | Leave stable until contract fields change |
| Findings Board | Live | Replace mock-backed risk badges after backend handoff |
| Calendars | Live | Expand only after more saved calendar artifacts exist |
| LLM Operations | Live | Not current priority |
| Simulation Engine | Live | Not current priority |
| Cybersecurity | Live, partial | Improve freshness and missing-artifact presentation |
| Risk Layer | Live, partial | Replace mock data with backend contract |

## Active Now

### F1 - Wire the Risk Layer UI to real backend data

Why now: the UI already exists and is reused, but it still shows mock outputs.

- [ ] Replace `get_risk_context_mock()` usage in `dashboards/components/risk_badge.py`
- [ ] Replace placeholder data in `dashboards/pages/13_Risk_Layer.py`
- [ ] Make unavailable data explicit instead of showing synthetic certainty
- [ ] Keep the badge contract aligned with backend `RiskContext`

### F2 - Harden the Cybersecurity page

Why now: the page is real, but it currently assumes artifacts that are not consistently present.

- [ ] Make `8_Cybersecurity.py` show freshness, missing artifact state, and empty-state guidance clearly
- [ ] Remove "MVP" wording once the page reflects actual artifact coverage instead of intent
- [ ] Only add visualizations that are backed by saved artifacts

### F3 - Make partial and mock-backed states visible in the generic pages

Why now: the fleet is heterogeneous, and the UI should stop implying full parity across agents.

- [ ] Update Fleet Overview to distinguish:
  - artifact-backed
  - partial
  - mock-backed
  - no recent artifacts
- [ ] Update Agent Detail to surface which artifacts are actually available per agent
- [ ] Update Findings Board once the real risk backend is available so badges stop using mock behavior

## Next

### F4 - Shared page polish after backend contract stabilization

- [ ] Add better filtering and severity handling to Findings Board
- [ ] Expand Calendars only when more agents emit stable calendar artifacts
- [ ] Add risk context hooks to the generic pages after `RiskContext` is stable

### F5 - Minimal regression coverage for critical dashboard surfaces

- [ ] Add smoke coverage for `dashboards/dashboard_data.py` changes if backend contract fields evolve
- [ ] Add targeted tests around the risk badge adapter once it stops using mock logic

## Later

### F6 - Controlled expansion pages

Do not treat these as current work until F1-F4 are complete and the backend artifacts exist.

- [ ] Geopolitical risk
- [ ] Defense intelligence
- [ ] Maritime logistics
- [ ] Conflict risk

### F7 - Lower-priority backlog

- [ ] Fleet Overview enhancements beyond status clarity
- [ ] Findings export and richer drill-downs
- [ ] Calendar layout enhancements
- [ ] LLM Operations polish
- [ ] Simulation comparison and reporting
- [ ] Mobile-specific layout work

## Not Current Work

The old frontend board treated several greenfield pages as immediate. That is no longer the right order.

Do not start:

- new sector pages that depend on undefined backend artifacts
- UI work that hardcodes mock datasets into shared components
- expansion work that assumes all agents already have equivalent artifact coverage
