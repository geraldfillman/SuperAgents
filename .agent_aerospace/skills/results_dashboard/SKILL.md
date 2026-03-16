# Results Dashboard

Purpose: turn the agent's JSON outputs into a single analyst-facing HTML dashboard.

Inputs:

- watchlist ranking JSON
- company scorecards JSON
- upcoming and overdue program calendar JSON

Outputs:

- self-contained HTML dashboard in `dashboards/`
- searchable ranking table
- spotlight cards for the highest-ranked names
- catalyst and risk summary panels

Notes:

- the dashboard is static HTML so it can be opened locally without a frontend build step
- it should be regenerated after ranking or calendar outputs change
