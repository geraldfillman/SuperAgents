# Super_Agents - Universal Execution Guide

## Quick Start

```bash
# List all runnable agents and skills
python -m super_agents list

# List skills for one agent
python -m super_agents list --agent biotech
python -m super_agents list --agent rare_earth

# Run a specific script
python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals -- --days 30
python -m super_agents run --agent renewable_energy --skill calendar --script build_calendar -- --window-days 180

# Run curated live search defaults
python -m super_agents search
python -m super_agents search --agent gaming --verbose
```

The CLI auto-discovers runnable agents from `.agent_*` folders. Only agents with `skills/*/scripts/*.py` are exposed.

Current CLI-visible agents:

- `aerospace`
- `autonomous_vehicles`
- `biotech`
- `fintech`
- `gaming`
- `quantum`
- `rare_earth`
- `renewable_energy`

Current `search` defaults are configured for:

- `biotech`
- `gaming`
- `aerospace`

---

## Claude Code

### Desktop and CLI

Claude Code can run these directly:

- "Run a biotech FDA search for the last 30 days"
- "List the rare earth agent skills"
- "Fetch Steam metrics for Dota 2"
- "Run the renewable energy calendar builder for the next 180 days"

Or use explicit commands:

```bash
python -m super_agents search --agent biotech --verbose
python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals -- --days 30 --limit 50
python -m super_agents run --agent gaming --skill storefront_monitor --script fetch_storefront_metrics -- --appid 570
python -m super_agents run --agent aerospace --skill award_tracker --script fetch_awards -- --days 30
python -m super_agents run --agent rare_earth --skill permit_tracker --script fetch_permits -- --days 30 --limit 25
```

### Web

Same commands work in the web interface. Example:

```text
Run: python -m super_agents list --agent quantum
```

---

## OpenAI Codex

### Codex CLI

```bash
# In the Super_Agents directory:
codex "Run python -m super_agents search --agent biotech --verbose"
codex "Run python -m super_agents run --agent gaming --skill storefront_monitor --script fetch_storefront_metrics -- --appid 570"
codex "List all available agent skills: python -m super_agents list"
codex "Run python -m super_agents list --agent rare_earth"
```

### Codex Desktop

Open the Super_Agents folder in Codex and ask:

- "Run the biotech FDA tracker to fetch drug approvals from the last 30 days"
- "Execute a live search across the configured search agents"
- "Show me what skills are available for the quantum agent"
- "Run the rare earth permit tracker"

---

## Google Gemini CLI

```bash
# In the Super_Agents directory:
gemini "Run python -m super_agents search --verbose"
gemini "Run python -m super_agents run --agent biotech --skill clinicaltrials_scraper --script fetch_trials -- --sponsor 'Moderna' --limit 10"
gemini "Run python -m super_agents list --agent aerospace"
gemini "Run python -m super_agents list --agent renewable_energy"
```

---

## Individual Script Invocation

If you want to bypass the CLI runner, invoke scripts directly.

### Aerospace Agent

```bash
python .agent_aerospace/skills/award_tracker/scripts/fetch_awards.py --days 30 --limit 10
python .agent_aerospace/skills/sbir_tracker/scripts/fetch_sbir_awards.py --agency "DOD" --year 2025
python .agent_aerospace/skills/faa_license_tracker/scripts/fetch_faa_signals.py
python .agent_aerospace/skills/sec_procurement_parser/scripts/fetch_sec_filings.py --cik "1047862"
python .agent_aerospace/skills/sam_pipeline_tracker/scripts/fetch_sam_pipeline.py
```

### Autonomous Vehicles Agent

```bash
python .agent_autonomous_vehicles/skills/permit_tracker/scripts/fetch_av_permits.py --days 30 --limit 25
python .agent_autonomous_vehicles/skills/safety_monitor/scripts/fetch_safety_reports.py --days 30 --limit 25
python .agent_autonomous_vehicles/skills/fleet_expansion_tracker/scripts/fetch_fleet_data.py --cik "1760689" --days 90
python .agent_autonomous_vehicles/skills/partnership_tracker/scripts/fetch_partnerships.py --cik "1760689" --days 180
```

### Biotech Agent

