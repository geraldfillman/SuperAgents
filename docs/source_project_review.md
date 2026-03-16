# Source Project Review

This review focuses on the current biotech repo as a source of reusable patterns for an aerospace and defense adaptation.

## Findings

### 1. Runtime blocker in the report orchestration scripts

All `run_*_report.py` scripts invoke `extract_catalysts.py` with no `--url` argument, but the extractor CLI requires `--url`. The pipeline therefore stops at the catalyst extraction step instead of producing SEC-derived signals.

Relevant files:

- `Biotechpanda-main/run_full_report.py`
- `Biotechpanda-main/run_gene_report.py`
- `Biotechpanda-main/run_radio_adc_report.py`
- `Biotechpanda-main/run_tpd_report.py`
- `Biotechpanda-main/.agent/skills/sec_filings_parser/scripts/extract_catalysts.py`

### 2. Integration bug between SEC cache output and financial monitor input

`search_edgar.py` writes SEC submission caches using `filings_{cik}_{timestamp}.json`, while `fetch_financials.py` looks for `filings_{cik.zfill(10)}_*.json`. If a non-padded CIK is written or discovered, the financial monitor misses the cached filing set and silently returns no work.

Relevant files:

- `Biotechpanda-main/.agent/skills/sec_filings_parser/scripts/search_edgar.py`
- `Biotechpanda-main/.agent/skills/financial_monitor/scripts/fetch_financials.py`

### 3. The catalyst calendar does not enforce its own time window

`build_calendar.py` computes `today` and `cutoff_date` but never filters records against them. The output is sorted, but it is not constrained to the requested forward window. That makes the reported "`next 90 days`" calendar unreliable.

Relevant file:

- `Biotechpanda-main/.agent/skills/catalyst_calendar/scripts/build_calendar.py`

## Reuse Decision

Reuse with minimal changes:

- financial runway concept
- insider trade monitoring concept
- workflow-based operating model
- asset-first framing

Reuse with focused modification:

- SEC filing ingestion and text classification
- milestone calendar builder
- data quality and source-confidence tagging

Replace outright:

- FDA tracker
- ClinicalTrials.gov tracker
- Orange Book watcher
- medical conference scraper

## Implication For This New Project

The aerospace/defense project should start as a clean sibling project rather than a branch of the biotech code. Reuse should be conceptual first, then code-level only after the orchestration and file-contract issues above are corrected.
