# Project Overview

Updated: 2026-03-15

## What This Repo Is

Super_Agents is a multi-sector, asset-first research and execution framework in Python. Each agent tracks the thing that creates or destroys value in its sector, then enriches that asset with regulatory, financial, and open-source signals.

The current repo is a mixed state:

- Some sectors already have `src/super_agents/<sector>/` packages.
- Some runnable agents still exist only as `.agent_*` script definitions.
- The dashboard has live pages for core fleet operations plus early cybersecurity and risk-layer surfaces.
- The docs are now anchored by [EXECUTION_PLAN.md](EXECUTION_PLAN.md), which is the active sequencing plan.

## Current Repo Surface

### Runnable Agents

The CLI currently exposes 10 runnable agents from script-backed `.agent_*` folders:

| Agent | Skills | Scripts | Matching `src/super_agents/<agent>/` package | Dedicated dashboard page | Notes |
|---|---:|---:|---|---|---|
| aerospace | 12 | 14 | Yes | No | Generic dashboard coverage only |
| autonomous_vehicles | 4 | 4 | No | No | Runnable scripts, no sector package yet |
| biotech | 11 | 21 | Yes | No | Strongest artifact coverage in `dashboards/` |
| cybersecurity | 2 | 2 | Yes | Yes | MVP exists; page is real, backend scope is still narrow |
| fintech | 4 | 4 | Yes | No | Generic dashboard coverage only |
| gaming | 8 | 10 | Yes | No | Generic dashboard coverage only |
| quantum | 5 | 5 | No | No | Runnable scripts, no sector package yet |
| rare_earth | 9 | 11 | No | No | Runnable scripts, no sector package yet |
| renewable_energy | 8 | 8 | No | No | Runnable scripts, partial committed artifacts |
| simulation | 1 | 6 | No | Yes | Backed by MiroFish integration and runtime tooling |

### Non-Runnable Agent Folders

These agent folders exist on disk but are not currently CLI-visible because they have no runnable scripts:

- `cannabis_psychedelics`
- `meddevice`
- `space`

### Current Python Package Layout

Current top-level packages under `src/super_agents/`:

- `aerospace`
- `biotech`
- `common`
- `cybersecurity`
- `db`
- `fintech`
- `gaming`
- `integrations`
- `llm`

There are no `src/super_agents/` packages yet for `autonomous_vehicles`, `quantum`, `rare_earth`, `renewable_energy`, or `simulation`.

## Dashboard Surface

There are 9 Streamlit pages in `dashboards/pages/`:

| Page | Status | Notes |
|---|---|---|
| `1_Fleet_Overview.py` | Live | Fleet summary driven by discovered runnable agents |
| `2_Agent_Detail.py` | Live | Generic per-agent detail view |
| `3_Run_History.py` | Live | Reads archived run summaries |
| `4_Findings_Board.py` | Live | Already imports `render_risk_badge()` |
| `5_Calendars.py` | Live | Aggregates saved calendar-style JSON files |
| `6_LLM_Operations.py` | Live | LLM operations surface |
| `7_Simulation_Engine.py` | Live | MiroFish runtime surface |
| `8_Cybersecurity.py` | Live | Artifact-driven MVP page for KEV and patch calendar |
| `13_Risk_Layer.py` | Live, partial | UI exists but still uses mock risk data |

Current dashboard component surface:

- `dashboards/components/risk_badge.py` exists and is reused already, but it is still mock-backed.

## Artifact Baseline

Committed dashboard artifacts are uneven across agents.

Currently present in `dashboards/`:

- `*_current_status.json` for `aerospace`, `biotech`, `fintech`, `gaming`, and `renewable_energy`
- `*_run_latest.json` and `*_run_latest.md` for `biotech`, `fintech`, `gaming`, and `renewable_energy`
- `*_findings_latest.json` for `biotech` and `gaming`

Not currently committed:

- Cybersecurity artifacts such as `cybersecurity_kev_latest.json` and `cybersecurity_patch_calendar.json`
- A shared formal artifact-contract document covering all saved JSON outputs

This uneven artifact coverage is one of the main reasons the active plan prioritizes contract hardening over new expansion.

## Test Health

Point-in-time local result from `python -m pytest -q` on 2026-03-15:

- 71 passed
- 4 failed

Observed failure cluster:

- All 4 failures are in `tests/test_cli_discovery.py`
- Failures are caused by Windows temp-directory permission errors during temporary-directory setup and cleanup

Current test layout on disk:

- Top-level: `tests/test_cli_discovery.py`, `tests/test_security.py`
- Package suites: `tests/test_common/`, `tests/test_biotech/`, `tests/test_cybersecurity/`, `tests/test_fintech/`, `tests/test_gaming/`
- `tests/test_aerospace/` exists but currently contains no test files

## Current Priorities

Detailed sequencing lives in [EXECUTION_PLAN.md](EXECUTION_PLAN.md). Summary:

1. Realign active docs and lane boards to the current repo state.
2. Finish the cybersecurity MVP as a reliable artifact-backed workflow.
3. Implement a real `super_agents.common.risk_layer` backend and remove mock risk UI behavior.
4. Formalize the dashboard artifact contract and add regression coverage around shared surfaces.
5. Resume sector and agent expansion only after the core contract is stable.

## Known Gaps

- `dashboards/components/risk_badge.py` and `dashboards/pages/13_Risk_Layer.py` still use mock risk data.
- Several runnable agents do not yet have matching `src/super_agents/<agent>/` packages.
- Artifact coverage in `dashboards/` is inconsistent across agents.
- `docs/architecture.md` does not yet serve as a complete artifact-contract spec.
- `tests/test_cli_discovery.py` currently fails on Windows temp-directory handling.
- `tests/test_aerospace/` exists but has no active test files.

## Documentation Map

| Document | Purpose | Status |
|---|---|---|
| [README.md](README.md) | Docs index | Current |
| [EXECUTION_PLAN.md](EXECUTION_PLAN.md) | Active sequencing plan | Current |
| [BACKEND_TASKS.md](BACKEND_TASKS.md) | Backend lane board | Current after repo-audit refresh |
| [FRONTEND_TASKS.md](FRONTEND_TASKS.md) | Frontend lane board | Current after repo-audit refresh |
| [architecture.md](architecture.md) | Platform and artifact-contract reference | Needs follow-up update |
| [implementation_plan.md](implementation_plan.md) | Historical phased plan | Historical |
| [current_status_2026-03-15.md](current_status_2026-03-15.md) | Point-in-time snapshot | Historical |
| [status_review_and_next_steps_2026-03-15.md](status_review_and_next_steps_2026-03-15.md) | Dated review | Historical |

## Maintenance Rules

When the repo changes materially:

1. Update [EXECUTION_PLAN.md](EXECUTION_PLAN.md) if phase order or ownership changed.
2. Update [BACKEND_TASKS.md](BACKEND_TASKS.md) and [FRONTEND_TASKS.md](FRONTEND_TASKS.md) when lane priorities or completion state changed.
3. Update [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) when the live repo surface changed in a way that affects onboarding or planning.
4. Keep exact counts only when they are verified from the live repo or from a fresh command result.