```bash
python .agent_biotech/skills/fda_tracker/scripts/fetch_drug_approvals.py --days 30 --limit 100
python .agent_biotech/skills/clinicaltrials_scraper/scripts/fetch_trials.py --sponsor "Moderna" --limit 10
python .agent_biotech/skills/sec_filings_parser/scripts/search_edgar.py --cik "1682852"
python .agent_biotech/skills/financial_monitor/scripts/fetch_financials.py --cik "1682852"
python .agent_biotech/skills/insider_tracker/scripts/monitor_form4.py --cik "1682852" --days 90
python .agent_biotech/skills/catalyst_calendar/scripts/build_calendar.py --window-days 180
python .agent_biotech/skills/conference_scraper/scripts/scrape_abstracts.py --conference "ASCO"
```

### Fintech Agent

```bash
python .agent_fintech/skills/license_tracker/scripts/fetch_licenses.py --company "SoFi" --state "CA" --limit 25
python .agent_fintech/skills/adoption_monitor/scripts/fetch_adoption_metrics.py --cik "1818874" --days 90
python .agent_fintech/skills/partnership_tracker/scripts/fetch_partnerships.py --cik "1818874" --days 180
python .agent_fintech/skills/enforcement_monitor/scripts/fetch_enforcement_actions.py --days 90 --limit 25
```

### Gaming Agent

```bash
python .agent_gaming/skills/storefront_monitor/scripts/fetch_storefront_metrics.py --appid 570
python .agent_gaming/skills/engagement_monitor/scripts/fetch_engagement_metrics.py --appid 570
python .agent_gaming/skills/studio_screener/scripts/screen_studios.py
python .agent_gaming/skills/release_calendar/scripts/build_calendar.py
```

### Quantum Agent

```bash
python .agent_quantum/skills/benchmark_tracker/scripts/fetch_benchmarks.py --days 30 --limit 25
python .agent_quantum/skills/publication_monitor/scripts/fetch_publications.py --company "IonQ" --days 30 --limit 25
python .agent_quantum/skills/patent_monitor/scripts/fetch_patents.py --assignee "IonQ" --days 365 --limit 25
python .agent_quantum/skills/roadmap_tracker/scripts/fetch_roadmap_signals.py --cik "1824920" --days 180
python .agent_quantum/skills/sbir_tracker/scripts/fetch_sbir_awards.py --days 90 --limit 25
```

### Rare Earth Agent

```bash
python .agent_rare_earth/skills/permit_tracker/scripts/fetch_permits.py --days 30 --limit 25
python .agent_rare_earth/skills/resource_estimate_parser/scripts/fetch_resource_estimates.py --cik "1951051" --limit 10
python .agent_rare_earth/skills/offtake_tracker/scripts/fetch_offtake_agreements.py --cik "1951051" --days 180
python .agent_rare_earth/skills/dpa_award_tracker/scripts/fetch_dpa_awards.py --days 365 --limit 25
python .agent_rare_earth/skills/financial_monitor/scripts/fetch_financials.py --batch
```

### Renewable Energy Agent

```bash
python .agent_renewable_energy/skills/interconnection_tracker/scripts/fetch_interconnection_queue.py --iso PJM --limit 25
python .agent_renewable_energy/skills/ppa_monitor/scripts/fetch_ppa_filings.py --cik "1711269" --days 180
python .agent_renewable_energy/skills/ira_credit_tracker/scripts/fetch_ira_credits.py --days 90 --limit 25
python .agent_renewable_energy/skills/doe_loan_tracker/scripts/fetch_doe_loans.py --days 365 --limit 25
python .agent_renewable_energy/skills/calendar/scripts/build_calendar.py --window-days 180
```

---

## Environment Variables

```bash
# Recommended for higher rate limits
export OPENFDA_API_KEY="your-key"
export SEC_EDGAR_USER_AGENT="YourName your@email.com"

# LLM-assisted extraction
export OPENAI_API_KEY="your-key"         # or
export ANTHROPIC_API_KEY="your-key"      # or
export GOOGLE_API_KEY="your-key"

# Observability
export LANGFUSE_SECRET_KEY="your-key"
export LANGFUSE_PUBLIC_KEY="your-key"
```

---

## Agent Skill Registry

The CLI only lists script-backed skills. Scaffold-only skill folders are omitted until they have runnable `scripts/*.py`.

