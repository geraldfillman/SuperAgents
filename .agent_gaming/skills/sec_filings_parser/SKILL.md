---
name: sec_filings_parser
description: Search SEC EDGAR filings and extract gaming catalyst disclosures
---

# SEC Filings Parser Skill

## Purpose

Parse EDGAR filings for the signals that matter to listed game studios:

- Release delays and narrowed or widened launch windows
- Publisher milestone payments
- Platform certification progress
- Marketing-spend acceleration
- Layoffs, restructurings, and impairment signals
- Financing events and equity dilution

## Scripts

### `scripts/extract_gaming_catalysts.py`

Extract filing text patterns for gaming-specific catalysts and save normalized JSON
records under `data/processed/gaming_sec_catalysts/`.

## Notes

- Keep SEC records as `source_type = "SEC"` and `source_confidence = "secondary"`
- Preserve the exact filing URL on every extracted catalyst
- Do not overwrite prior timing assumptions without appending change history
