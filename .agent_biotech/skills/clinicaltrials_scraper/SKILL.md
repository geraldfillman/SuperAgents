---
name: clinicaltrials_scraper
description: Query ClinicalTrials.gov v2 API for trial data by sponsor, NCT ID, or indication and detect changes, with WHO ICTRP and AACT fallback paths when needed
---

# ClinicalTrials Scraper Skill

## Purpose
Populate and maintain the `clinical_trials` table using the ClinicalTrials.gov v2 API, with WHO ICTRP and AACT fallback paths when the live API is blocked or unavailable.

## API Reference
- **Base URL**: `https://clinicaltrials.gov/api/v2/studies`
- **Rate Limit**: 100 requests/minute
- **Auth**: None required
- **Docs**: https://clinicaltrials.gov/data-api/api

## Scripts

### `scripts/fetch_trials.py`
Search and fetch trials by sponsor name, NCT ID, condition, or intervention.
Primary source: ClinicalTrials.gov v2 API.
Fallbacks: WHO ICTRP advanced search, then a local AACT SQLite index.

Populates:
- `nct_id`, `phase`, `status`, `title`, `indication`
- `primary_endpoint`, `estimated_primary_completion`
- `estimated_study_completion`, `results_posted`

### `scripts/detect_trial_changes.py`
Compare current API data against stored records to detect:
- Status changes (recruiting -> active -> completed)
- Date changes (completion date pushed/pulled)
- New results posted
- Newly registered trials for tracked sponsors

### `scripts/build_aact_index.py`
Build a local SQLite index from a downloaded AACT flatfile snapshot so trial lookups still work when the live ClinicalTrials.gov API is unavailable.

## Usage
```bash
# Search by sponsor
python .agent/skills/clinicaltrials_scraper/scripts/fetch_trials.py --sponsor "Agenus Inc"

# Search by NCT ID
python .agent/skills/clinicaltrials_scraper/scripts/fetch_trials.py --nct NCT05148962

# Search by condition
python .agent/skills/clinicaltrials_scraper/scripts/fetch_trials.py --condition "glioblastoma" --phase 3

# Build the local AACT fallback index from the latest downloaded snapshot
python .agent/skills/clinicaltrials_scraper/scripts/build_aact_index.py

# Detect changes from last snapshot
python .agent/skills/clinicaltrials_scraper/scripts/detect_trial_changes.py
```

## Important Notes
- Trial marked "Completed" does not mean topline data is publicly available
- Always store `results_posted` separately from `status`
- Save raw source responses to `data/raw/clinicaltrials/`
- ClinicalTrials.gov records should keep `source_type = "ClinicalTrials.gov"` and `source_confidence = "primary"`
- AACT fallback records are stored with `source_type = "AACT"` and `source_confidence = "secondary"`
- WHO ICTRP is a best-effort backup, not the preferred source of record
