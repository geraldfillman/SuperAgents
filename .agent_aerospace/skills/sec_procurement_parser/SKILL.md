# SEC Procurement Parser

Purpose: extract aerospace and defense procurement signals from issuer filings.

Workflow:

- fetch recent filing text with `fetch_sec_filings.py`
- run `extract_procurement_signals.py` on one file or a whole directory
- review normalized procurement-risk and milestone records before scoring

Target language:

- OTA
- IDIQ
- SBIR or STTR
- downselect
- protest
- production lot
- low-rate initial production
- full-rate production
- option exercise
- launch manifest

Outputs:

- normalized milestone records
- procurement-risk tags
- source confidence set to `secondary`
