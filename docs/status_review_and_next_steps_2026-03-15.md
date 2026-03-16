# Super Agents Status Review And Next Steps

Reviewed on 2026-03-15 against the `docs/` folder and the live repository state.

## Executive Summary

Super Agents is past the pure scaffold stage and has three meaningful strengths today:

- the CLI is working and discovers runnable agents
- the test suite is green
- there is already a Streamlit dashboard foundation with recent biotech, gaming, and aerospace artifacts

The main issue is not lack of progress. It is drift between the docs and the repo. That gap has
been narrowed a lot in this session, but the next-step plan should now move forward from docs
cleanup and dashboard discovery work instead of repeating them.

Update: the docs truth pass, dashboard discovery cleanup, and initial biotech and gaming package
scaffolding described below have now been completed. The remaining next steps start with
artifact-writer standardization and fintech live-source hardening.

## Verified Current State

### What is working

- `python -m super_agents list` currently exposes 9 runnable agents:
  `aerospace`, `autonomous_vehicles`, `biotech`, `fintech`, `gaming`, `quantum`,
  `rare_earth`, `renewable_energy`, and `simulation`
- `python -m pytest -q` passes with `32 passed`
- `src/super_agents/aerospace/` is the strongest full shared library layout today
- `src/super_agents/biotech/` and `src/super_agents/gaming/` now exist with starter helpers
- `src/super_agents/fintech/` now exists with starter helpers and a seed watchlist
- `dashboards/app.py` and six Streamlit pages already exist
- dashboard artifacts already exist for `aerospace`, `biotech`, and `gaming`
- `renewable_energy` now writes shared current-status and run-summary artifacts from its calendar flow
- `fintech` now writes shared current-status and run-summary artifacts from its license tracker flow
- aerospace seed data exists in `data/seeds/company_watchlist.csv` and
  `data/seeds/system_watchlist.csv`
- biotech, gaming, and fintech seed watchlists now exist under `data/seeds/`

### What is still incomplete

- `biotech` and `gaming` are only partially package-backed so far
- `fintech` is only partially package-backed so far and still needs live-source hardening
- most non-aerospace seed watchlists are still missing
- `cybersecurity` is still undiscoverable because it has no `.agent_cybersecurity/config.yaml`
- `cybersecurity` also has zero workflow files and no checked-in script files yet
- the dashboard now discovers the runnable fleet, but artifact coverage is still uneven across
  sectors

## Doc Review

### Current docs after cleanup

- `docs/current_status_2026-03-15.md` is directionally right about:
  - aerospace being the most mature agent
  - the need to graduate PARTIAL agents into repeatable READY agents
  - the next meaningful platform gap being artifact consistency rather than UI discovery

### Issues identified during the review and now resolved

- `docs/architecture.md` was rewritten to be repo-wide instead of aerospace-only
- `docs/implementation_plan.md` was rewritten to remove the stale `adt_agent` reference and
  focus on the current platform phases
- `docs/current_status_2026-03-15.md` was refreshed to acknowledge the existing Streamlit
  dashboard and current runnable fleet
- the docs now distinguish canonical platform docs from historical notes via `docs/README.md`
- the cybersecurity note is now framed as an explicit keep-or-defer decision, not only a
  missing-config fix

## Recommended Next-Step Plan

### Completed: Make the docs truthful and repo-wide

Goal: establish one source of truth before adding more sectors.

Tasks:

1. Rewrite `docs/architecture.md` as a repo-wide architecture doc and move aerospace-specific
   content into a dedicated subsection or sibling doc.
2. Replace `docs/implementation_plan.md` with a platform plan that covers:
   sector package pattern, seed data pattern, workflow pattern, dashboard pattern, and
   readiness criteria.
3. Keep `docs/current_status_2026-03-15.md` as a session snapshot, but add a pointer to this
   review or merge the corrected status into a new canonical status page.

Outcome:

- `docs/` now has a repo-wide architecture doc, a repo-wide implementation plan, a refreshed
  current status snapshot, and a docs index

### Priority 1: Continue hardening the existing dashboard instead of rebuilding one

Goal: turn the current Streamlit app into a reliable operational control surface by improving
the artifact contracts behind it.

Tasks:

1. Standardize where current-status, findings, and run-summary artifacts are written.
2. Document the dashboard launch path and artifact contract in `docs/`.
3. Expand calendar and findings coverage for sectors that currently appear mostly empty.

Exit criteria:

- the dashboard reflects the real discovered fleet without code edits per new agent

### Completed: Promote biotech and gaming from script-first to starter package-backed agents

Goal: stabilize the two agents that already look closest to daily analyst use.

Tasks:

1. Add `src/super_agents/biotech/` with `paths.py`, `watchlist.py`, and `io_utils.py`.
2. Add `src/super_agents/gaming/` with the same pattern.
3. Create seed watchlists for both sectors.
4. Refactor existing scripts to use shared helpers instead of ad hoc local path logic.
5. Add tests around loaders and artifact-writing contracts.

Exit criteria:

- biotech and gaming can evolve without script-local duplication or path drift

Update:

- starter packages now exist for both sectors
- seed watchlists now exist for both sectors
- initial script refactors and watchlist tests are in place
- direct script execution was restored for the refactored scripts

### Priority 2: Decide whether cybersecurity is a real near-term target

Goal: avoid carrying a broken agent that creates false breadth.

Tasks if keeping it:

1. Add `.agent_cybersecurity/config.yaml`.
2. Add workflow files.
3. Land at least one runnable script in one high-signal skill.

Tasks if deferring it:

1. mark it as planned or archived in docs
2. remove it from "current platform" language until it becomes runnable

Exit criteria:

- cybersecurity is either discoverable and minimally real, or explicitly deferred

### Priority 3: Graduate one PARTIAL sector end-to-end

Recommendation: choose `fintech` first.

Why fintech first:

- the scripts already exist
- the signal sources are relatively accessible
- it is a cleaner proving ground for the reusable sector-package pattern than the more
  specialized mining or energy domains

Tasks:

1. Add `src/super_agents/fintech/`.
2. Add a fintech seed watchlist.
3. Define a daily workflow and artifact outputs.
4. Run one end-to-end smoke path and capture the expected outputs in docs.

Exit criteria:

- Super Agents has a second fully normalized sector pattern beyond aerospace

Update:

- starter package helpers now exist for fintech
- a seed watchlist and daily workflow now exist
- the license tracker now emits current-status and run-summary artifacts
- the remaining blockers are live-source specific: NMLS currently returns `403 Forbidden`, and
  the OCC charter list path no longer returns JSON

### Priority 4: Return to aerospace live ingestion after the platform pattern is stable

Goal: invest in live-source depth only after the reusable operating model is clearer.

Tasks:

1. finish `award_tracker` live integration
2. connect SEC procurement parsing to the watchlist
3. connect SBIR and FAA signals
4. feed those outputs into the ranking layer and dashboard

Exit criteria:

- aerospace moves from "best structured agent" to "best operational agent"

## Suggested Sequencing

### Week 1

- artifact-writer standardization for dashboard coverage
- cybersecurity keep-or-defer decision

### Week 2

- fintech live-source hardening and successful smoke-path capture
- expand biotech and gaming helper usage where duplication still remains

### Week 3

- fintech completion
- aerospace live-ingestion slice
- dashboard polish driven by real artifacts instead of placeholders

## Recommended Immediate Move

Standardize the artifact contract first, then harden fintech live sources and decide
cybersecurity. That path makes the dashboard more trustworthy, reduces false breadth, and builds
the next reusable sector pattern after aerospace.
