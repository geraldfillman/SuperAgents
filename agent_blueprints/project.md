# Future Agent Project Guide

This document defines how to create future sector agents from the Biotech Agent base, how to structure their files, and how each agent should report what it is doing and what it found after every task run.

The goal is consistency. Every new agent should look familiar at the folder level, behave similarly at the workflow level, and emit run outputs that are easy to review without opening raw JSON files by hand.

## 1. Core Rule

Every future agent must stay asset-first.

- In biotech, the asset is the product.
- In gaming, the asset is the title.
- In mining, the asset is the project.
- In defense, the asset is the system.

Do not build future agents around general company stories. Build them around the thing that creates or destroys value.

## 2. Required Design Questions Before Building a New Agent

Answer these before creating files:

1. What is the primary tracked asset?
2. What are the equivalent binary or high-signal catalysts?
3. Which existing skills can be reused exactly?
4. Which skills need logic changes only?
5. Which skills need full replacement?
6. What are the primary sources, secondary sources, and sponsor-only sources?
7. What should the main schema tables be called?
8. What should a daily run update?
9. What should a weekly review summarize?
10. What should a monthly reconciliation clean up?

If these are not explicit, the agent design is not ready.

## 3. Standard Build Process For Future Agents

Use this sequence every time:

1. Write a sector blueprint in `agent_blueprints/<sector>_agent.md`.
2. Decide whether the agent should live in a parallel folder such as `.agent_<sector>/`.
3. Copy only the reusable skills first.
4. Rewrite the schema before writing new ingestion logic.
5. Add workflow documents before adding dashboards.
6. Seed a small pilot universe.
7. Run one end-to-end workflow on the pilot set.
8. Tighten noisy extraction rules before expanding coverage.
9. Add reporting outputs so each run is reviewable.

Do not jump straight to a large ingestion build without a small pilot.

## 4. Recommended Folder Layout

Each future agent should use this structure:

```text
.agent_<sector>/
  config.yaml
  mcp/
  workflows/
  skills/
  plugins/

schema/
  create_<sector>_tables.sql

data/
  raw/<sector>/
  processed/<sector>_...

dashboards/
  <sector>_current_status.json
  <sector>_run_latest.md
  <sector>_findings_latest.json
  <sector>_calendar_*.json

docs/
  <sector>_integration.md

agent_blueprints/
  <sector>_agent.md
```

This keeps each agent isolated while preserving the same operating model.

## 5. Skill Classification Rules

When adapting a new agent, classify every skill into one of four buckets:

- `reuse_exactly`
- `modify_logic`
- `rewrite`
- `new`

Do this inside the blueprint and inside the implementation doc.

Example:

| Existing skill | New sector action |
|---|---|
| `financial_monitor` | Usually reusable |
| `sec_filings_parser` | Usually modify logic |
| `fda_tracker` | Usually rewrite or replace |
| `clinicaltrials_scraper` | Usually rewrite or replace |
| `data_quality` | Usually keep and retune |

## 6. Schema Rules

Every future agent schema should preserve these ideas:

- One company table
- One primary asset table
- One event table
- One metrics table
- One scoring table
- One change-history table
- One financials table if the sector is pre-revenue or cash-sensitive

Use sector names, not biotech leftovers.

Good examples:

- `products` -> `titles`
- `regulatory_events` -> `release_events`
- `clinical_trials` -> `storefront_metrics`

Bad examples:

- Keeping biotech table names and only changing comments
- Mixing multiple asset types into one generic table without a clear reason

## 7. Source Confidence Rules

Every record written by any future agent must carry:

- `source_url`
- `source_type`
- `source_confidence`

Use the same confidence meanings everywhere:

- `primary`: official registry, official database, official store page, official filing
- `secondary`: SEC filing interpretation, third-party structured data, aggregator
- `sponsor`: company press release, investor presentation, self-reported milestone

This is mandatory. If the agent cannot explain where a record came from, the record is not complete.

## 8. Pilot Universe Rules

Start small.

- 3 to 5 companies
- 1 to 3 primary assets per company
- enough coverage to exercise every important skill

A good pilot set includes:

- one large or stable name
- one mid-cap or sector bellwether
- one smaller or distressed name

The pilot should be chosen to test workflows, not to maximize coverage.

## 9. What Each Agent Should Display While It Is Working

Every agent run should surface a current-status view.

Recommended files:

- `dashboards/<agent>_current_status.json`
- `dashboards/<agent>_current_status.md`

Required fields:

```json
{
  "agent_name": "gaming-studio-tracker",
  "run_id": "20260315_151500",
  "workflow_name": "daily_update",
  "task_name": "fetch_storefront_metrics",
  "status": "running",
  "started_at": "2026-03-15T15:15:00Z",
  "input_scope": ["EA", "TTWO", "MSGM", "CAPCOM", "SQEX"],
  "active_source": "steam_storefront",
  "progress": {
    "completed": 3,
    "total": 5
  },
  "current_focus": "Fetching public storefront snapshots for tracked titles",
  "latest_message": "Processed 3/5 titles"
}
```

