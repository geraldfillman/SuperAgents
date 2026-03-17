"""Shared dashboard data-loading helpers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import urlopen

import streamlit as st
import yaml

from super_agents.integrations.mirofish.zep import summarize_bundle_activity

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DASHBOARDS_DIR = Path(__file__).resolve().parent
RUNS_DIR = DASHBOARDS_DIR / "runs"
MIROFISH_BUNDLES_DIR = PROJECT_ROOT / "data" / "processed" / "mirofish_simulations"
MIROFISH_RUNTIME_HOME = PROJECT_ROOT / "_reviews" / "MiroFish"
MIROFISH_RUNTIME_PYTHON = PROJECT_ROOT / ".venv-mirofish" / "Scripts" / "python.exe"
MIROFISH_PUBLISH_SCRIPT = (
    PROJECT_ROOT
    / ".agent_simulation"
    / "skills"
    / "mirofish_runtime"
    / "scripts"
    / "publish_bundle_to_zep.py"
)
DEFAULT_MIROFISH_FRONTEND_URL = "http://127.0.0.1:3000"
DEFAULT_MIROFISH_BACKEND_URL = "http://127.0.0.1:5001"


def humanize_name(name: str) -> str:
    """Convert a slug into a human-readable label."""
    return name.replace("_", " ").replace("-", " ").strip().title()


def _safe_load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _safe_load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


@st.cache_data(ttl=300)
def discover_runnable_agents(project_root: Path = PROJECT_ROOT) -> list[dict[str, Any]]:
    """Discover runnable agents from on-disk configs and script folders."""
    agents: list[dict[str, Any]] = []

    for agent_dir in sorted(project_root.glob(".agent_*")):
        skills_root = agent_dir / "skills"
        if not skills_root.is_dir():
            continue

        skill_names: list[str] = []
        script_count = 0

        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue
            scripts_dir = skill_dir / "scripts"
            if not scripts_dir.is_dir():
                continue
            scripts = sorted(scripts_dir.glob("*.py"))
            if not scripts:
                continue
            skill_names.append(skill_dir.name)
            script_count += len(scripts)

        if script_count == 0:
            continue

        agent_name = agent_dir.name[len(".agent_") :]
        config_path = agent_dir / "config.yaml"
        config = _safe_load_yaml(config_path) if config_path.exists() else {}
        agent_config = config.get("agent", {}) if isinstance(config.get("agent"), dict) else {}
        description = agent_config.get("description") or humanize_name(agent_name)

        agents.append(
            {
                "name": agent_name,
                "label": humanize_name(agent_name),
                "description": str(description),
                "dir": agent_dir,
                "config_exists": config_path.exists(),
                "skill_names": skill_names,
                "skill_count": len(skill_names),
                "script_count": script_count,
                "workflow_count": len(list((agent_dir / "workflows").glob("*.md"))),
            }
        )

    return agents


def discover_agent_names(project_root: Path = PROJECT_ROOT) -> list[str]:
    """Return discovered runnable agent names."""
    return [agent["name"] for agent in discover_runnable_agents(project_root)]


def load_agent_status(
    agent_name: str,
    dashboards_dir: Path = DASHBOARDS_DIR,
) -> dict[str, Any] | None:
    """Load the current-status artifact for one agent."""
    data = _safe_load_json(dashboards_dir / f"{agent_name}_current_status.json")
    return data if isinstance(data, dict) else None


def load_agent_latest_run(
    agent_name: str,
    dashboards_dir: Path = DASHBOARDS_DIR,
) -> dict[str, Any] | None:
    """Load the latest run summary for one agent."""
    data = _safe_load_json(dashboards_dir / f"{agent_name}_run_latest.json")
    return data if isinstance(data, dict) else None


def load_agent_findings(
    agent_name: str,
    dashboards_dir: Path = DASHBOARDS_DIR,
) -> list[dict[str, Any]]:
    """Load the latest rolling findings for one agent."""
    data = _safe_load_json(dashboards_dir / f"{agent_name}_findings_latest.json")
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


@st.cache_data(ttl=300)
def load_all_runs(runs_dir: Path = RUNS_DIR) -> list[dict[str, Any]]:
    """Load run summaries across all agents."""
    runs: list[dict[str, Any]] = []
    if not runs_dir.exists():
        return runs

    for agent_dir in sorted(runs_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        for run_dir in sorted(agent_dir.iterdir(), reverse=True):
            summary_path = run_dir / "summary.json"
            data = _safe_load_json(summary_path)
            if not isinstance(data, dict):
                continue
            data["_md_path"] = run_dir / "summary.md"
            runs.append(data)

    runs.sort(
        key=lambda run: (
            run.get("completed_at", ""),
            run.get("started_at", ""),
            run.get("run_id", ""),
        ),
        reverse=True,
    )
    return runs


@st.cache_data(ttl=300)
def load_all_findings(
    agent_names: Iterable[str] | None = None,
    dashboards_dir: Path = DASHBOARDS_DIR,
    project_root: Path = PROJECT_ROOT,
) -> list[dict[str, Any]]:
    """Load rolling findings across the discovered fleet."""
    all_findings: list[dict[str, Any]] = []
    names = list(agent_names) if agent_names is not None else discover_agent_names(project_root)

    for agent_name in names:
        for finding in load_agent_findings(agent_name, dashboards_dir):
            enriched = dict(finding)
            enriched["_agent"] = agent_name
            all_findings.append(enriched)

    all_findings.sort(key=lambda finding: finding.get("finding_time", ""), reverse=True)
    return all_findings


@st.cache_data(ttl=300)
def load_calendar_events(
    pattern: str,
    dashboards_dir: Path = DASHBOARDS_DIR,
) -> list[dict[str, Any]]:
    """Load calendar-style events from matching dashboard JSON files."""
    events: list[dict[str, Any]] = []
    for path in sorted(dashboards_dir.glob(pattern)):
        data = _safe_load_json(path)
        if not isinstance(data, list):
            continue
        events.extend(item for item in data if isinstance(item, dict))
    events.sort(key=lambda event: event.get("date", ""))
    return events


def _http_status(url: str, timeout_seconds: float = 1.0) -> int | None:
    try:
        with urlopen(url, timeout=timeout_seconds) as response:
            return int(getattr(response, "status", 200))
    except (OSError, URLError, ValueError):
        return None


def detect_mirofish_services(
    frontend_url: str = DEFAULT_MIROFISH_FRONTEND_URL,
    backend_url: str = DEFAULT_MIROFISH_BACKEND_URL,
) -> dict[str, Any]:
    """Return local MiroFish runtime and HTTP service status."""

    frontend_status = _http_status(frontend_url)
    backend_status = _http_status(f"{backend_url}/api/graph/project/list")
    return {
        "frontend_url": frontend_url,
        "backend_url": backend_url,
        "frontend_status_code": frontend_status,
        "backend_status_code": backend_status,
        "frontend_reachable": frontend_status is not None and frontend_status < 500,
        "backend_reachable": backend_status == 200,
        "runtime_home_exists": MIROFISH_RUNTIME_HOME.exists(),
        "runtime_python_exists": MIROFISH_RUNTIME_PYTHON.exists(),
        "publish_script_exists": MIROFISH_PUBLISH_SCRIPT.exists(),
    }


def build_mirofish_publish_command(
    bundle_dir: str | Path,
    *,
    force: bool = True,
) -> list[str]:
    """Build the publish command that uses the dedicated MiroFish Python runtime."""

    command = [
        str(MIROFISH_RUNTIME_PYTHON),
        str(MIROFISH_PUBLISH_SCRIPT),
        "--bundle-dir",
        str(Path(bundle_dir).resolve()),
        "--json",
    ]
    if force:
        command.append("--force")
    return command


def format_mirofish_publish_command(
    bundle_dir: str | Path,
    *,
    force: bool = True,
) -> str:
    """Return a copy-pasteable PowerShell command for publishing one bundle."""

    bundle_path = str(Path(bundle_dir).resolve())
    force_flag = " --force" if force else ""
    return (
        f".\\.venv-mirofish\\Scripts\\python.exe "
        f".agent_simulation\\skills\\mirofish_runtime\\scripts\\publish_bundle_to_zep.py "
        f"--bundle-dir \"{bundle_path}\" --json{force_flag}"
    )


def build_mirofish_embed_url(process_url: str | None) -> str | None:
    """Return an embed-friendly MiroFish URL with graph-only English defaults."""

    if not process_url:
        return None

    parsed = urlsplit(process_url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("embed", "1")
    query.setdefault("lang", "en")
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query),
            parsed.fragment,
        )
    )


def load_simulation_bundle(
    bundle_dir: str | Path,
) -> dict[str, Any] | None:
    """Load one MiroFish simulation bundle with optional Zep publish metadata."""

    bundle_path = Path(bundle_dir).resolve()
    config = _safe_load_json(bundle_path / "simulation_config.json")
    if not isinstance(config, dict):
        return None

    publish_result = _safe_load_json(bundle_path / "zep_publish_result.json")
    publish_result = publish_result if isinstance(publish_result, dict) else {}
    import_record = _safe_load_json(bundle_path / "zep_import.json")
    import_record = import_record if isinstance(import_record, dict) else {}
    bundle_summary = _safe_load_json(bundle_path / "bundle_summary.json")
    bundle_summary = bundle_summary if isinstance(bundle_summary, dict) else {}
    activity = summarize_bundle_activity(bundle_path)

    simulation_id = str(config.get("simulation_id") or bundle_path.name)
    graph_data = publish_result.get("graph_data", {})
    graph_data = graph_data if isinstance(graph_data, dict) else {}
    imported_at = (
        import_record.get("imported_at")
        or publish_result.get("imported_at")
        or config.get("completed_at")
        or datetime_from_path(bundle_path / "zep_publish_result.json")
        or datetime_from_path(bundle_path / "simulation_config.json")
    )

    return {
        "simulation_id": simulation_id,
        "label": humanize_name(simulation_id.replace("sim_", "")),
        "bundle_dir": bundle_path,
        "project_id": publish_result.get("project_id") or import_record.get("project_id") or config.get("project_id"),
        "graph_id": publish_result.get("graph_id") or import_record.get("graph_id") or config.get("graph_id"),
        "graph_name": publish_result.get("graph_name") or humanize_name(simulation_id),
        "simulation_requirement": config.get("simulation_requirement", ""),
        "agent_count": len(config.get("agent_configs", [])),
        "platforms": activity.get("platforms", []),
        "action_counts": activity.get("action_counts", {}),
        "recent_actions": activity.get("recent_actions", []),
        "published": bool(publish_result.get("graph_id")),
        "published_at": imported_at,
        "process_url": publish_result.get("process_url"),
        "simulation_url": publish_result.get("simulation_url"),
        "result_path": publish_result.get("result_path"),
        "import_record_path": publish_result.get("import_record_path") or import_record.get("import_record_path"),
        "node_count": graph_data.get("node_count") or bundle_summary.get("node_count") or 0,
        "edge_count": graph_data.get("edge_count") or bundle_summary.get("edge_count") or 0,
        "summary": publish_result.get("summary") or bundle_summary,
    }


# ---------------------------------------------------------------------------
# Crucix integration helpers
# ---------------------------------------------------------------------------

CRUCIX_SIGNALS_DB = PROJECT_ROOT / "data" / "signals.db"
CRUCIX_RUNS_DIR = PROJECT_ROOT / "crucix" / "runs"
SIMULATION_RUNS_DIR = PROJECT_ROOT / "runs" / "simulations"

# Agent-to-sector mapping (mirrors source_map.py sectors)
AGENT_SECTOR_MAP: dict[str, dict[str, Any]] = {
    "aerospace": {
        "sector": "aerospace",
        "icon": "🚀",
        "color": "#4A90D9",
        "description": "Defense, aviation, and space systems",
    },
    "autonomous_vehicles": {
        "sector": "autonomous_vehicles",
        "icon": "🚗",
        "color": "#7B68EE",
        "description": "Self-driving vehicles and mobility tech",
    },
    "biotech": {
        "sector": "biotech",
        "icon": "🧬",
        "color": "#2ECC71",
        "description": "Pharmaceuticals, drug approvals, clinical trials",
    },
    "cannabis_psychedelics": {
        "sector": "cannabis_psychedelics",
        "icon": "🌿",
        "color": "#1ABC9C",
        "description": "Regulatory trends in emerging therapeutic markets",
    },
    "cybersecurity": {
        "sector": "cybersecurity",
        "icon": "🔒",
        "color": "#E74C3C",
        "description": "Threat intelligence, vulnerabilities, patches",
    },
    "fintech": {
        "sector": "fintech",
        "icon": "💰",
        "color": "#F39C12",
        "description": "Financial markets, payments, regulatory",
    },
    "gaming": {
        "sector": "gaming",
        "icon": "🎮",
        "color": "#9B59B6",
        "description": "Game industry, storefronts, player metrics",
    },
    "meddevice": {
        "sector": "meddevice",
        "icon": "🩺",
        "color": "#3498DB",
        "description": "Medical devices, diagnostics, and health tech",
    },
    "quantum": {
        "sector": "quantum",
        "icon": "⚛️",
        "color": "#00CED1",
        "description": "Quantum computing, cryptography, research",
    },
    "rare_earth": {
        "sector": "rare_earth",
        "icon": "⛏️",
        "color": "#CD853F",
        "description": "Critical minerals, supply chains, trade flows",
    },
    "renewable_energy": {
        "sector": "renewable_energy",
        "icon": "⚡",
        "color": "#27AE60",
        "description": "Solar, wind, nuclear, energy policy",
    },
    "simulation": {
        "sector": "simulation",
        "icon": "🎯",
        "color": "#95A5A6",
        "description": "Scenario simulation and what-if analysis",
    },
    "space": {
        "sector": "space",
        "icon": "🌌",
        "color": "#2C3E50",
        "description": "Commercial space, orbital economy, and launch",
    },
}


def get_agent_sector(agent_name: str) -> dict[str, Any]:
    """Return sector metadata for an agent, with fallback."""
    return AGENT_SECTOR_MAP.get(agent_name, {
        "sector": agent_name,
        "icon": "📦",
        "color": "#BDC3C7",
        "description": "",
    })


def group_agents_by_sector(
    agents: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Group agents into sector categories for organized display."""
    # Define sector groupings
    groups: dict[str, list[str]] = {
        "Intelligence & Defense": ["aerospace", "cybersecurity", "autonomous_vehicles", "space"],
        "Markets & Finance": ["fintech", "rare_earth", "renewable_energy", "cannabis_psychedelics"],
        "Science & Technology": ["biotech", "quantum", "gaming", "meddevice"],
        "Operations": ["simulation"],
    }

    result: dict[str, list[dict[str, Any]]] = {}
    assigned: set[str] = set()

    for group_name, sector_names in groups.items():
        group_agents = [a for a in agents if a["name"] in sector_names]
        if group_agents:
            result[group_name] = group_agents
            assigned.update(a["name"] for a in group_agents)

    # Catch any ungrouped agents
    ungrouped = [a for a in agents if a["name"] not in assigned]
    if ungrouped:
        result["Other"] = ungrouped

    return result


