---
description: Weekly review - re-rank titles, review runway risk, and audit stale records
---

# Weekly Review Workflow

Run every Monday to keep coverage quality high and title priorities explicit.

## Steps

1. Screen for new listed studios
```bash
python .agent_gaming/skills/studio_screener/scripts/screen_studios.py
```

2. Review all catalysts in the next 180 days
```bash
python .agent_gaming/skills/release_calendar/scripts/build_calendar.py --days 180 --format csv --output dashboards/gaming_release_review.csv
```

3. Re-score all active titles
```bash
python .agent_gaming/skills/title_scoring/scripts/score_title.py --batch --active-only
```

4. Audit stale records
```bash
python .agent_gaming/skills/data_quality/scripts/audit_stale_records.py --days 45
```

5. Validate source integrity
```bash
python .agent_gaming/skills/data_quality/scripts/validate_sources.py
```

6. Generate the weekly report
   - New studios added this week
   - Titles at highest launch-delay risk
   - Titles with strong storefront momentum
   - Titles with weak funding resilience
