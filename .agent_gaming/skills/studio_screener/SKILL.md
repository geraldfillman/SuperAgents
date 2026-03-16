---
name: studio_screener
description: Discover publicly traded console and PC studios in the target coverage universe
---

# Studio Screener Skill

## Purpose

Identify listed studios that fit the coverage universe for the gaming tracker.

## Universe traits

- Publicly traded game developers or publishers
- Small and mid-cap names preferred
- Console and PC exposure preferred
- Exclude pure services or generic media holding companies

## Scripts

### `scripts/screen_studios.py`

Load candidate studio records from a local JSON file, normalize them, and emit a starter coverage report.

### `scripts/sync_steam_appids.py`

Generate `data/raw/gaming/appids.txt` from `studio_candidates.json` and optionally
search Steam for titles that are missing `steam_app_id`. High-confidence exact matches
can be written back into the tracked-studios file.
