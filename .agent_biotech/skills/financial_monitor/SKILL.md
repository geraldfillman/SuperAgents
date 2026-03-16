---
name: financial_monitor
description: Calculate cash runway and flag equity dilution risks from SEC 10-Q, 10-K, and S-3 filings.
---

# Financial Monitor Skill

## Purpose
Micro-cap biotech companies live and die by their cash runway. A positive clinical readout is frequently followed by an immediate equity offering. This skill parses SEC filings to extract exact cash balances, compute quarterly burn rates, and detect At-The-Market (ATM) offerings or "Going Concern" warnings.

## Data Sources
- **SEC EDGAR**: Pulls financial data from 10-Q (quarterly) and 10-K (annual) filings.
- **Form S-3**: Shelf registrations indicating potential future equity dilution.

## Scripts Provided

### `scripts/fetch_financials.py`
Parses the latest 10-Q/10-K for a company to extract cash, cash equivalents, marketable securities, and R&D / SG&A expenses to calculate the quarterly burn rate and total months of runway.
**Usage:**
```bash
python .agent/skills/financial_monitor/scripts/fetch_financials.py --ticker CRSP
python .agent/skills/financial_monitor/scripts/fetch_financials.py --batch
```

### `scripts/flag_offerings.py`
Monitors for S-3 shelf registrations, prospectus supplements (424B5), or specific "going concern" disclosures in financial filings indicating immediate cash needs.
**Usage:**
```bash
python .agent/skills/financial_monitor/scripts/flag_offerings.py --days 7
```

## Setup & Rules
1. Must run `search_edgar.py` periodically to keep local SEC data fresh.
2. Extracts XBRL nodes where possible, or falls back to regex matching on "Cash and cash equivalents" in the balance sheet.
3. Save output to `data/processed/financials/`.
