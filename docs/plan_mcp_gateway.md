# MCP Gateway Integration Plan

## Overview

Integrate GitHub's MCP Gateway (`gh-aw-mcpg`) as a Docker-based proxy layer between
the Super_Agents orchestrator and backend MCP servers. Each sector agent gets a
registered MCP server behind the gateway, with guard policies enforcing per-sector
access scopes. The existing tmux orchestrator gains HTTP-based tool routing alongside
its current direct-spawn model.

---

## Phase 1: Infrastructure — Docker Compose + Gateway Config

| # | File | Action |
|---|------|--------|
| 1 | `infra/mcp-gateway/config.json` | Gateway config: 3 pilot servers (crucix, biotech, shared-store) in routed mode |
| 2 | `infra/mcp-gateway/.env.example` | Template: `MCP_GATEWAY_API_KEY`, `MCP_GATEWAY_PORT=8000` |
| 3 | `docker-compose.yml` | Services: mcp-gateway + 3 backend containers, Docker socket mount |

## Phase 2: MCP Server Wrapper — Expose Skills as Tools

| # | File | Action |
|---|------|--------|
| 4 | `src/super_agents/mcp/server_wrapper.py` | Lightweight MCP server using `discover_agents()` — exposes skills as `{agent}.{skill}.{script}` tools |
| 5 | `infra/mcp-gateway/Dockerfile.mcp-server` | Generic Dockerfile with `--agent` build arg, one image per sector |

## Phase 3: Gateway Python Client

| # | File | Action |
|---|------|--------|
| 6 | `src/super_agents/orchestrator/gateway_client.py` | `GatewayClient`: `list_tools()`, `call_tool()`, `health()`, `list_servers()` via HTTP |

## Phase 4: Orchestrator Integration

| # | File | Action |
|---|------|--------|
| 7 | `src/super_agents/orchestrator/orchestrator.py` | Add `call_tool()`, `list_remote_tools()`, `gateway_status()` — purely additive |
| 8 | `src/super_agents/orchestrator/__init__.py` | Re-export `GatewayClient` |

## Phase 5: Guard Policies

| # | File | Action |
|---|------|--------|
| 9 | `infra/mcp-gateway/config.json` | `allow-only` per sector (biotech → biotech tools only), `write-sink` on shared-store |

Guard mapping:
```
biotech      → allow-only: [biotech.fda_tracker.*, biotech.clinicaltrials_scraper.*]
gaming       → allow-only: [gaming.storefront_monitor.*]
aerospace    → allow-only: [aerospace.award_tracker.*]
crucix       → allow-only: [crucix.*]  (read-only)
shared-store → write-sink: log all writes
```

## Phase 6: CLI Commands

| # | File | Action |
|---|------|--------|
| 10 | `src/super_agents/orchestrator/cli_commands.py` | `cmd_gateway_status()`, `cmd_gateway_servers()`, `cmd_gateway_tools()`, `cmd_gateway_call()` |
| 11 | `src/super_agents/cli.py` | Wire under `orchestrate gateway-status/servers/tools/call` |

## Phase 7: Dashboard Integration

| # | File | Action |
|---|------|--------|
| 12 | `dashboards/dashboard_data.py` | `load_gateway_health()` with `@st.cache_data(ttl=30)` |
| 13 | `dashboards/pages/gateway.py` | Status indicator, server table, tool counts, request log |

## Phase 8: Scale to All Agents

| # | File | Action |
|---|------|--------|
| 14 | `infra/mcp-gateway/config.json` | Expand from 3 to all 13 sector agents |
| 15 | `infra/mcp-gateway/generate_config.py` | Auto-generates config.json from `discover_agents()` |

## Phase 9: VPS Deployment

| # | File | Action |
|---|------|--------|
| 16 | `infra/mcp-gateway/docker-compose.prod.yml` | Restart policies, memory limits, log rotation, health checks |
| 17 | `infra/mcp-gateway/deploy.sh` | Ubuntu deploy script: checks Docker, builds images, starts gateway, verifies health |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Config format changes between versions | Pin image tag (not `:latest`) |
| Docker socket security on shared VPS | Non-root container + Docker socket proxy |
| 13 containers consume too much memory | Start with 3; optionally use single multi-agent MCP server |
| Gateway = single point of failure | tmux direct-spawn stays as fallback |
| HTTP proxy latency vs stdio | Localhost = sub-ms; not an issue for ETL workloads |

## Success Criteria

- [ ] `docker compose up` starts gateway + 3 backends
- [ ] `python -m super_agents orchestrate gateway-status` shows healthy
- [ ] `python -m super_agents orchestrate gateway-tools --server biotech` lists tools
- [ ] Guard policies prevent cross-sector access
- [ ] Existing tmux orchestrator unchanged (backward compatible)
- [ ] Dashboard shows gateway health
- [ ] 80%+ test coverage on new code
- [ ] VPS deploy script works on Ubuntu 22.04
