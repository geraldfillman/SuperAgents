---
description: Weekly review — add new companies, review 90-day catalysts, re-rank products, audit stale records
---

# Weekly Review Workflow

Run every Monday to maintain coverage quality and product rankings.

## Steps

1. **Screen for new companies**
   - Run company screener for newly listed biotech/pharma/medtech names
   - Check for IPOs, uplists, or newly active clinical programs
// turbo
```bash
python .agent/skills/company_screener/scripts/screen_companies.py
```

2. **Review all catalysts in next 90 days**
// turbo
```bash
python .agent/skills/catalyst_calendar/scripts/build_calendar.py --days 90 --format csv --output dashboards/weekly_catalyst_review.csv
```

3. **Re-rank products by evidence maturity and regulatory visibility**
   - Run product scoring for all active products
   - Sort by composite score and binary event risk
   - Identify products with score changes >10 points

4. **Audit stale records**
// turbo
```bash
python .agent/skills/data_quality/scripts/audit_stale_records.py --days 60
```

5. **Validate source integrity**
// turbo
```bash
python .agent/skills/data_quality/scripts/validate_sources.py
```

6. **Generate weekly report**
   - New companies added this week
   - Catalyst calendar summary (next 90 days by type)
   - Product ranking changes
   - Stale record count and recommended actions
   - Indication coverage distribution
