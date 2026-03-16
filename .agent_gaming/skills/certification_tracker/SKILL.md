---
name: certification_tracker
description: Track rating-board and platform-certification signals that indicate launch readiness
---

# Certification Tracker Skill

## Purpose

Use official or directly exported certification records as leading indicators that
a title is nearing release readiness.

## Signals to track

- ESRB or regional age ratings
- Korean or European ratings-board entries
- Platform-certification status changes
- Gold-master or submission-complete disclosures when corroborated

## Scripts

### `scripts/fetch_certification_signals.py`

Normalize JSON snapshots or exported records into the `certifications`-style
output used by the gaming schema.

## Notes

- Official registry pages should be treated as `primary`
- Press-release-only claims remain `sponsor` until corroborated
