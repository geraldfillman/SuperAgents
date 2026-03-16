# Docs Guide

Updated: 2026-03-15

## Start Here

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - single entry point for architecture, agent fleet status, priorities, gaps, and pointers to the rest of the docs
- [EXECUTION_PLAN.md](EXECUTION_PLAN.md) - active sequencing plan based on the current repo state

## Task Boards

Lane-specific boards for implementation detail. Refresh them against [EXECUTION_PLAN.md](EXECUTION_PLAN.md) before treating them as current status.

- [BACKEND_TASKS.md](BACKEND_TASKS.md) - backend lane for Python, ETL, API, package, data, and artifact-contract work
- [FRONTEND_TASKS.md](FRONTEND_TASKS.md) - frontend lane for Streamlit pages, layout, filters, charts, and operator workflow

## Parallel Work Split

Use the task boards as two separate lanes so agents can work at the same time without editing the same code.

- Backend lane owns `src/super_agents/`, `.agent_*/`, `tests/`, `schema/`, `data/seeds/`, and artifact writers that produce dashboard inputs.
- Frontend lane owns `dashboards/pages/`, `dashboards/components/`, Streamlit interaction flow, and dashboard presentation logic.
- Shared files need coordination and should have only one active editor at a time: `dashboards/app.py`, `dashboards/dashboard_data.py`, `src/super_agents/common/status.py`, `src/super_agents/common/run_summary.py`, and `docs/architecture.md`.
- Preferred handoff is backend-first for new artifact fields: backend defines or updates the artifact contract, frontend consumes it without editing the backend writer in the same pass.

## Platform Reference

- [APPLICATION_DESCRIPTION.md](APPLICATION_DESCRIPTION.md) - detailed application description, competitive positioning, and future roadmap (near/medium/long/visionary)
- [architecture.md](architecture.md) - repo-wide platform architecture for agents, CLI, dashboard, and MiroFish integration
- [sitdeck_expansion_plan.md](sitdeck_expansion_plan.md) - proposed new agents, enrichment layers, and Global Risk Layer design

## Historical Context

- [implementation_plan.md](implementation_plan.md) - original phased plan; kept for history and no longer the active source of truth
- [current_status_2026-03-15.md](current_status_2026-03-15.md) - point-in-time snapshot from 2026-03-15; counts in this file are historical, not live status
- [status_review_and_next_steps_2026-03-15.md](status_review_and_next_steps_2026-03-15.md) - dated architecture and security review that informed the current task boards
- [source_project_review.md](source_project_review.md) - review of the source Biotechpanda project

## Maintenance Rule

When the repo changes materially:

1. Update [EXECUTION_PLAN.md](EXECUTION_PLAN.md) if sequencing or phase ownership changed.
2. Update [BACKEND_TASKS.md](BACKEND_TASKS.md) and [FRONTEND_TASKS.md](FRONTEND_TASKS.md) if lane priorities or completion state changed.
3. Update [architecture.md](architecture.md) if the platform model, runtime flow, or artifact contract changed.
4. Keep this index free of live counts unless you will maintain them with every material repo change.
5. Treat dated `current_status_*.md` files as read-only history. Add a new dated snapshot when needed instead of editing an old one.
