"""Current-status writer per project.md section 12.

Writes a live status file during agent execution so the dashboard
can display what each agent is currently doing.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import DASHBOARDS_DIR, ensure_directory


def write_current_status(
    agent_name: str,
    run_id: str,
    workflow_name: str,
    task_name: str,
    status: str,
    input_scope: list[str] | None = None,
    active_source: str = "",
    progress_completed: int = 0,
    progress_total: int = 0,
    current_focus: str = "",
    latest_message: str = "",
    blocker: str | None = None,
) -> Path:
    """Write current-status JSON for the dashboard to consume.

    Returns:
        Path to the written status file.
    """
    ensure_directory(DASHBOARDS_DIR)

    status_data: dict[str, Any] = {
        "agent_name": agent_name,
        "run_id": run_id,
        "workflow_name": workflow_name,
        "task_name": task_name,
        "status": status,
        "started_at": datetime.now().isoformat(),
        "input_scope": input_scope or [],
        "active_source": active_source,
        "progress": {
            "completed": progress_completed,
            "total": progress_total,
        },
        "current_focus": current_focus,
        "latest_message": latest_message,
    }

    if blocker:
        status_data["blocker"] = blocker

    path = DASHBOARDS_DIR / f"{agent_name}_current_status.json"
    path.write_text(json.dumps(status_data, indent=2, default=str), encoding="utf-8")
    return path
