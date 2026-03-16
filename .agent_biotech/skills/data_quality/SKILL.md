---
name: data_quality
description: Audit stale records, validate source integrity, track product aliases, and ensure data quality across all tables
---

# Data Quality Skill

## Purpose
Enforce the quality control rules from `Biotech.md` to keep the database trustworthy.

## Quality Control Rules (from Biotech.md)

1. Never overwrite an old catalyst without keeping history
2. Store the exact source URL for every regulatory event
3. Mark whether a date came from FDA, ClinicalTrials.gov, SEC, or press release
4. Keep company-level notes separate from product-level evidence
5. When a product changes name, preserve aliases
6. When a company merges or reverse-splits, keep product continuity intact
7. Flag stale records if no source has changed in 90+ days
8. Flag "sponsor-only" milestones until externally corroborated

## Scripts

### `scripts/audit_stale_records.py`
Scan all tables for records not updated in 90+ days. Generates a report with:
- Last update date
- Staleness severity (90/120/180+ days)
- Recommended action (verify, archive, or flag)

### `scripts/validate_sources.py`
Check all records for:
- Missing `source_url` fields
- `source_confidence` = "sponsor" without external corroboration
- `official_fda_source_present = false` for events that should have FDA backing
- Broken source URLs (optional HTTP check)

## Usage
```bash
# Run stale record audit
python .agent/skills/data_quality/scripts/audit_stale_records.py

# Validate source integrity
python .agent/skills/data_quality/scripts/validate_sources.py

# Check for broken source URLs (slower)
python .agent/skills/data_quality/scripts/validate_sources.py --check-urls
```
