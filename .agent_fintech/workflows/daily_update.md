# Fintech Daily Update

Goal: refresh the tracked fintech watchlist, capture licensing and regulatory signals, and leave
dashboard-ready artifacts for review.

## Suggested sequence

1. Refresh licensing signals across the seed watchlist:

```bash
python .agent_fintech/skills/license_tracker/scripts/fetch_licenses.py --batch --limit 25
```

2. Pull recent enforcement actions:

```bash
python .agent_fintech/skills/enforcement_monitor/scripts/fetch_enforcement_actions.py --days 90 --limit 50
```

3. Refresh company-specific adoption and partnership checks for the highest-priority names:

```bash
python .agent_fintech/skills/adoption_monitor/scripts/fetch_adoption_metrics.py --cik 1818874 --limit 3
python .agent_fintech/skills/partnership_tracker/scripts/fetch_partnerships.py --cik 1818874 --days 90
```

## Expected outputs

- raw licensing payloads in `data/raw/fintech/licenses/`
- raw enforcement payloads in `data/raw/fintech/enforcement/`
- raw adoption payloads in `data/raw/fintech/adoption/`
- raw partnership payloads in `data/raw/fintech/partnerships/`
- dashboard artifacts in `dashboards/` when the license tracker completes
