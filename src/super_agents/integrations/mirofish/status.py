"""Status and IPC helpers for prepared MiroFish bundles."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def read_runtime_status(bundle_dir: Path | str) -> dict[str, Any]:
    """Summarize the state of a prepared or running MiroFish bundle."""

    root = Path(bundle_dir)
    config = _read_json_if_present(root / "simulation_config.json") or {}
    run_state = _read_json_if_present(root / "run_state.json")
    env_status = _read_json_if_present(root / "env_status.json")

    return {
        "bundle_dir": str(root.resolve()),
        "simulation_id": config.get("simulation_id"),
        "project_id": config.get("project_id"),
        "graph_id": config.get("graph_id"),
        "agent_count": len(config.get("agent_configs", [])),
        "run_state": run_state,
        "env_status": env_status,
        "has_runtime_log": (root / "mirofish_runtime.log").exists(),
        "has_simulation_log": (root / "simulation.log").exists(),
        "has_twitter_db": (root / "twitter_simulation.db").exists(),
        "has_reddit_db": (root / "reddit_simulation.db").exists(),
        "has_twitter_actions": (root / "twitter" / "actions.jsonl").exists(),
        "has_reddit_actions": (root / "reddit" / "actions.jsonl").exists(),
    }


def send_close_command(bundle_dir: Path | str, timeout: float = 30.0) -> dict[str, Any]:
    """Write a MiroFish IPC close-env command file into the bundle."""

    root = Path(bundle_dir)
    commands_dir = root / "ipc_commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    command_id = str(uuid.uuid4())
    command = {
        "command_id": command_id,
        "command_type": "close_env",
        "args": {},
        "timestamp": datetime.now().isoformat(),
        "requested_timeout": timeout,
    }
    command_path = commands_dir / f"{command_id}.json"
    command_path.write_text(json.dumps(command, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "command_id": command_id,
        "command_path": str(command_path),
        "bundle_dir": str(root.resolve()),
    }
