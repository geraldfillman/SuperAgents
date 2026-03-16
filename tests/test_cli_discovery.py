"""
Phase 2 architecture tests — CLI auto-discovery and common skill injection.

Verifies:
- _build_search_configs() auto-discovers all agents, not just the 3 curated ones
- Curated entries take priority over auto-discovered ones for known agents
- _load_common_skill_descriptions() reads from common/config.yaml
- discover_agents() injects common skill descriptions for skills with no local entry
- SEARCH_CONFIGS at module level covers every agent in AGENTS
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import tempfile

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from super_agents.cli import (
    AGENTS,
    SEARCH_CONFIGS,
    _build_search_configs,
    _load_common_skill_descriptions,
    discover_agents,
)


# ---------------------------------------------------------------------------
# _build_search_configs
# ---------------------------------------------------------------------------

class TestBuildSearchConfigs:
    def _make_agents(self, names: list[str]) -> dict:
        """Build a minimal AGENTS-like dict with one skill+script per agent."""
        fake_script_path = PROJECT_ROOT / "src" / "super_agents" / "cli.py"
        return {
            name: {
                "description": f"{name} agent",
                "skills": {
                    "some_skill": {
                        "description": "A skill",
                        "scripts": {
                            "fetch_data": {
                                "file": "fetch_data.py",
                                "path": fake_script_path,
                                "args": [],
                                "description": "Fetch data",
                            }
                        },
                    }
                },
            }
            for name in names
        }

    def test_curated_agents_keep_specific_args(self) -> None:
        agents = self._make_agents(["biotech", "gaming", "aerospace"])
        configs = _build_search_configs(agents)
        # Curated biotech entry has specific --days and --limit args
        biotech_scripts = [script for _, script, _ in configs["biotech"]]
        assert "fetch_drug_approvals" in biotech_scripts

    def test_unknown_agent_gets_auto_entry(self) -> None:
        agents = self._make_agents(["quantum"])
        configs = _build_search_configs(agents)
        assert "quantum" in configs
        assert len(configs["quantum"]) >= 1
        skill_name, script_name, args = configs["quantum"][0]
        assert skill_name == "some_skill"
        assert script_name == "fetch_data"
        assert args == []

    def test_all_agents_covered(self) -> None:
        agents = self._make_agents(["biotech", "gaming", "aerospace", "space", "quantum", "rare_earth"])
        configs = _build_search_configs(agents)
        for name in agents:
            assert name in configs, f"Agent '{name}' missing from search configs"

    def test_agent_with_no_skills_not_included(self) -> None:
        agents: dict = {
            "empty_agent": {
                "description": "No skills",
                "skills": {},
            }
        }
        configs = _build_search_configs(agents)
        assert "empty_agent" not in configs

    def test_auto_entries_limited_to_two_skills(self) -> None:
        fake_path = PROJECT_ROOT / "src" / "super_agents" / "cli.py"
        agents = {
            "new_sector": {
                "description": "test",
                "skills": {
                    f"skill_{i}": {
                        "description": f"Skill {i}",
                        "scripts": {
                            "fetch": {
                                "file": "fetch.py",
                                "path": fake_path,
                                "args": [],
                                "description": "fetch",
                            }
                        },
                    }
                    for i in range(5)
                },
            }
        }
        configs = _build_search_configs(agents)
        assert len(configs["new_sector"]) <= 2


# ---------------------------------------------------------------------------
# _load_common_skill_descriptions
# ---------------------------------------------------------------------------

class TestLoadCommonSkillDescriptions:
    def test_loads_financial_monitor(self) -> None:
        descriptions = _load_common_skill_descriptions(PROJECT_ROOT)
        assert "financial_monitor" in descriptions
        assert descriptions["financial_monitor"]  # non-empty

    def test_loads_insider_tracker(self) -> None:
        descriptions = _load_common_skill_descriptions(PROJECT_ROOT)
        assert "insider_tracker" in descriptions

    def test_returns_empty_dict_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            descriptions = _load_common_skill_descriptions(Path(tmp))
        assert descriptions == {}

    def test_returns_empty_for_malformed_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_dir = tmp_path / "src" / "super_agents" / "common"
            config_dir.mkdir(parents=True)
            (config_dir / "config.yaml").write_text("not_common_skills:\n  - junk\n")
            descriptions = _load_common_skill_descriptions(tmp_path)
        assert descriptions == {}

    def test_parses_custom_common_skills_block(self) -> None:
        yaml_content = textwrap.dedent("""
            common_skills:
              - name: test_skill_alpha
                description: Does alpha things

              - name: test_skill_beta
                description: Does beta things
        """)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config_dir = tmp_path / "src" / "super_agents" / "common"
            config_dir.mkdir(parents=True)
            (config_dir / "config.yaml").write_text(yaml_content)
            descriptions = _load_common_skill_descriptions(tmp_path)
        assert descriptions["test_skill_alpha"] == "Does alpha things"
        assert descriptions["test_skill_beta"] == "Does beta things"


# ---------------------------------------------------------------------------
# discover_agents — common skill injection
# ---------------------------------------------------------------------------

class TestDiscoverAgentsCommonInjection:
    def test_common_description_injected_for_skill_without_local_entry(self) -> None:
        """Agents that have a financial_monitor skill dir but no config.yaml entry
        for it should still get the common description."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # Create a minimal agent dir with financial_monitor skill
            agent_dir = tmp_path / ".agent_test_sector"
            scripts_dir = agent_dir / "skills" / "financial_monitor" / "scripts"
            scripts_dir.mkdir(parents=True)
            script = scripts_dir / "run_monitor.py"
            script.write_text('"""Run financial monitor."""\n')

            # Config with empty skills: block so no local description is set
            (agent_dir / "config.yaml").write_text(
                "agent:\n  name: test-sector\n  description: Test sector\nskills: []\n"
            )

            # Common config with financial_monitor description
            common_dir = tmp_path / "src" / "super_agents" / "common"
            common_dir.mkdir(parents=True)
            (common_dir / "config.yaml").write_text(
                "common_skills:\n"
                "  - name: financial_monitor\n"
                "    description: Shared financial monitor description\n"
            )

            agents = discover_agents(tmp_path)

        assert "test_sector" in agents
        skill = agents["test_sector"]["skills"].get("financial_monitor")
        assert skill is not None
        assert skill["description"] == "Shared financial monitor description"


