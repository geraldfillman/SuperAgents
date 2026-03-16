---
name: insider_tracker
description: Track high-signal insider trades (Form 4s) leading up to data readouts.
---

# Insider Buying / Selling Tracker

## Purpose
A CEO or Chief Medical Officer buying/selling open-market shares right before a major clinical readout is a highly actionable signal. This skill tracks SEC Form 4 and SC 13G/D filings to flag significant insider transactions.

## Data Sources
- **SEC EDGAR**: Pulls Form 4 (Statement of Changes in Beneficial Ownership).

## Scripts Provided

### `scripts/monitor_form4.py`
Parses recent SEC filing data for Form 4s and extracts the transaction details (Buy/Sell, volume, value, insider title).
**Usage:**
```bash
python .agent/skills/insider_tracker/scripts/monitor_form4.py --days 14
```

## Setup & Rules
1. Must run `search_edgar.py` periodically to keep local SEC data fresh.
2. Filter for "P" (Purchase) or "S" (Sale) on the open market, ignoring routine grant/award vests.
3. Save output to `data/processed/insider_trades/`.
