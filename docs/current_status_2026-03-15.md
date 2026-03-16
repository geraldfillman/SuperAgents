# Super Agents Current Status

Date: 2026-03-15

This file is a time-boxed status snapshot. For the cleaned-up next-step sequence, see
`status_review_and_next_steps_2026-03-15.md`.

## Summary

Super Agents has moved beyond scaffold stage into an operational baseline:

- the CLI exposes 9 runnable agents
- the test suite is green with 32 passing tests
- aerospace is the strongest package-backed implementation
- biotech and gaming are operational, feed dashboard artifacts, and now have starter packages
- fintech now has starter package scaffolding and dashboard artifact wiring, but live-source
  hardening is still needed
- the Streamlit dashboard now discovers the runnable fleet dynamically

The main gap is consistency across sectors, not missing scaffolding.

## Repository-Verified Baseline

### Working now

- `python -m super_agents list` exposes:
  `aerospace`, `autonomous_vehicles`, `biotech`, `fintech`, `gaming`, `quantum`,
  `rare_earth`, `renewable_energy`, and `simulation`
- `python -m pytest -q` passes with `32 passed`
- `dashboards/app.py` exists with six pages under `dashboards/pages/`
- current-status and run artifacts already exist for `aerospace`, `biotech`, `gaming`, and
  `renewable_energy`
- fintech now writes current-status and run-summary artifacts from its license tracker flow
- aerospace seed watchlists exist in `data/seeds/company_watchlist.csv` and
  `data/seeds/system_watchlist.csv`
- biotech seed watchlists now exist in `data/seeds/biotech_company_watchlist.csv` and
  `data/seeds/biotech_product_watchlist.csv`
- gaming seed watchlists now exist in `data/seeds/gaming_studio_watchlist.csv`
- fintech seed watchlists now exist in `data/seeds/fintech_company_watchlist.csv`

### Still incomplete

- only `src/super_agents/aerospace/` is a full sector package today
- `biotech` and `gaming` now have starter package-backed helpers, but they are not yet at
  aerospace-level coverage
- `fintech` now has starter package-backed helpers, a seed watchlist, and a workflow, but its
  NMLS and OCC live-source paths still need hardening
- most other non-aerospace sectors still lack seed watchlists
- `cybersecurity` is still undiscoverable because `.agent_cybersecurity/config.yaml` is missing
- several sectors still do not emit consistent dashboard-ready status, findings, or calendar artifacts

## Completed In The Recent Session

### MiroFish runtime unblocked

- rebuilt `.venv-mirofish` on Python 3.11 to satisfy dependency constraints
- validated the local runtime checkout and config path
- confirmed the simulation wrapper can probe and run against the local bundle workflow

### Aerospace seed data landed

- added `data/seeds/company_watchlist.csv`
- added `data/seeds/system_watchlist.csv`
- fixed the aerospace project-root resolver in `src/super_agents/aerospace/paths.py`

### Fleet audit completed

- reviewed the registered sector folders and runnable surface area
- confirmed that runnable breadth is ahead of package maturity
- identified documentation drift as the main coordination problem

### Docs cleanup completed

- rewrote the core docs to describe the multi-agent platform instead of only the aerospace slice
- added a small docs index to distinguish current docs from historical review notes
- aligned the status snapshot and implementation plan with the existing dashboard baseline

### Dashboard hardening completed

- added shared dashboard data loaders and tests
- switched the dashboard from hardcoded three-agent lists to dynamic runnable-agent discovery
- added clearer empty states for missing status, run history, and findings artifacts

### Biotech and gaming package scaffolding landed

- added `src/super_agents/biotech/` and `src/super_agents/gaming/` starter helper modules
- added seed watchlists for biotech companies, biotech products, and gaming studios
- refactored a first wave of biotech and gaming scripts to use shared helpers
- restored direct script execution for those refactored scripts and added watchlist tests

### Renewable energy artifact wiring landed