Best display principles:

- show one active task, not a wall of logs
- show progress counts
- show which companies or assets are in scope
- show which data source is being used
- show the current blocker if there is one

## 10. What Each Agent Should Output After Every Task Run

Every task run should write both machine-readable and analyst-readable output.

Recommended files:

- `dashboards/runs/<agent>/<timestamp>/summary.json`
- `dashboards/runs/<agent>/<timestamp>/summary.md`
- `dashboards/<agent>_run_latest.json`
- `dashboards/<agent>_run_latest.md`

The JSON is for automation. The Markdown is for humans.

### Required Run Summary Fields

```json
{
  "agent_name": "gaming-studio-tracker",
  "run_id": "20260315_151500",
  "workflow_name": "daily_update",
  "task_name": "fetch_storefront_metrics",
  "status": "completed",
  "started_at": "2026-03-15T15:15:00Z",
  "completed_at": "2026-03-15T15:15:42Z",
  "duration_seconds": 42,
  "inputs": {
    "titles": 5,
    "companies": 5
  },
  "outputs": {
    "records_written": 5,
    "files_written": 2
  },
  "findings": [
    {
      "severity": "info",
      "asset": "PRAGMATA",
      "finding_type": "release_date_detected",
      "summary": "Steam page shows release date April 16, 2026",
      "source_url": "https://store.steampowered.com/app/3357650",
      "confidence": "primary"
    }
  ],
  "blockers": [],
  "next_actions": [
    "Rebuild gaming release calendar"
  ]
}
```

### Required Markdown Summary Structure

Use this format:

```md
# Run Summary

## What Ran
- workflow
- task
- scope
- start/end time

## What Changed
- new records
- updated records
- files written

## Findings
- finding 1
- finding 2

## Blockers
- blocker 1

## Next Actions
- next action 1
```

## 11. Best Ways To Display Findings

Findings should be displayed in three layers.

### Layer 1: Current Run Summary

Purpose: show exactly what just happened.

Best format:

- concise Markdown summary
- one JSON summary for automation

### Layer 2: Rolling Findings Board

Purpose: show the most recent meaningful discoveries across runs.

Recommended file:

- `dashboards/<agent>_findings_latest.json`

Recommended fields:

- finding time
- asset
- company
- finding type
- severity
- summary
- source URL
- confidence
- whether action is required

### Layer 3: Structured Calendars And Scoreboards

Purpose: show what matters next.

Recommended outputs:

- release or catalyst calendar
- financial runway table
- data quality report
- title or asset score table
- recent source validation report

## 12. Best Ways To Display What The Agent Is Working On

Use a status-plus-findings model, not raw logs.

Recommended dashboard pattern:

1. `Current Task`
2. `Progress`
3. `Sources In Use`
4. `Assets In Scope`
5. `Latest Findings`
6. `Open Blockers`
7. `Next Scheduled Step`

Good example:

- Current task: Fetching Steam storefront metrics
- Progress: 3/5 titles processed
- Sources in use: Steam store page, tracked studio seed file
- Assets in scope: PRAGMATA, Life is Strange: Reunion
- Latest findings: two upcoming release dates confirmed
- Open blockers: no critic score source wired yet
- Next scheduled step: rebuild release calendar

Bad example:

- dumping 500 lines of mixed HTTP logs and print statements
- hiding the active scope
- showing counts without the affected assets

## 13. Required Run Artifacts

Each task run should ideally produce:

- one raw-source snapshot when practical
- one processed output file
- one run summary file
- one status update file

This makes debugging possible after the fact.

## 14. Noise Control Rules

Future agents must tighten noisy extraction before scaling up.

Required checks:

- deduplicate repeated text matches
- reject obvious table-only matches when they are not actionable
- separate generic risk-factor language from specific event disclosures
- preserve exact source context for audits

Do not expand coverage until noise is under control on the pilot set.

## 15. Launch Checklist For Any New Agent

Before calling a new agent ready, confirm:

1. The blueprint exists.
2. The agent has its own config and workflows.
3. The schema is renamed to sector-appropriate tables.
4. Source confidence is present on every record type.
5. A pilot universe exists.
6. At least one daily workflow runs end to end.
7. The agent writes a current-status view.
8. The agent writes a run summary after each task.
9. The findings board can be reviewed without opening raw files.
10. The calendar or equivalent forward-looking output is populated.

## 16. Recommendation For This Repo

Use `agent_blueprints/` for sector design docs and use `docs/` for implementation notes after scaffolding starts.

The blueprint should answer:

- what the agent is
- what skills map over
- what sources replace biotech sources
- what schema changes are required

The implementation doc should answer:

- what was actually created
- what is still stubbed
- what pilot data exists
- what outputs the workflows currently produce

That split keeps sector design and actual implementation from drifting into one mixed document.
