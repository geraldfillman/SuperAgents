# Backend Tasks

Updated: 2026-03-15

## Backend Lane Ownership

Use this board for backend-only work that can run in parallel with frontend execution.

- Primary ownership: `src/super_agents/`, `.agent_*/`, `tests/`, `schema/`, `data/seeds/`, source fetchers, normalization code, and dashboard artifact writers.
- Do not use this board for Streamlit page layout or visualization work under `dashboards/pages/`.
- Coordinate before editing shared integration files: `dashboards/dashboard_data.py`, `src/super_agents/common/status.py`, `src/super_agents/common/run_summary.py`, and `docs/architecture.md`.
- Backend handoff rule: define or update the artifact contract first, then let the frontend lane consume it.

## Current Backend Baseline

Verified from the live repo:

- Current sector packages: `aerospace`, `biotech`, `cybersecurity`, `fintech`, `gaming`
- Current runnable script-backed agents: 10
- Current cybersecurity MVP package: `src/super_agents/cybersecurity/`
- Shared helpers already present: `src/super_agents/common/env.py`, `paths.py`, `io_utils.py`, `status.py`, `run_summary.py`
- Current local test result: `python -m pytest -q` -> 71 passed, 4 failed

Current failure cluster:

- `tests/test_cli_discovery.py`
- Root cause observed during the run: Windows temp-directory permission errors

## Completed Or Verified

- [x] CLI auto-discovers runnable agents from `.agent_*` directories with script-backed skills.
- [x] Shared common config and environment helpers exist under `src/super_agents/common/`.
- [x] Shared dashboard-data and artifact-writer tests exist under `tests/test_common/`.
- [x] Cybersecurity MVP backend exists:
  - `src/super_agents/cybersecurity/cisa.py`
  - `src/super_agents/cybersecurity/calendar.py`
  - `src/super_agents/cybersecurity/watchlist.py`
  - `.agent_cybersecurity/skills/threat_landscape/scripts/fetch_kev_catalog.py`
  - `.agent_cybersecurity/skills/calendar/scripts/build_patch_calendar.py`
- [x] Cybersecurity backend tests exist:
  - `tests/test_cybersecurity/test_cisa.py`
  - `tests/test_cybersecurity/test_watchlist.py`
- [x] Simulation runtime tooling is script-backed and dashboard-visible through `.agent_simulation/` and `dashboards/pages/7_Simulation_Engine.py`.

## Active Now

### B1 - Fix the current red test baseline

Why now: the repo is close to green, and the failing tests are concentrated in one area.

- [ ] Fix Windows temp-directory failures in `tests/test_cli_discovery.py`
- [ ] Re-run `python -m pytest -q` and capture the clean baseline in docs only after it passes

### B2 - Implement the real Risk Layer backend

Why now: the dashboard already exposes risk UI, but it is still driven by mock data.

- [ ] Create `src/super_agents/common/risk_layer/__init__.py`
- [ ] Create `src/super_agents/common/risk_layer/schema.py`
- [ ] Implement backend modules for:
  - sanctions
  - conflict
  - weather
  - cyber
- [ ] Define a stable `RiskContext` contract used by dashboards and agents
- [ ] Add unit tests for the new backend package

### B3 - Formalize the dashboard artifact contract

Why now: backend/frontend parallel work is already gated by shared JSON shapes.

- [ ] Document the contract in `docs/architecture.md`
- [ ] Make current-status, latest-run, findings, and calendar artifacts consistent where possible
- [ ] Define freshness fields and missing-data behavior explicitly
- [ ] Add regression coverage around shared writers and readers if fields change

### B4 - Harden the cybersecurity MVP

Why now: cybersecurity is real, but still too narrow and not yet a fully consistent artifact pipeline.

- [ ] Make the cybersecurity workflow reliably emit:
  - current status
  - latest run summary
  - findings
  - KEV dataset artifact
  - patch calendar artifact
- [ ] Standardize filenames and field names for those artifacts
- [ ] Add freshness metadata so the dashboard can show stale or missing data honestly

## Next

### B5 - Expand cybersecurity sources after the contract is stable

- [ ] Add the next highest-value live sources after B2-B4 land:
  - NVD
  - IODA
  - RIPE
  - OONI
  - Cloudflare Radar
- [ ] Keep each new source behind a saved artifact instead of wiring raw fetch logic directly into pages

### B6 - Normalize runnable agents that still lack sector packages

- [ ] Create package backfills for:
  - `autonomous_vehicles`
  - `quantum`
  - `rare_earth`
  - `renewable_energy`
- [ ] Move reusable parsing and artifact logic out of one-off scripts into those packages

## Later

### B7 - Controlled expansion

Do not treat this as current work until B1-B4 are complete.

- [ ] Add new agents only after the shared contract and risk layer are stable
- [ ] Follow the order in [EXECUTION_PLAN.md](EXECUTION_PLAN.md):
  1. geopolitical risk
  2. defense intelligence
  3. maritime logistics
  4. conflict risk

### B8 - Test coverage backlog

- [ ] Add active tests under `tests/test_aerospace/`
- [ ] Expand sector coverage for script-backed agents as they gain packages
- [ ] Add more contract-level tests around artifact compatibility across agents

## Not Current Work

The old board treated multiple new agents and pages as immediate. That is no longer the right order.

Do not start these before B1-B4 are done:

- large multi-agent expansion waves
- greenfield page work that depends on undefined artifacts
- package creation for non-runnable stubs such as `space`, `meddevice`, and `cannabis_psychedelics`
