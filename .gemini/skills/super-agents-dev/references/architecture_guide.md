# Super Agents Architecture Guide

## Core Objective
Multi-sector research and execution framework. Each agent tracks a specific **asset class** (e.g., Biotech: Products, Aerospace: Systems).

## Project Structure
- `src/super_agents/`: Core platform logic and shared packages.
- `.agent_<sector>/`: Agent definitions (configs, scripts, workflows).
- `dashboards/`: Streamlit UI and run artifacts.
- `data/`: Raw, processed, and seed data (CSV/JSON).

## Readiness Levels
- `READY`: Fully functional, tests passing, package-backed.
- `OPERATIONAL`: Runnable scripts/workflows, script-local logic.
- `PARTIAL`: Incomplete coverage or missing artifacts.
- `STUB`: Folder/Config only, no runnable scripts.

## Key Principles
1. **Asset-First**: Focus on the underlying asset before the company.
2. **Local-First**: Works entirely from the local repo.
3. **Verifiable**: Every finding must have a `source_url` and `confidence`.

## Data Flow
`Discovery -> Execute (Workflow/Skill) -> Fetch Raw -> Process -> Emit Artifacts -> Dashboard`
