"""Tests for shared dashboard artifact writers."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from super_agents.common import run_summary as run_summary_module
from super_agents.common import status as status_module


def _workspace_temp_dir(label: str) -> Path:
    root = Path("tests") / ".tmp_artifacts" / label
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_write_current_status_writes_expected_shape(monkeypatch):
    dashboards_dir = _workspace_temp_dir("status_writer") / "dashboards"
    monkeypatch.setattr(status_module, "DASHBOARDS_DIR", dashboards_dir)

    path = status_module.write_current_status(
        agent_name="renewable_energy",
        run_id="20260315_130000",
        workflow_name="calendar",
        task_name="build_calendar",
        status="running",
        input_scope=["window:180d"],
        active_source="data/processed/renewable_energy",
        progress_completed=1,
        progress_total=4,
        current_focus="Building calendar",
        latest_message="Loaded interconnection events",
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert path == dashboards_dir / "renewable_energy_current_status.json"
    assert payload["agent_name"] == "renewable_energy"
    assert payload["status"] == "running"
    assert payload["progress"] == {"completed": 1, "total": 4}
    assert payload["input_scope"] == ["window:180d"]


def test_write_run_summary_writes_latest_and_history_files(monkeypatch):
    dashboards_dir = _workspace_temp_dir("run_summary_writer") / "dashboards"
    monkeypatch.setattr(run_summary_module, "DASHBOARDS_DIR", dashboards_dir)

    started_at = datetime(2026, 3, 15, 13, 0, 0)
    completed_at = started_at + timedelta(seconds=30)
    json_path, md_path = run_summary_module.write_run_summary(
        agent_name="renewable_energy",
        run_id="20260315_130000",
        workflow_name="calendar",
        task_name="build_calendar",
        status="completed",
        started_at=started_at,
        completed_at=completed_at,
        inputs={"window_days": 180},
        outputs={"records_written": 2},
        findings=[
            {
                "severity": "info",
                "summary": "cod for Example Solar on 2026-04-01",
            }
        ],
        next_actions=["Review upcoming events"],
    )

    latest_json = dashboards_dir / "renewable_energy_run_latest.json"
    latest_md = dashboards_dir / "renewable_energy_run_latest.md"

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert json_path.exists()
    assert md_path.exists()
    assert latest_json.exists()
    assert latest_md.exists()
    assert payload["status"] == "completed"
    assert payload["duration_seconds"] == 30.0
    assert payload["outputs"]["records_written"] == 2
    assert payload["findings"][0]["summary"] == "cod for Example Solar on 2026-04-01"
