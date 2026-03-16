# Cybersecurity Daily Update

Run the Phase 1 cybersecurity MVP in two passes:

1. Refresh the latest KEV feed and findings artifact.
   `python -m super_agents run --agent cybersecurity --skill threat_landscape --script fetch_kev_catalog -- --days 30 --limit 50`
2. Rebuild the rolling patch calendar from the latest KEV artifact.
   `python -m super_agents run --agent cybersecurity --skill calendar --script build_patch_calendar -- --window-days 30 --limit 100`

Expected outputs:

- `dashboards/cybersecurity_current_status.json`
- `dashboards/cybersecurity_run_latest.json`
- `dashboards/cybersecurity_findings_latest.json`
- `dashboards/cybersecurity_kev_latest.json`
- `dashboards/cybersecurity_patch_calendar.json`
