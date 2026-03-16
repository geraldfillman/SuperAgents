---
description: Daily data update - check certification signals, SEC filings, storefront metadata, and release timing
---

# Daily Update Workflow

Run every weekday morning to keep tracked studios and titles current.

## Steps

1. Pull new certification and rating-board signals
```bash
python .agent_gaming/skills/certification_tracker/scripts/fetch_certification_signals.py --days 1
```

2. Check SEC filings for tracked studios
   - Search EDGAR for 8-K, 10-Q, 10-K, 20-F, and 6-K filings from the covered universe
   - Extract delay language, milestone-payment references, launch timing changes, layoffs, and financing signals

3. Refresh storefront snapshots for pre-launch titles
```bash
python .agent_gaming/skills/storefront_monitor/scripts/fetch_storefront_metrics.py --batch
```

4. Refresh engagement metrics for launched titles
```bash
python .agent_gaming/skills/engagement_monitor/scripts/fetch_engagement_metrics.py --batch
```

5. Rebuild the rolling release calendar
```bash
python .agent_gaming/skills/release_calendar/scripts/build_calendar.py --days 180
```

6. Tag source confidence on every new record
   - Official registry or storefront source: `primary`
   - SEC filing: `secondary`
   - Company press release or investor deck: `sponsor`

7. Generate the daily summary
   - New certification signals
   - Release-date changes in the next 180 days
   - Titles with deteriorating runway coverage
   - Titles that launched and need Day 1 engagement review
