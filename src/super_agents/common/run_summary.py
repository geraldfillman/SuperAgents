"""Standardized run summary writer per project.md sections 9-10.

Every task run writes both machine-readable JSON and analyst-readable
Markdown output.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .paths import DASHBOARDS_DIR, ensure_directory


def write_run_summary(
    agent_name: str,
    run_id: str,
    workflow_name: str,
    task_name: str,
    status: str,
    started_at: datetime,
    completed_at: datetime | None = None,
    inputs: dict[str, int] | None = None,
    outputs: dict[str, int] | None = None,
    findings: list[dict[str, Any]] | None = None,
    blockers: list[str] | None = None,
    next_actions: list[str] | None = None,
) -> tuple[Path, Path]:
    """Write JSON and Markdown run summaries.

    Returns:
        Tuple of (json_path, markdown_path).
    """
    completed_at = completed_at or datetime.now()
    duration = (completed_at - started_at).total_seconds()

    summary = {
        "agent_name": agent_name,
        "run_id": run_id,
        "workflow_name": workflow_name,
        "task_name": task_name,
        "status": status,
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round(duration, 1),
        "inputs": inputs or {},
        "outputs": outputs or {},
        "findings": findings or [],
        "blockers": blockers or [],
        "next_actions": next_actions or [],
    }

    # Write to timestamped directory
    run_dir = ensure_directory(DASHBOARDS_DIR / "runs" / agent_name / run_id)
    json_path = run_dir / "summary.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    md_path = run_dir / "summary.md"
    md_path.write_text(_build_markdown(summary), encoding="utf-8")

    # Copy to "latest" shortcuts
    latest_json = DASHBOARDS_DIR / f"{agent_name}_run_latest.json"
    latest_json.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")

    latest_md = DASHBOARDS_DIR / f"{agent_name}_run_latest.md"
    latest_md.write_text(_build_markdown(summary), encoding="utf-8")

    return json_path, md_path


def _build_markdown(summary: dict) -> str:
    """Build Markdown run summary per project.md template."""
    lines = [
        "# Run Summary",
        "",
        "## What Ran",
        f"- **Workflow**: {summary['workflow_name']}",
        f"- **Task**: {summary['task_name']}",
        f"- **Agent**: {summary['agent_name']}",
        f"- **Start**: {summary['started_at']}",
        f"- **End**: {summary['completed_at']}",
        f"- **Duration**: {summary['duration_seconds']}s",
        "",
        "## What Changed",
    ]

    inputs = summary.get("inputs", {})
    for key, val in inputs.items():
        lines.append(f"- Input {key}: {val}")

    outputs = summary.get("outputs", {})
    for key, val in outputs.items():
        lines.append(f"- {key}: {val}")

    lines.extend(["", "## Findings"])
    for finding in summary.get("findings", []):
        severity = finding.get("severity", "info")
        text = finding.get("summary", str(finding))
        lines.append(f"- [{severity}] {text}")
    if not summary.get("findings"):
        lines.append("- None")

    lines.extend(["", "## Blockers"])
    for blocker in summary.get("blockers", []):
        lines.append(f"- {blocker}")
    if not summary.get("blockers"):
        lines.append("- None")

    lines.extend(["", "## Next Actions"])
    for action in summary.get("next_actions", []):
        lines.append(f"- {action}")
    if not summary.get("next_actions"):
        lines.append("- None")

    return "\n".join(lines) + "\n"
