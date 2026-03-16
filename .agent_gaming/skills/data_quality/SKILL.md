---
name: data_quality
description: Audit stale records, validate sources, and preserve release-history integrity
---

# Data Quality Skill

## Purpose

Keep gaming records trustworthy and historically traceable.

## Rules

1. Never overwrite a prior release date without keeping change history
2. Store the exact source URL for every release-critical event
3. Preserve title aliases, working titles, and regional variants
4. Flag sponsor-only milestones until externally corroborated
5. Audit stale records before a title nears release

## Scripts

### `scripts/audit_stale_records.py`

Scan processed gaming directories for records older than a configurable threshold.

### `scripts/validate_sources.py`

Check gaming records for missing source URLs or missing source-confidence tags.
