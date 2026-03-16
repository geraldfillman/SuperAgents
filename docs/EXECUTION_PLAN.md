# Execution Plan

Updated: 2026-03-15

## Why This Plan Exists

The docs index is organized well, but the active task boards have drifted from the repo:

- Cybersecurity is no longer a zero-script stub. The repo already has a package, two runnable scripts, tests, and a dashboard page.
- The Risk Layer UI already exists, but it is still mock-driven and the backend `risk_layer` package does not exist yet.
- The shared dashboard artifact contract is still only partially documented, which makes parallel backend/frontend work fragile.

This plan becomes the active sequencing document until the lane boards are refreshed to match the current repo state.

## Plan Summary

| Phase | Focus | Timeline | Outcome |
|---|---|---|---|
| 0 | Documentation realignment | Now | One current source of truth and no false "not built yet" claims |
| 1 | Cybersecurity MVP hardening | W1 | Real artifact-backed cyber workflow beyond KEV-only basics |
| 2 | Risk Layer backend integration | W1-W2 | `get_risk_context()` replaces mock UI logic |
| 3 | Contract and regression hardening | W2-W3 | Stable artifact schema and test coverage for shared surfaces |
| 4 | Controlled expansion | W3+ | New agents/pages added only after the core contract is stable |

## Phase 0 - Documentation Realignment

Purpose: remove planning drift before adding more scope.

- Update `docs/PROJECT_OVERVIEW.md`, `docs/BACKEND_TASKS.md`, and `docs/FRONTEND_TASKS.md` to reflect what is already implemented.
- Keep `docs/README.md` as the index and point it to this file as the active plan.
- Separate "implemented MVP", "placeholder UI", and "planned work" so partial delivery is visible instead of implied complete or implied absent.
- Confirm which shared files require handoff rules and keep that list consistent across docs.

Exit criteria:

- No active doc describes cybersecurity or risk-layer UI as greenfield work.
- The docs set has one clearly named active plan and older plans are labeled historical or subordinate.

## Phase 1 - Cybersecurity MVP Hardening

Purpose: turn the existing cybersecurity slice into a reliable first-class lane.

Backend:

- Expand `src/super_agents/cybersecurity/` beyond KEV and patch calendar with the next highest-value live signals.
- Define a stable artifact set for cyber outputs: current status, latest run, findings, KEV dataset, and patch calendar.
- Add or extend tests under `tests/test_cybersecurity/` for fetch, normalize, watchlist, and artifact-writing behavior.

Frontend:

- Keep `dashboards/pages/8_Cybersecurity.py` artifact-driven.
- Replace "Phase 1 MVP" assumptions with a status view that makes source coverage and freshness explicit.
- Add richer views only after the corresponding saved artifact exists.

Exit criteria:

- Cybersecurity can be run end-to-end from CLI to dashboard using saved artifacts only.
- Tests cover the implemented cyber modules and artifact readers.

## Phase 2 - Risk Layer Backend Integration

Purpose: replace the current mock risk experience with a real shared service.

Backend:

- Implement `src/super_agents/common/risk_layer/` with `__init__.py`, `schema.py`, and source modules for sanctions, conflict, weather, and cyber.
- Define `RiskContext` as the contract used by all dashboards and agents.
- Set source refresh expectations and graceful degradation rules when one source is unavailable.

Frontend:

- Replace `get_risk_context_mock()` usage in `dashboards/components/risk_badge.py`.
- Replace placeholder data in `dashboards/pages/13_Risk_Layer.py` with live reads from the new backend contract.
- Keep fallbacks user-visible when data is missing rather than silently showing fake certainty.

Exit criteria:

- `render_risk_badge()` calls a real backend adapter.
- The Risk Layer page renders real or explicitly unavailable data, never mock data.

## Phase 3 - Shared Contract And Regression Hardening

Purpose: make parallel work safe before adding more sectors.

- Formalize the dashboard artifact contract in `docs/architecture.md`.
- Add tests for `dashboards/dashboard_data.py`, `src/super_agents/common/status.py`, and `src/super_agents/common/run_summary.py`.
- Mark partial agents and partial pages with explicit missing-data or mock-data states.
- Remove assumptions in docs that depend on stale counts unless those counts are automated.

Exit criteria:

- Shared artifact readers/writers have regression coverage.
- Backend and frontend can add fields without ambiguous handoff.

## Phase 4 - Controlled Expansion

Purpose: resume growth only after the platform surfaces are stable.

- Choose the next expansion wave only after Phases 0-3 are complete.
- Add new backend agents and frontend pages in matched pairs with one artifact contract per wave.
- Prefer one new high-signal agent pair at a time over multiple partially wired greenfield pages.

Suggested order after the core is stable:

1. Geopolitical risk
2. Defense intelligence
3. Maritime logistics
4. Conflict risk

## Immediate Next Actions

1. Refresh `docs/PROJECT_OVERVIEW.md`, `docs/BACKEND_TASKS.md`, and `docs/FRONTEND_TASKS.md` against the live repo.
2. Define the cybersecurity artifact contract and freshness fields.
3. Implement `src/super_agents/common/risk_layer/` and wire the risk badge to it.
4. Replace mock data on `dashboards/pages/13_Risk_Layer.py`.
5. Add shared-surface regression tests before opening the next expansion wave.