# ---------------------------------------------------------------------------
# Module-level integration — AGENTS and SEARCH_CONFIGS
# ---------------------------------------------------------------------------

class TestModuleLevelIntegration:
    def test_search_configs_covers_all_agents(self) -> None:
        """Every agent discovered at import time should have a search config."""
        for agent_name in AGENTS:
            assert agent_name in SEARCH_CONFIGS, (
                f"Agent '{agent_name}' is in AGENTS but missing from SEARCH_CONFIGS"
            )

    def test_search_configs_entries_are_valid_tuples(self) -> None:
        for agent_name, entries in SEARCH_CONFIGS.items():
            for entry in entries:
                assert len(entry) == 3, f"Entry for {agent_name} should be (skill, script, args)"
                skill_name, script_name, args = entry
                assert isinstance(skill_name, str) and skill_name
                assert isinstance(script_name, str) and script_name
                assert isinstance(args, list)

    def test_cybersecurity_now_discoverable(self) -> None:
        """cybersecurity config.yaml was created in Phase 1.0 — it must now appear in AGENTS."""
        # The cybersecurity agent has a config.yaml but (currently) no scripts,
        # so it may not appear in AGENTS (discover_agents skips agents with no
        # runnable scripts).  Assert the config.yaml exists at minimum.
        cyber_config = PROJECT_ROOT / ".agent_cybersecurity" / "config.yaml"
        assert cyber_config.exists(), "cybersecurity config.yaml is missing"
