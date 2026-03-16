# Super_Agents Project

Multi-sector "asset-first" agent framework. See `project.md` for the canonical design guide.

Based on: `Desktop/Biotechpanda-main` (working biotech/pharma product tracker).

## Stack

- Python (ETL, skills, workflows)
- SQLite / PostgreSQL (data storage)
- MCP servers (agent architecture)
- YAML (configuration)
- JSON / Markdown / HTML (output)

## Approved Skills

These skills are approved for use in this project. Do not invoke skills outside this list.

### Core (17)

- `python-patterns` — core language idioms
- `python-testing` — TDD for ETL and data quality
- `python-review` — code review
- `postgres-patterns` — schema design
- `database-migrations` — schema evolution
- `api-design` — MCP server and external API patterns
- `backend-patterns` — server-side architecture
- `security-review` — API key management, input validation
- `security-scan` — automated security scanning
- `coding-standards` — cross-sector consistency
- `verification-loop` — ETL output quality
- `docker-patterns` — containerization
- `deployment-patterns` — production deployment
- `agent-harness-construction` — tool definitions and action spaces
- `agentic-engineering` — eval-first execution
- `market-research` — sector research phase
- `continuous-agent-loop` — daily/weekly/monthly workflow loops

### Secondary (5)

- `cost-aware-llm-pipeline` — LLM cost control
- `enterprise-agent-ops` — observability and lifecycle
- `eval-harness` — extraction quality measurement
- `tdd-workflow` — general TDD patterns
- `search-first` — research-before-coding

## Security Decisions

### Plugins

| Plugin | Status | Reason |
|--------|--------|--------|
| `context-mode` (mksglu) | Installed | Deny-by-default security, secret sanitization, context window optimization |
| `ccg-workflow` (fengshao1227) | Rejected | .env isolation vulnerability history, multi-model credential exposure, 72+ open issues |
| `frontend-design` | Disabled | Not relevant (no frontend) |
| `typescript-lsp` | Disabled | Not relevant (no TypeScript) |

## Universal CLI

```bash
python -m super_agents list                    # Show all agents/skills
python -m super_agents list --agent biotech    # Show biotech skills
python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals -- --days 30
python -m super_agents search --verbose        # Live search all agents
```

See `AGENTS.md` for full execution guide including Codex and Gemini CLI instructions.

## Conventions

- Asset-first: track the product/title/system/project, not the company
- Every record must have `source_url`, `source_type`, `source_confidence`
- Confidence levels: `primary`, `secondary`, `sponsor`
- Pilot with 3-5 companies before scaling
- Tighten noise before expanding coverage
- Emit both JSON (automation) and Markdown (humans) for every run
