# Super Agents Architecture

Updated: 2026-03-15

## Objective

Super Agents is a multi-sector, asset-first research and execution framework. Each agent tracks
the thing that creates or destroys value in its sector, then ties company-level risk and
opportunity back to that asset.

Examples:

- biotech tracks products
- gaming tracks titles
- aerospace tracks systems and programs
- rare earth tracks mine sites and deposits
- renewable energy tracks projects

## Core Principles

- Asset-first: analyze the tracked asset before the company story.
- Shared platform, sector-specific logic: common runtime rules live in `src/super_agents/`,
  while sector logic lives in `.agent_<sector>/` and, when mature, `src/super_agents/<sector>/`.
- Verifiable outputs: scripts should emit raw evidence, processed records, and human-readable
  summaries instead of opaque console-only results.
- Local-first operation: workflows, dashboards, and artifacts should work from the local
  repository without requiring a hosted control plane.
- Source confidence everywhere: each meaningful record should preserve source URL, source type,
  and confidence so analysts can audit findings quickly.

## Platform Layers

### 1. Agent Definitions

Each sector agent lives under `.agent_<sector>/` and should contain:

- `config.yaml` for discovery and metadata
- `skills/*/scripts/*.py` for runnable tasks
- `workflows/*.md` for daily, weekly, and monthly operating cadence
- optional `schema/`, `plugins/`, or MCP-specific support files

### 2. Shared Python Package

`src/super_agents/` provides reusable platform logic, including:

- `cli.py` for agent discovery and execution
- `common/` for shared paths, status, run summaries, and I/O helpers
- `llm/` for model configuration and client behavior
- `db/` for database integration
- `integrations/mirofish/` for the simulation runtime wrapper

### 3. Sector Packages

When an agent matures past script-local logic, it should gain a package under
`src/super_agents/<sector>/` with reusable helpers such as:

- `paths.py`
- `watchlist.py`
- `io_utils.py`
- sector-specific normalization, scoring, and parsing modules

Current state:

- `aerospace` is the most complete package-backed sector today
- `biotech` and `gaming` now have starter sector packages, seed watchlists, and shared helpers
- `fintech` now has starter package helpers, a seed watchlist, and a documented workflow, but
  its live source integrations still need hardening
- other runnable sectors are mostly script-first and partial

### 4. Data And Artifacts

The repository separates source evidence from analyst-facing outputs:

- `data/raw/<sector>/` for captured raw responses and source snapshots
- `data/processed/<sector>/` for normalized records
- `data/seeds/` for tracked pilot universes and watchlists
- `dashboards/` for status, run summaries, findings, and the Streamlit UI

## Execution Model

The normal operating flow is:

1. Discover agents from `.agent_*` directories with valid configs and runnable scripts.
2. Execute a workflow or direct skill script through `python -m super_agents`.
3. Pull or stage source data into `data/raw/`.
4. Normalize and write structured outputs into `data/processed/`.
5. Emit run artifacts into `dashboards/` so humans and automation can review results.
6. Render summaries in Streamlit without the dashboard mutating source data.

## Artifact Contract

Each meaningful task run should write:

- current status: `dashboards/<agent>_current_status.json`
- latest run summary: `dashboards/<agent>_run_latest.json`
- analyst-readable summary: `dashboards/<agent>_run_latest.md`
- rolling findings when applicable: `dashboards/<agent>_findings_latest.json`
- run history: `dashboards/runs/<agent>/<timestamp>/summary.json` and `summary.md`

The dashboard is a consumer of these artifacts, not the writer of record.

## Agent Readiness Model

Use these readiness levels consistently in docs and reviews:

- `READY`: runnable scripts, workflows, seed data, repeatable artifact outputs, and a sector
  package when shared logic is non-trivial
- `OPERATIONAL`: runnable scripts and workflows exist, but the agent still relies heavily on
  script-local logic and needs package-backed helpers
- `PARTIAL`: some runnable scripts exist, but coverage, workflows, or artifacts are incomplete
- `STUB`: sector folder and skill ideas exist, but no runnable scripts yet
- `BROKEN`: the agent is not discoverable or is missing required config or runtime wiring

## Dashboard Architecture

The current dashboard entrypoint is `dashboards/app.py` with multipage views in
`dashboards/pages/`. It already supports:

- fleet overview
- per-agent detail
- run history
- findings board
- calendars
- LLM operations

Current limitation:

- the UI now discovers the runnable fleet dynamically, but artifact coverage is still uneven
  because several sectors do not yet emit consistent status, findings, and calendar outputs

## Source Confidence Rules

Use these platform-wide labels:

- `primary`: official registry, regulator filing, government source, or first-party platform
- `secondary`: structured aggregator or third-party normalization of primary evidence
- `sponsor`: company self-reporting such as press releases, investor decks, and interviews

## Current Architectural Baseline

As of 2026-03-15:

- 9 runnable agents are exposed by the CLI
- 32 tests pass
- aerospace is the strongest reference implementation
- simulation is a specialized runtime integration rather than a standard asset-tracking sector
- the main architectural gap is consistency across sectors, not missing scaffolding
