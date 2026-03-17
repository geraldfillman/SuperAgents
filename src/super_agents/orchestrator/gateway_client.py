"""GatewayClient — HTTP client for the MCP server's REST endpoints.

Reads MCP_SERVER_URL (default http://localhost:9000) from env.
MCP_GATEWAY_API_KEY is optional — include if the gateway requires auth.

Usage:
    from super_agents.orchestrator.gateway_client import GatewayClient

    client = GatewayClient()
    print(client.health())
    print(client.list_tools())
    result = client.call_tool("biotech__fda_tracker__fetch_drug_approvals", args=["--days", "30"])
    print(result["output"])
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_DEFAULT_SERVER_URL = "http://localhost:9000"
_DEFAULT_TIMEOUT = 30.0
_CALL_TIMEOUT = 130.0  # tool scripts can run up to 120s + margin


class GatewayClient:
    """Thin HTTP client wrapping the mcp-server REST endpoints.

    All methods return plain dicts/lists — no MCP protocol objects.
    Methods return a dict with an ``"error"`` key on failure rather than raising,
    so callers can handle gracefully (e.g. dashboard showing an offline state).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._base_url = (base_url or os.environ.get("MCP_SERVER_URL", _DEFAULT_SERVER_URL)).rstrip("/")
        self._api_key = api_key or os.environ.get("MCP_GATEWAY_API_KEY")
        self._timeout = timeout

    # -- Public API ---------------------------------------------------------

    def health(self) -> dict[str, Any]:
        """GET /health — returns server status dict or ``{"error": ...}``."""
        return self._get("/health")

    def list_tools(self) -> list[dict[str, Any]]:
        """GET /tools — returns list of ``{"name": ..., "description": ...}`` dicts.

        Returns an empty list on error.
        """
        result = self._get("/tools")
        if isinstance(result, list):
            return result
        if "error" in result:
            logger.warning("list_tools: %s", result["error"])
        return []

    def call_tool(
        self,
        tool_name: str,
        *,
        args: list[str] | None = None,
    ) -> dict[str, Any]:
        """POST /call — run a tool and return ``{"output": ..., "exit_code": ...}``.

        Returns ``{"error": ...}`` on HTTP/network failure.
        """
        return self._post("/call", {"tool": tool_name, "args": args or []}, timeout=_CALL_TIMEOUT)

    def list_servers(self) -> list[str]:
        """Return the list of registered server names.

        With a single multi-agent server this always returns ``["super-agents"]``
        when healthy, empty list when unreachable.
        """
        h = self.health()
        if "error" in h:
            return []
        return ["super-agents"]

    # -- HTTP helpers -------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _get(self, path: str) -> dict[str, Any] | list[Any]:
        url = f"{self._base_url}{path}"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            logger.debug("GatewayClient GET %s timed out", path)
            return {"error": f"timeout after {self._timeout}s", "url": url}
        except httpx.HTTPStatusError as exc:
            logger.debug("GatewayClient GET %s → HTTP %d", path, exc.response.status_code)
            return {"error": f"HTTP {exc.response.status_code}", "url": url}
        except Exception as exc:  # noqa: BLE001
            logger.debug("GatewayClient GET %s failed: %s", path, exc)
            return {"error": str(exc), "url": url}

    def _post(self, path: str, payload: dict[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers={**self._headers(), "Content-Type": "application/json"},
                timeout=timeout or self._timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            t = timeout or self._timeout
            logger.debug("GatewayClient POST %s timed out after %ss", path, t)
            return {"error": f"timeout after {t}s", "url": url}
        except httpx.HTTPStatusError as exc:
            logger.debug("GatewayClient POST %s → HTTP %d", path, exc.response.status_code)
            try:
                detail = exc.response.json()
            except Exception:
                detail = exc.response.text
            return {"error": f"HTTP {exc.response.status_code}", "detail": detail, "url": url}
        except Exception as exc:  # noqa: BLE001
            logger.debug("GatewayClient POST %s failed: %s", path, exc)
            return {"error": str(exc), "url": url}


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_client: GatewayClient | None = None


def get_gateway_client() -> GatewayClient:
    """Return the module-level singleton GatewayClient (creates on first call)."""
    global _default_client  # noqa: PLW0603
    if _default_client is None:
        _default_client = GatewayClient()
    return _default_client
