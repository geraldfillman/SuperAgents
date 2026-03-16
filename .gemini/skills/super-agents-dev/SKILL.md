---
name: super-agents-dev
description: Specialized development guide for the Super Agents project. Use when building new sector agents, modifying dashboard components, or integrating shared risk signals.
---

# Super Agents Development Skill

This skill provides the authoritative reference for the Super Agents multi-sector research framework.

## When to Use
- **New Agent Creation**: When asked to add a new sector (e.g., Cybersecurity, Space).
- **Dashboard Updates**: When modifying `dashboards/pages/` or adding reusable components.
- **Workflow Implementation**: When defining `.agent_<sector>/workflows/`.
- **Signal Integration**: When connecting agents to the Global Risk Layer.

## Core Workflows

### 1. Backend: Agent Implementation
- **Discovery**: Ensure `.agent_<sector>/config.yaml` exists.
- **Artifacts**: Every script must write JSON to `dashboards/` matching schemas in [artifact_schemas.md](references/artifact_schemas.md).
- **Packaging**: Once mature, logic should move from script-local to `src/super_agents/<sector>/`.

### 2. Frontend: Dashboard Development
- **Templates**: Use `2_Agent_Detail.py` as the template for sector pages.
- **Risk Integration**: Use `render_risk_badge(entity_name)` from `dashboards/components/risk_badge.py` to cross-reference entities.
- **Data Loading**: Use helpers in `dashboards/dashboard_data.py`.

## Key Resources
- **Architecture**: See [architecture_guide.md](references/architecture_guide.md) for project principles and data flow.
- **Schemas**: See [artifact_schemas.md](references/artifact_schemas.md) for the exact JSON contracts required by the UI.

## Readiness Gate
Before marking a task as complete, verify:
1. `current_status.json` is updated during run.
2. `run_latest.json` is emitted on completion.
3. Findings include `source_url` and `confidence`.
4. Tests cover at least 80% of new logic.
