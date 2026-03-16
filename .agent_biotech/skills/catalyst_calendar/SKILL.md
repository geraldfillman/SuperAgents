---
name: catalyst_calendar
description: Build and refresh the 90-day rolling catalyst calendar from regulatory events, trials, and advisory meetings
---

# Catalyst Calendar Skill

## Purpose
Aggregate all known upcoming catalysts into a rolling 90-day calendar — the Master Catalyst Calendar described in `Biotech.md`.

## Calendar Columns

| Column | Description |
|--------|-------------|
| date | Expected catalyst date |
| ticker | Company trading symbol |
| company | Company name |
| product | Product/asset name |
| indication | Disease target |
| catalyst_type | PDUFA / adcom / topline data / submission / clearance / etc. |
| source_confidence | primary / secondary / sponsor |
| official_vs_sponsor | Whether date is from official FDA source or sponsor |
| next_step_after_outcome | What happens if positive / negative |

## Data Sources (merged)
1. `regulatory_events` — FDA action dates, submission acceptances
2. `clinical_trials` — estimated completion dates, topline windows
3. `advisory_meetings` — scheduled adcom dates
4. `postmarketing` — PMR deadlines

## Scripts

### `scripts/build_calendar.py`
Queries all source tables, merges into a unified calendar, and sorts by date.

## Usage
```bash
# Build the next 90 days
python .agent/skills/catalyst_calendar/scripts/build_calendar.py --days 90

# Build for a specific ticker
python .agent/skills/catalyst_calendar/scripts/build_calendar.py --ticker AGEN --days 180

# Export as CSV
python .agent/skills/catalyst_calendar/scripts/build_calendar.py --days 90 --format csv --output catalysts.csv
```