def load_crucix_status() -> dict[str, Any]:
    """Load Crucix integration status without importing runner (avoids Node dep)."""
    crucix_dir = PROJECT_ROOT / "crucix"
    return {
        "installed": (crucix_dir / "package.json").exists() and (crucix_dir / "node_modules").exists(),
        "cloned": (crucix_dir / "package.json").exists(),
        "latest_briefing_exists": (CRUCIX_RUNS_DIR / "latest.json").exists(),
        "signals_db_exists": CRUCIX_SIGNALS_DB.exists(),
        "crucix_dir": str(crucix_dir),
    }


def load_crucix_source_map() -> dict[str, dict[str, Any]]:
    """Load the Crucix source-to-sector mapping."""
    try:
        from super_agents.integrations.crucix.source_map import CRUCIX_SOURCE_MAP
        return dict(CRUCIX_SOURCE_MAP)
    except ImportError:
        return {}


@st.cache_data(ttl=300)
def load_crucix_signal_stats() -> dict[str, Any]:
    """Load signal store statistics if the DB exists."""
    if not CRUCIX_SIGNALS_DB.exists():
        return {"total_signals": 0, "sources": [], "top_topics": {}}
    try:
        from super_agents.integrations.crucix.store import SignalStore
        with SignalStore(CRUCIX_SIGNALS_DB) as store:
            return store.stats()
    except Exception:
        return {"total_signals": 0, "sources": [], "top_topics": {}}


