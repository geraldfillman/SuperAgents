"""Single multi-agent MCP server.

Uses AgentRegistry to auto-discover all sector agents at startup and exposes
every (agent, skill, script) triple as an MCP tool named:

    {agent}__{skill}__{script}

Double-underscore separators keep names within the MCP ^[a-zA-Z0-9_-]{1,64}$
constraint. Guard policies enforcing per-sector access live at the gateway layer;
this server exposes all tools unconditionally.

Tool execution spawns the script as a subprocess, matching CLI behaviour.

Run:
    MCP_SERVER_PORT=9000 python -m super_agents.mcp.server
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import uvicorn
from mcp import types
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from super_agents.common.paths import PROJECT_ROOT
from super_agents.common.registry import AgentRegistry, ScriptInfo

logger = logging.getLogger(__name__)

# MCP spec: tool names must match ^[a-zA-Z0-9_-]{1,64}$
_MAX_TOOL_NAME = 64


# ---------------------------------------------------------------------------
# Tool name helpers
# ---------------------------------------------------------------------------

def _tool_name(agent: str, skill: str, script: str) -> str:
    name = f"{agent}__{skill}__{script}"
    if len(name) > _MAX_TOOL_NAME:
        # Preserve agent prefix for guard policy matching; truncate from the middle
        truncated = name[:_MAX_TOOL_NAME]
        logger.warning("Tool name truncated to %d chars: %s -> %s", _MAX_TOOL_NAME, name, truncated)
        return truncated
    return name


def _parse_tool_name(name: str) -> tuple[str, str, str] | None:
    parts = name.split("__")
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

def _build_mcp_server(registry: AgentRegistry) -> tuple[Server, dict[str, ScriptInfo]]:
    """Build the MCP Server and return it alongside the tool -> ScriptInfo map."""
    server = Server("super-agents")

    tool_list: list[types.Tool] = []
    tool_map: dict[str, ScriptInfo] = {}

    for agent_name, skill_name, script_info in registry.all_scripts():
        name = _tool_name(agent_name, skill_name, script_info.name)

        agent = registry.get_agent(agent_name)
        skill = agent.get_skill(skill_name) if agent else None
        description = f"[{agent_name}/{skill_name}] {script_info.description}"
        if skill and skill.description:
            description = f"[{agent_name}/{skill_name}] {skill.description} — {script_info.description}"

        tool_list.append(types.Tool(
            name=name,
            description=description,
            inputSchema={
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "CLI arguments passed directly to the script. "
                            "Example: [\"--days\", \"30\", \"--limit\", \"10\"]"
                        ),
                        "default": [],
                    }
                },
            },
        ))
        tool_map[name] = script_info

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return tool_list

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        script_info = tool_map.get(name)
        if not script_info:
            raise ValueError(f"Unknown tool: {name}")

        args: list[str] = arguments.get("args") or []
        cmd = [sys.executable, str(script_info.path)] + args

        logger.info("Executing tool %s: %s", name, " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            return [types.TextContent(type="text", text="[ERROR] Script timed out after 120s")]
        except Exception as exc:
            return [types.TextContent(type="text", text=f"[ERROR] {exc}")]

        output = stdout.decode(errors="replace").strip()
        if proc.returncode != 0:
            err = stderr.decode(errors="replace").strip()
            output = f"[EXIT {proc.returncode}]\n{output}\n[STDERR]\n{err}" if output else f"[EXIT {proc.returncode}]\n[STDERR]\n{err}"

        return [types.TextContent(type="text", text=output or "(no output)")]

    return server, tool_map


# ---------------------------------------------------------------------------
# Starlette app — /health + MCP SSE routes
# ---------------------------------------------------------------------------

def build_app(registry: AgentRegistry) -> Starlette:
    mcp_server, tool_map = _build_mcp_server(registry)
    sse = SseServerTransport("/mcp/messages/")

    async def handle_sse(request: Request) -> Response:
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )
        return Response()

    async def handle_messages(request: Request) -> Response:
        await sse.handle_post_message(request.scope, request.receive, request._send)
        return Response()

    async def health(_: Request) -> JSONResponse:
        summary = registry.summary()
        return JSONResponse({
            "status": "ok",
            "agents": summary["agent_count"],
            "skills": summary["total_skills"],
            "tools": len(tool_map),
        })

    async def tools_list(_: Request) -> JSONResponse:
        return JSONResponse([
            {"name": t.name, "description": t.description}
            for t in tool_list
        ])

    async def call_rest(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid JSON body"}, status_code=400)

        tool_name = body.get("tool")
        if not tool_name:
            return JSONResponse({"error": "missing 'tool' field"}, status_code=400)

        script_info = tool_map.get(tool_name)
        if not script_info:
            return JSONResponse({"error": f"unknown tool: {tool_name}"}, status_code=404)

        args: list[str] = body.get("args") or []
        cmd = [sys.executable, str(script_info.path)] + args
        logger.info("REST call tool %s: %s", tool_name, " ".join(cmd))

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(PROJECT_ROOT),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            return JSONResponse({"error": "script timed out after 120s"}, status_code=504)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)

        output = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()
        return JSONResponse({
            "output": output or "(no output)",
            "stderr": err,
            "exit_code": proc.returncode,
        })

    return Starlette(routes=[
        Route("/health", health),
        Route("/tools", tools_list),
        Route("/call", call_rest, methods=["POST"]),
        Route("/mcp", handle_sse),
        Mount("/mcp/messages", app=handle_messages),
    ])


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    port = int(os.environ.get("MCP_SERVER_PORT", "9000"))

    logger.info("Discovering agents from %s ...", PROJECT_ROOT)
    registry = AgentRegistry(PROJECT_ROOT)
    summary = registry.summary()
    logger.info(
        "Registry ready: %d agents, %d skills, %d tools",
        summary["agent_count"],
        summary["total_skills"],
        summary["total_scripts"],
    )

    app = build_app(registry)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