- wired the renewable-energy calendar builder to `write_current_status()` and
  `write_run_summary()`
- added common artifact-writer tests to lock the shared dashboard contract
- verified the renewable-energy calendar can now emit current-status and latest-run artifacts

### Fintech starter package and workflow landed

- added `src/super_agents/fintech/` starter helper modules and a seed company watchlist
- added a documented daily workflow under `.agent_fintech/workflows/`
- refactored the fintech scripts onto shared path and I/O helpers
- wired the fintech license tracker to shared current-status and run-summary artifacts
- confirmed live smoke runs now emit dashboard artifacts even when upstream sources fail
- identified current fintech live blockers: NMLS returns `403 Forbidden` and the OCC charter list
  endpoint no longer returns JSON

## Current Readiness Snapshot

| Agent | Status | Notes |
|------|--------|-------|
| aerospace | READY | Full sector package plus seed watchlists and workflows |
| biotech | OPERATIONAL | Runnable with workflows, dashboard artifacts, starter package helpers, and seed watchlists |
| gaming | OPERATIONAL | Runnable with workflows, dashboard artifacts, starter package helpers, and seed watchlists |
| fintech | PARTIAL | Starter package, watchlist, workflow, and artifact wiring landed, but live source hardening is still needed |
| autonomous_vehicles | PARTIAL | Runnable scripts exist, but platform integration is still thin |
| quantum | PARTIAL | Runnable scripts exist, but package-backed structure is missing |
| rare_earth | PARTIAL | Runnable scripts exist, but still script-first |
| renewable_energy | PARTIAL | Runnable scripts exist, but still script-first |
| simulation | OPERATIONAL | Specialized runtime integration, not a standard sector package |
| cannabis_psychedelics | STUB | Sector idea exists, no runnable surface |
| meddevice | STUB | Sector idea exists, no runnable surface |
| space | STUB | Sector idea exists, no runnable surface |
| cybersecurity | BROKEN | Not discoverable and missing baseline config |

## Dashboard State

The project already has a user-facing interface:

- entrypoint: `dashboards/app.py`
- pages:
  - fleet overview
  - agent detail
  - run history
  - findings board
  - calendars
  - LLM operations

Current dashboard limitations:

- dynamic discovery is in place, but status and findings still only look as good as the artifact
  writers behind them
- calendar and latest-run coverage is improving, but remains uneven across sectors

## Immediate Priorities

1. Standardize artifact writers for sectors that still do not feed the dashboard well.
2. Harden fintech live-source integrations and capture a successful smoke path.
3. Decide whether cybersecurity should be implemented now or deferred explicitly.
4. Expand biotech and gaming helper adoption where script-local duplication still exists.
5. Deepen aerospace live ingestion after the reusable sector pattern is clearer.

## Useful Paths

| Path | Purpose |
|------|---------|
| `src/super_agents/cli.py` | CLI entrypoint and agent discovery |
| `src/super_agents/common/` | Shared status, paths, I/O, and run-summary helpers |
| `src/super_agents/aerospace/` | Strongest current sector package |
| `src/super_agents/biotech/` | Starter biotech package helpers |
| `src/super_agents/fintech/` | Starter fintech package helpers |
| `src/super_agents/gaming/` | Starter gaming package helpers |
| `src/super_agents/integrations/mirofish/` | Simulation runtime wrapper |
| `dashboards/app.py` | Streamlit dashboard entrypoint |
| `dashboards/pages/` | Dashboard views |
| `data/seeds/company_watchlist.csv` | Aerospace company seed data |
| `data/seeds/system_watchlist.csv` | Aerospace system seed data |
| `data/seeds/biotech_company_watchlist.csv` | Biotech company seed data |
| `data/seeds/biotech_product_watchlist.csv` | Biotech product seed data |
| `data/seeds/fintech_company_watchlist.csv` | Fintech company seed data |
| `data/seeds/gaming_studio_watchlist.csv` | Gaming studio seed data |
| `tests/` | Current automated test suite |
