"""Runtime AgentRegistry — programmatic access to all discovered agents.

The CLI (cli.py) already has discover_agents() that scans .agent_* dirs.
This module wraps that into a proper class so other Python code can:

  - Query agents by name or sector
  - Find agents that have a specific skill
  - Route signals to matching agents
  - Enumerate all available skills across the fleet

Usage:
    from super_agents.common.registry import AgentRegistry

    registry = AgentRegistry()
    biotech = registry.get_agent("biotech")
    sec_agents = registry.agents_with_skill("sec_filings_parser")
    all_skills = registry.all_skills()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .paths import PROJECT_ROOT

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes — immutable views of agent/skill/script metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScriptInfo:
    """Metadata for a single runnable script."""

    name: str
    path: Path
    description: str
    args: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillInfo:
    """Metadata for a skill (collection of scripts)."""

    name: str
    description: str
    scripts: tuple[ScriptInfo, ...] = ()

    def get_script(self, name: str) -> ScriptInfo | None:
        """Find a script by name."""
        for script in self.scripts:
            if script.name == name:
                return script
        return None

    @property
    def script_names(self) -> list[str]:
        return [s.name for s in self.scripts]


@dataclass(frozen=True)
class AgentInfo:
    """Metadata for a sector agent."""

    name: str
    description: str
    config_dir: Path
    skills: tuple[SkillInfo, ...] = ()
    sectors: tuple[str, ...] = ()

    def get_skill(self, name: str) -> SkillInfo | None:
        """Find a skill by name."""
        for skill in self.skills:
            if skill.name == name:
                return skill
        return None

    def has_skill(self, name: str) -> bool:
        return any(s.name == name for s in self.skills)

    @property
    def skill_names(self) -> list[str]:
        return [s.name for s in self.skills]

    @property
    def total_scripts(self) -> int:
        return sum(len(s.scripts) for s in self.skills)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class AgentRegistry:
    """Discovers and indexes all agents from .agent_* directories.

    Instantiate once at app startup. The registry is immutable after construction.
    """

    def __init__(self, project_root: Path = PROJECT_ROOT) -> None:
        self._project_root = project_root
        self._agents: dict[str, AgentInfo] = {}
        self._discover()

    # -- Public API ---------------------------------------------------------

    @property
    def agent_names(self) -> list[str]:
        """All discovered agent names, sorted."""
        return sorted(self._agents.keys())

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    def get_agent(self, name: str) -> AgentInfo | None:
        """Look up an agent by name."""
        return self._agents.get(name)

    def agents_with_skill(self, skill_name: str) -> list[AgentInfo]:
        """Find all agents that have a given skill."""
        return [a for a in self._agents.values() if a.has_skill(skill_name)]

    def agents_for_sector(self, sector: str) -> list[AgentInfo]:
        """Find agents tagged with a sector label."""
        sector_lower = sector.lower()
        return [
            a for a in self._agents.values()
            if sector_lower in (s.lower() for s in a.sectors) or sector_lower == a.name
        ]

    def all_skills(self) -> list[tuple[str, SkillInfo]]:
        """Return (agent_name, skill) pairs across all agents."""
        pairs: list[tuple[str, SkillInfo]] = []
        for agent in self._agents.values():
            for skill in agent.skills:
                pairs.append((agent.name, skill))
        return pairs

    def all_scripts(self) -> list[tuple[str, str, ScriptInfo]]:
        """Return (agent_name, skill_name, script) triples."""
        triples: list[tuple[str, str, ScriptInfo]] = []
        for agent in self._agents.values():
            for skill in agent.skills:
                for script in skill.scripts:
                    triples.append((agent.name, skill.name, script))
        return triples

    def summary(self) -> dict[str, Any]:
        """Return a summary dict of the entire fleet."""
        return {
            "agent_count": self.agent_count,
            "total_skills": sum(len(a.skills) for a in self._agents.values()),
            "total_scripts": sum(a.total_scripts for a in self._agents.values()),
            "agents": {
                name: {
                    "description": agent.description,
                    "skills": agent.skill_names,
                    "script_count": agent.total_scripts,
                }
                for name, agent in sorted(self._agents.items())
            },
        }

    # -- Discovery ----------------------------------------------------------

    def _discover(self) -> None:
        """Scan .agent_* directories and build the registry."""
        for agent_dir in sorted(self._project_root.glob(".agent_*")):
            skills_root = agent_dir / "skills"
            if not skills_root.is_dir():
                continue

            agent_name = agent_dir.name[len(".agent_"):]
            config = self._load_config(agent_dir / "config.yaml")

            agent_description = (
                config.get("agent", {}).get("description", "")
                or self._humanize(agent_name)
            )

            sectors = tuple(config.get("agent", {}).get("sectors", [agent_name]))

            skills: list[SkillInfo] = []
            for skill_dir in sorted(skills_root.iterdir()):
                if not skill_dir.is_dir():
                    continue
                scripts_dir = skill_dir / "scripts"
                if not scripts_dir.is_dir():
                    continue

                scripts: list[ScriptInfo] = []
                for script_path in sorted(scripts_dir.glob("*.py")):
                    scripts.append(ScriptInfo(
                        name=script_path.stem,
                        path=script_path,
                        description=self._humanize(script_path.stem),
                    ))

                if not scripts:
                    continue

                skills.append(SkillInfo(
                    name=skill_dir.name,
                    description=self._humanize(skill_dir.name),
                    scripts=tuple(scripts),
                ))

            if not skills:
                continue

            self._agents[agent_name] = AgentInfo(
                name=agent_name,
                description=agent_description,
                config_dir=agent_dir,
                skills=tuple(skills),
                sectors=sectors,
            )

        logger.info(
            "AgentRegistry: discovered %d agents with %d total skills",
            self.agent_count,
            sum(len(a.skills) for a in self._agents.values()),
        )

    @staticmethod
    def _load_config(config_path: Path) -> dict[str, Any]:
        """Load a YAML config, returning empty dict on failure."""
        if not config_path.exists():
            return {}
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _humanize(name: str) -> str:
        return name.replace("_", " ").replace("-", " ").strip().title()
