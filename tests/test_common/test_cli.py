"""Tests for CLI agent discovery and registration."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

from super_agents import cli

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _script_backed_agents() -> set[str]:
    return {
        agent_dir.name[len(".agent_") :]
        for agent_dir in PROJECT_ROOT.glob(".agent_*")
        if any(agent_dir.glob("skills/*/scripts/*.py"))
    }


def test_discover_agents_matches_script_backed_directories():
    assert set(cli.AGENTS) == _script_backed_agents()


def test_discovery_reconciles_existing_registry_drift():
    assert "conference_scraper" in cli.AGENTS["biotech"]["skills"]
    assert "scrape_abstracts" in cli.AGENTS["biotech"]["skills"]["conference_scraper"]["scripts"]
    assert "rare_earth" in cli.AGENTS
    assert "financial_monitor" not in cli.AGENTS["gaming"]["skills"]
    assert "simulation" in cli.AGENTS
    assert "mirofish_runtime" in cli.AGENTS["simulation"]["skills"]


def test_list_command_supports_new_agent(capsys: pytest.CaptureFixture[str]):
    exit_code = cli.cmd_list(argparse.Namespace(agent="rare_earth"))
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "RARE EARTH" in captured.out
    assert "permit_tracker" in captured.out
    assert "fetch_permits" in captured.out


@pytest.mark.parametrize(
    ("agent", "skill", "script"),
    [
        ("renewable_energy", "calendar", "build_calendar"),
        ("rare_earth", "data_quality", "audit_stale_records"),
        ("simulation", "mirofish_runtime", "probe_runtime"),
    ],
)
def test_cmd_run_help_smoke(agent: str, skill: str, script: str):
    exit_code = cli.cmd_run(
        argparse.Namespace(agent=agent, skill=skill, script=script, extra=["--", "--help"])
    )
    assert exit_code == 0


def test_python_module_entrypoint_from_repo_root():
    result = subprocess.run(
        [sys.executable, "-m", "super_agents", "list", "--agent", "rare_earth"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "permit_tracker" in result.stdout
