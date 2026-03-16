---
name: sec_filings_parser
description: Search SEC EDGAR for 8-K, 10-Q, 10-K, 20-F, 6-K filings and extract pipeline/regulatory catalyst disclosures
---

# SEC Filings Parser Skill

## Purpose
Parse SEC filings to confirm or discover regulatory milestones disclosed by biotech sponsors — Tier 3 in the source hierarchy.

## API Reference
- **EDGAR Full-Text Search**: `https://efts.sec.gov/LATEST/search-index?q=...`
- **EDGAR Filing API**: `https://data.sec.gov/submissions/CIK{cik}.json`
- **Rate Limit**: 10 requests/second
- **Auth**: User-Agent header required (name + email)
- **Docs**: https://www.sec.gov/edgar/searchedgar/efulltext.htm

## Scripts

### `scripts/search_edgar.py`
Search EDGAR for filings by company CIK, ticker, or filing type. Returns filing metadata and download URLs.

### `scripts/extract_catalysts.py`
Parse filing text (8-K, 10-Q, 10-K) to extract:
- PDUFA target action dates
- NDA/BLA/PMA submission confirmations
- Complete Response Letters (CRL)
- Trial enrollment updates
- Manufacturing (CMC) disclosures
- Partnership/licensing agreements affecting products

## Important Notes
- SEC filings are `source_type = "SEC"` with `source_confidence = "secondary"`
- Sponsor-disclosed dates should go in `sponsor_disclosed_target_date`, NOT `official_fda_source_present`
- Always store filing URL in `source_url`
- SEC requires User-Agent header: `"CompanyName contact@email.com"`
