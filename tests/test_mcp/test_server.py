"""Tests for the MCP server — tool registration and REST endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from super_agents.common.registry import AgentInfo, AgentRegistry, ScriptInfo, SkillInfo
from super_agents.mcp.server import build_app, _tool_name, _parse_tool_name


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_registry(tmp_path: Path) -> AgentRegistry:
    """Build a minimal AgentRegistry with 2 agents, 1 skill, 1 script each."""
    script_a = tmp_path / "script_a.py"
    script_b = tmp_path / "script_b.py"
    script_a.write_text('print("a")')
    script_b.write_text('print("b")')

    registry = MagicMock(spec=AgentRegistry)
    registry.all_scripts.return_value = [
        ("biotech", "fda_tracker", ScriptInfo(name="fetch_approvals", path=script_a, description="Fetch FDA approvals")),
        ("gaming", "storefront", ScriptInfo(name="fetch_metrics", path=script_b, description="Fetch storefront metrics")),
    ]
    registry.get_agent.return_value = None
    registry.summary.return_value = {"agent_count": 2, "total_skills": 2, "total_scripts": 2}
    return registry


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    registry = _make_registry(tmp_path)
    app = build_app(registry)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tool name helpers
# ---------------------------------------------------------------------------

def test_tool_name_format():
    assert _tool_name("biotech", "fda_tracker", "fetch_approvals") == "biotech__fda_tracker__fetch_approvals"


def test_tool_name_truncates_at_64():
    long = _tool_name("a" * 30, "b" * 20, "c" * 20)
    assert len(long) <= 64


def test_parse_tool_name_roundtrip():
    name = _tool_name("biotech", "fda_tracker", "fetch_approvals")
    assert _parse_tool_name(name) == ("biotech", "fda_tracker", "fetch_approvals")


def test_parse_tool_name_invalid():
    assert _parse_tool_name("no_double_underscores") is None


# ---------------------------------------------------------------------------
# /health endpoint
# ---------------------------------------------------------------------------

def test_health_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["agents"] == 2
    assert data["tools"] == 2


# ---------------------------------------------------------------------------
# /tools endpoint
# ---------------------------------------------------------------------------

def test_tools_list(client: TestClient):
    response = client.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert len(tools) == 2
    names = {t["name"] for t in tools}
    assert "biotech__fda_tracker__fetch_approvals" in names
    assert "gaming__storefront__fetch_metrics" in names


def test_tools_have_description(client: TestClient):
    tools = client.get("/tools").json()
    for tool in tools:
        assert "description" in tool
        assert tool["description"]


# ---------------------------------------------------------------------------
# /call endpoint
# ---------------------------------------------------------------------------

def test_call_missing_tool_field(client: TestClient):
    response = client.post("/call", json={"args": []})
    assert response.status_code == 400


def test_call_unknown_tool(client: TestClient):
    response = client.post("/call", json={"tool": "unknown__x__y"})
    assert response.status_code == 404


def test_call_runs_script(client: TestClient, tmp_path: Path):
    # The fixture scripts just print a letter and exit 0
    response = client.post("/call", json={"tool": "biotech__fda_tracker__fetch_approvals", "args": []})
    assert response.status_code == 200
    data = response.json()
    assert "output" in data
    assert "exit_code" in data
    assert data["exit_code"] == 0
    assert "a" in data["output"]


def test_call_invalid_json(client: TestClient):
    response = client.post("/call", content=b"not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400
