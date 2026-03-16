# Budget Tracker

Purpose: ingest official DoD Comptroller budget documents into normalized `budget_lines` records.

Inputs:

- official budget PDF URL or local PDF path
- document family: `p1` or `rdte`
- agency label when the parser cannot infer it cleanly
- fiscal year override when the source file name is ambiguous

Outputs:

- normalized `budget_lines` records
- extracted text cache for parser debugging
- raw PDF cache when the source is fetched by URL
- reconciled budget exposure matches and watchlist scorecards

Priority signals:

- line-item funding increases or cuts
- program element visibility for tracked systems
- agency and appropriation concentration

Notes:

- only ingest official Comptroller PDFs or analyst-provided files
- use `--kind` when a source document does not self-identify clearly in extracted text
- keep the parser conservative; do not backfill missing fields with guesses
- use `scripts/reconcile_budget_exposure.py` after ingestion to map budget lines back to tracked systems
- analyst-approved overrides live in `data/seeds/budget_mapping_overrides.csv`
