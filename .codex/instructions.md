# Super_Agents — Codex Instructions

This is a Python monorepo with 3 sector-specific research agents (biotech, gaming, aerospace/defense). Each agent has skills that fetch data from free public APIs.

## How to Run Agents

Use the universal CLI runner:

```bash
# List all agents and available skills
python -m super_agents list

# Run a specific skill
python -m super_agents run --agent <agent> --skill <skill> --script <script> -- [args]

# Run live search across all agents
python -m super_agents search --verbose
```

## Common Tasks

### Biotech: Search FDA drug approvals
```bash
python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals -- --days 30 --limit 50
```

### Biotech: Search clinical trials
```bash
python -m super_agents run --agent biotech --skill clinicaltrials_scraper --script fetch_trials -- --sponsor "Moderna" --limit 10
```

### Biotech: Search SEC filings
```bash
python -m super_agents run --agent biotech --skill sec_filings_parser --script search_edgar -- --ticker "MRNA"
```

### Gaming: Steam storefront data
```bash
python -m super_agents run --agent gaming --skill storefront_monitor --script fetch_storefront_metrics -- --appid 570
```

### Aerospace: Government contract awards
```bash
python -m super_agents run --agent aerospace --skill award_tracker --script fetch_awards -- --days 30
```

## Project Structure

- `src/super_agents/` — Shared library (CIK normalization, LLM client, DB engine)
- `.agent_biotech/skills/` — 11 biotech data skills (FDA, trials, SEC, calendars)
- `.agent_gaming/skills/` — 9 gaming data skills (Steam, storefronts, releases)
- `.agent_aerospace/skills/` — 12 aerospace skills (contracts, budgets, FAA, SBIR)
- `dashboards/` — Streamlit multi-page dashboard (run with `python -m streamlit run dashboards/app.py`)
- `schema/` — SQL table definitions
- `data/` — Raw and processed output data

## Environment Variables (optional)

- `OPENFDA_API_KEY` — Higher rate limits for FDA queries
- `SEC_EDGAR_USER_AGENT` — Required header for SEC EDGAR (format: "Name email@example.com")
- `DATABASE_URL` — Database connection (defaults to SQLite)

## Key Conventions

- Asset-first architecture: track the product/title/system, not just the company
- Every record has `source_url`, `source_type`, `source_confidence`
- Output goes to `data/raw/<sector>/` and `data/processed/<sector>/`
- Dashboard reads from `dashboards/runs/<agent>/<timestamp>/summary.json`
