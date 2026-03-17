"""Tests for GatewayClient — HTTP calls and error handling."""

from __future__ import annotations

import pytest
import httpx
import respx

from super_agents.orchestrator.gateway_client import GatewayClient

BASE = "http://localhost:9000"


@pytest.fixture()
def client() -> GatewayClient:
    return GatewayClient(base_url=BASE)


# ---------------------------------------------------------------------------
# health()
# ---------------------------------------------------------------------------

@respx.mock
def test_health_ok(client: GatewayClient):
    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200, json={
        "status": "ok", "agents": 13, "skills": 40, "tools": 80
    }))
    result = client.health()
    assert result["status"] == "ok"
    assert result["agents"] == 13


@respx.mock
def test_health_connection_error(client: GatewayClient):
    respx.get(f"{BASE}/health").mock(side_effect=httpx.ConnectError("refused"))
    result = client.health()
    assert "error" in result


@respx.mock
def test_health_timeout(client: GatewayClient):
    respx.get(f"{BASE}/health").mock(side_effect=httpx.TimeoutException("timed out"))
    result = client.health()
    assert "error" in result
    assert "timeout" in result["error"]


# ---------------------------------------------------------------------------
# list_tools()
# ---------------------------------------------------------------------------

@respx.mock
def test_list_tools_ok(client: GatewayClient):
    respx.get(f"{BASE}/tools").mock(return_value=httpx.Response(200, json=[
        {"name": "biotech__fda_tracker__fetch_approvals", "description": "Fetch FDA approvals"},
        {"name": "gaming__storefront__fetch_metrics", "description": "Fetch storefront metrics"},
    ]))
    tools = client.list_tools()
    assert len(tools) == 2
    assert tools[0]["name"] == "biotech__fda_tracker__fetch_approvals"


@respx.mock
def test_list_tools_server_offline(client: GatewayClient):
    respx.get(f"{BASE}/tools").mock(side_effect=httpx.ConnectError("refused"))
    tools = client.list_tools()
    assert tools == []


# ---------------------------------------------------------------------------
# call_tool()
# ---------------------------------------------------------------------------

@respx.mock
def test_call_tool_success(client: GatewayClient):
    respx.post(f"{BASE}/call").mock(return_value=httpx.Response(200, json={
        "output": "drug approved: XYZ",
        "stderr": "",
        "exit_code": 0,
    }))
    result = client.call_tool("biotech__fda_tracker__fetch_approvals", args=["--days", "30"])
    assert result["exit_code"] == 0
    assert "XYZ" in result["output"]


@respx.mock
def test_call_tool_sends_correct_payload(client: GatewayClient):
    route = respx.post(f"{BASE}/call").mock(return_value=httpx.Response(200, json={
        "output": "ok", "stderr": "", "exit_code": 0
    }))
    client.call_tool("biotech__fda_tracker__run", args=["--days", "7"])
    request = route.calls[0].request
    import json
    body = json.loads(request.content)
    assert body["tool"] == "biotech__fda_tracker__run"
    assert body["args"] == ["--days", "7"]


@respx.mock
def test_call_tool_http_error(client: GatewayClient):
    respx.post(f"{BASE}/call").mock(return_value=httpx.Response(404, json={"error": "unknown tool"}))
    result = client.call_tool("nonexistent__x__y")
    assert "error" in result


@respx.mock
def test_call_tool_timeout(client: GatewayClient):
    respx.post(f"{BASE}/call").mock(side_effect=httpx.TimeoutException("timed out"))
    result = client.call_tool("biotech__fda_tracker__run")
    assert "error" in result
    assert "timeout" in result["error"]


# ---------------------------------------------------------------------------
# list_servers()
# ---------------------------------------------------------------------------

@respx.mock
def test_list_servers_when_healthy(client: GatewayClient):
    respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    servers = client.list_servers()
    assert servers == ["super-agents"]


@respx.mock
def test_list_servers_when_offline(client: GatewayClient):
    respx.get(f"{BASE}/health").mock(side_effect=httpx.ConnectError("refused"))
    servers = client.list_servers()
    assert servers == []


# ---------------------------------------------------------------------------
# Auth header
# ---------------------------------------------------------------------------

@respx.mock
def test_api_key_sent_as_bearer(tmp_path):
    client = GatewayClient(base_url=BASE, api_key="secret-key")
    route = respx.get(f"{BASE}/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
    client.health()
    assert route.calls[0].request.headers["authorization"] == "Bearer secret-key"
