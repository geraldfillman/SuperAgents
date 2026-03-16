---
name: fda_tracker
description: Fetch FDA drug approvals, device clearances, advisory committee meetings, and postmarketing requirements from official FDA databases
---

# FDA Tracker Skill

## Purpose
Ingest regulatory data from official FDA sources — the highest-confidence tier in the tracker's source hierarchy.

## Data Sources

| Source | URL | Data Type |
|--------|-----|-----------|
| openFDA Drug API | `https://api.fda.gov/drug/` | Drug approvals, labels, recalls |
| Drugs@FDA | `https://www.fda.gov/drugs/development-approval-process-drugs/drug-approvals-and-databases` | NDA/BLA approvals by year |
| 510(k) Database | `https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/pmn.cfm` | Device clearances |
| PMA Database | `https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm` | Premarket approvals |
| De Novo Database | `https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpmn/denovo.cfm` | Novel device classifications |
| Purple Book | `https://purplebooksearch.fda.gov/` | Licensed biologics |
| Advisory Committee Calendar | `https://www.fda.gov/advisory-committees/advisory-committee-calendar` | Scheduled meetings |
| Postmarketing Requirements DB | FDA PMR database | PMR/PMC obligations |

## Scripts

### `scripts/fetch_drug_approvals.py`
Queries the openFDA drug approvals endpoint. Populates `regulatory_events` table with:
- `event_type`: "approval"
- `pathway`: NDA / BLA
- `source_type`: "FDA"
- `source_confidence`: "primary"
- `official_fda_source_present`: true

### `scripts/fetch_device_clearances.py`
Scrapes 510(k), PMA, and De Novo databases. Maps to device status taxonomy.

### `scripts/fetch_advisory_calendar.py`
Parses the FDA Advisory Committee Calendar page. Creates `advisory_meetings` records.

### `scripts/fetch_postmarketing.py`
Pulls postmarketing requirements/commitments. Populates `postmarketing` table.

## Usage
```bash
# Fetch recent drug approvals (last 30 days)
python .agent/skills/fda_tracker/scripts/fetch_drug_approvals.py --days 30

# Fetch device clearances for a specific product code
python .agent/skills/fda_tracker/scripts/fetch_device_clearances.py --product-code QAS

# Update advisory committee calendar
python .agent/skills/fda_tracker/scripts/fetch_advisory_calendar.py

# Refresh postmarketing requirements
python .agent/skills/fda_tracker/scripts/fetch_postmarketing.py
```

## Important Notes
- Always set `official_fda_source_present = true` for data from these sources
- openFDA rate limit: 240 req/min with API key, 40/min without
- Device database queries require HTML scraping (no formal JSON API)
- Store raw responses in `data/raw/fda/` before transforming