### Aerospace (12 skills, 14 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| award_tracker | fetch_awards | USAspending.gov |
| budget_tracker | fetch_budget_lines, reconcile_budget_exposure | DoD budget data |
| faa_license_tracker | fetch_faa_signals | FAA AST |
| financial_monitor | fetch_financials | SEC EDGAR |
| insider_tracker | monitor_form4 | SEC EDGAR |
| program_calendar | build_program_calendar | Aggregated |
| results_dashboard | build_results_dashboard | Aggregated |
| sam_pipeline_tracker | fetch_sam_pipeline | SAM.gov |
| sbir_tracker | fetch_sbir_awards | SBIR.gov |
| sec_procurement_parser | fetch_sec_filings, extract_procurement_signals | SEC EDGAR |
| trl_tracker | track_trl_signals | Internal analysis |
| watchlist_ranker | build_watchlist_ranking | Internal DB |

### Autonomous Vehicles (4 skills, 4 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| permit_tracker | fetch_av_permits | California DMV, NHTSA, SEC EDGAR |
| safety_monitor | fetch_safety_reports | NHTSA |
| fleet_expansion_tracker | fetch_fleet_data | SEC EDGAR |
| partnership_tracker | fetch_partnerships | SEC EDGAR |

### Biotech (11 skills, 21 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| fda_tracker | fetch_drug_approvals, fetch_device_clearances, fetch_advisory_calendar, fetch_postmarketing | openFDA API |
| clinicaltrials_scraper | fetch_trials, detect_trial_changes, fetch_aact_snapshot_info, build_aact_index, aact_fallback | ClinicalTrials.gov v2, AACT |
| sec_filings_parser | search_edgar, extract_catalysts | SEC EDGAR |
| financial_monitor | fetch_financials, flag_offerings | SEC EDGAR |
| insider_tracker | monitor_form4 | SEC EDGAR |
| catalyst_calendar | build_calendar | Aggregated |
| company_screener | screen_companies | Internal DB |
| product_scoring | score_product | Internal DB |
| orange_book_watcher | fetch_patents | FDA Orange Book |
| conference_scraper | scrape_abstracts | Conference sites |
| data_quality | audit_stale_records, validate_sources | Internal DB |

### Fintech (4 skills, 4 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| license_tracker | fetch_licenses | NMLS, OCC |
| adoption_monitor | fetch_adoption_metrics | SEC EDGAR |
| partnership_tracker | fetch_partnerships | SEC EDGAR |
| enforcement_monitor | fetch_enforcement_actions | CFPB, OCC, SEC, FinCEN, state AGs |

### Gaming (8 skills, 10 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| storefront_monitor | fetch_storefront_metrics | Steam API |
| engagement_monitor | fetch_engagement_metrics | Steam API |
| certification_tracker | fetch_certification_signals | Internal data |
| sec_filings_parser | extract_gaming_catalysts | SEC EDGAR |
| studio_screener | screen_studios, sync_steam_appids | Steam plus DB |
| title_scoring | score_title | Internal DB |
| release_calendar | build_calendar | Aggregated |
| data_quality | audit_stale_records, validate_sources | Internal DB |

### Quantum (5 skills, 5 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| benchmark_tracker | fetch_benchmarks | SEC EDGAR, arXiv |
| publication_monitor | fetch_publications | arXiv |
| patent_monitor | fetch_patents | USPTO PatentsView |
| roadmap_tracker | fetch_roadmap_signals | SEC EDGAR |
| sbir_tracker | fetch_sbir_awards | USAspending.gov |

### Rare Earth (9 skills, 11 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| permit_tracker | fetch_permits | Federal Register |
| resource_estimate_parser | fetch_resource_estimates | SEC EDGAR |
| offtake_tracker | fetch_offtake_agreements | SEC EDGAR |
| dpa_award_tracker | fetch_dpa_awards | USAspending.gov |
| financial_monitor | fetch_financials | SEC EDGAR |
| insider_tracker | monitor_form4 | SEC EDGAR |
| sec_filings_parser | search_edgar, extract_mining_catalysts | SEC EDGAR |
| data_quality | audit_stale_records, validate_sources | Internal DB |
| mineral_scoring | score_project | Internal DB |

### Renewable Energy (8 skills, 8 scripts)

| Skill | Scripts | Data Source |
|-------|---------|-------------|
| interconnection_tracker | fetch_interconnection_queue | EIA, ISO queues |
| ppa_monitor | fetch_ppa_filings | SEC EDGAR |
| ira_credit_tracker | fetch_ira_credits | DOE, IRS, Federal Register |
| project_milestone_tracker | fetch_milestones | SEC EDGAR |
| doe_loan_tracker | fetch_doe_loans | USAspending.gov |
| sec_filings_parser | extract_energy_catalysts | SEC EDGAR |
| project_scoring | score_project | Internal DB |
| calendar | build_calendar | Aggregated |