def load_latest_briefing_summary() -> dict[str, Any] | None:
    """Load and summarize the latest Crucix briefing."""
    latest = CRUCIX_RUNS_DIR / "latest.json"
    if not latest.exists():
        return None
    data = _safe_load_json(latest)
    if not isinstance(data, dict):
        return None

    results = data.get("results", [])
    ok_count = sum(1 for r in results if r.get("status") == "ok")
    error_count = sum(1 for r in results if r.get("status") != "ok")
    sources = [r.get("name", "unknown") for r in results]
    timestamp = data.get("crucix", {}).get("timestamp", "")

    return {
        "timestamp": timestamp,
        "total_sources": len(results),
        "ok_sources": ok_count,
        "error_sources": error_count,
        "source_names": sources,
        "ok_source_names": [r.get("name") for r in results if r.get("status") == "ok"],
        "error_source_names": [r.get("name") for r in results if r.get("status") != "ok"],
    }


@st.cache_data(ttl=300)
def discover_simulation_results(
    sim_dir: Path = SIMULATION_RUNS_DIR,
) -> list[dict[str, Any]]:
    """Discover scenario simulation results (from the new engine)."""
    results: list[dict[str, Any]] = []
    if not sim_dir.exists():
        return results

    for json_file in sorted(sim_dir.glob("*.json"), reverse=True):
        data = _safe_load_json(json_file)
        if not isinstance(data, dict) or "scenario" not in data:
            continue
        results.append({
            "file": json_file,
            "scenario": data.get("scenario", ""),
            "description": data.get("description", ""),
            "tick_count": data.get("tick_count", 0),
            "signal_count": data.get("signal_count", 0),
            "started_at": data.get("started_at", ""),
            "completed_at": data.get("completed_at", ""),
            "alerts": data.get("alerts", []),
            "predictions": data.get("predictions", []),
            "final_variables": data.get("final_variables", {}),
            "variable_history": data.get("variable_history", []),
            "hypotheses": data.get("hypotheses", []),
            "ticks": data.get("ticks", []),
        })

    return results


# ---------------------------------------------------------------------------
# MCP Gateway helpers
# ---------------------------------------------------------------------------

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:9000")


@st.cache_data(ttl=30)
def load_gateway_health(server_url: str = MCP_SERVER_URL) -> dict[str, Any]:
    """Fetch /health from the MCP server. Returns error dict when unreachable."""
    status = _http_status(f"{server_url}/health")
    if status is None:
        return {"status": "offline", "error": f"unreachable at {server_url}"}
    try:
        import json as _json
        from urllib.request import urlopen as _urlopen
        with _urlopen(f"{server_url}/health", timeout=2.0) as resp:
            data = _json.loads(resp.read())
        return data if isinstance(data, dict) else {"status": "ok"}
    except Exception:
        return {"status": "unknown", "error": f"HTTP {status}"}


@st.cache_data(ttl=30)
def load_gateway_tools(server_url: str = MCP_SERVER_URL) -> list[dict[str, Any]]:
    """Fetch /tools from the MCP server. Returns empty list when unreachable."""
    try:
        import json as _json
        from urllib.request import urlopen as _urlopen
        with _urlopen(f"{server_url}/tools", timeout=5.0) as resp:
            data = _json.loads(resp.read())
        return data if isinstance(data, list) else []
    except Exception:
        return []


def datetime_from_path(path: Path) -> str | None:
    """Best-effort ISO timestamp from a file's mtime."""

    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat()


@st.cache_data(ttl=300)
def discover_simulation_bundles(
    processed_dir: Path = MIROFISH_BUNDLES_DIR,
) -> list[dict[str, Any]]:
    """Discover portable MiroFish bundles and any Zep publish metadata."""

    bundles: list[dict[str, Any]] = []
    if not processed_dir.exists():
        return bundles

    for bundle_dir in sorted(processed_dir.iterdir()):
        if not bundle_dir.is_dir():
            continue
        bundle = load_simulation_bundle(bundle_dir)
        if bundle:
            bundles.append(bundle)

    bundles.sort(
        key=lambda bundle: (
            bundle.get("published_at", ""),
            bundle.get("simulation_id", ""),
        ),
        reverse=True,
    )
    return bundles
