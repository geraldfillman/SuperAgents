"""Scenario definition and YAML parser.

A scenario defines:
  - Name and description
  - Personas (agent roles that will reason about the scenario)
  - Variables (initial conditions that can change per tick)
  - Duration and tick interval
  - Data feeds (which Crucix sources to inject)
  - Hypotheses (what we're trying to predict)

Example YAML:
  scenario:
    name: hormuz_zero_transit
    description: Strait of Hormuz commercial crossings fall to zero
    personas:
      - name: energy_analyst
        role: Senior energy market analyst
        perspective: Track oil supply disruption and price impact
      - name: logistics_officer
        role: Global shipping logistics coordinator
        perspective: Model route diversions and container rate changes
    variables:
      oil_price: 95
      strait_status: closed
      coalition_response: failed
      cape_route_capacity_pct: 40
    duration: 7d
    tick: 1d
    data_feeds:
      - crucix.energy
      - crucix.maritime
    hypotheses:
      - When does Cape of Good Hope become the global standard route?
      - What is the peak TEU spot rate for EU-Asia?
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from super_agents.common.io_utils import read_json

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

def _parse_duration(value: str) -> timedelta:
    """Parse a human-friendly duration string into a timedelta.

    Supports: 1d, 7d, 2w, 1h, 30m, etc.
    """
    value = value.strip().lower()
    if value.endswith("d"):
        return timedelta(days=int(value[:-1]))
    if value.endswith("w"):
        return timedelta(weeks=int(value[:-1]))
    if value.endswith("h"):
        return timedelta(hours=int(value[:-1]))
    if value.endswith("m"):
        return timedelta(minutes=int(value[:-1]))
    # Default: treat as days
    try:
        return timedelta(days=int(value))
    except ValueError:
        raise ValueError(f"Cannot parse duration: '{value}'. Use format like '7d', '2w', '1h'.")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PersonaConfig:
    """Configuration for a simulation persona."""

    name: str
    role: str
    perspective: str
    sector: str = ""
    expertise: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PersonaConfig:
        expertise = data.get("expertise", [])
        return cls(
            name=data["name"],
            role=data.get("role", data["name"]),
            perspective=data.get("perspective", ""),
            sector=data.get("sector", ""),
            expertise=tuple(expertise) if isinstance(expertise, list) else (expertise,),
        )


@dataclass(frozen=True)
class Hypothesis:
    """A question the simulation is trying to answer."""

    question: str
    metric: str = ""
    unit: str = ""

    @classmethod
    def from_value(cls, value: Any) -> Hypothesis:
        if isinstance(value, str):
            return cls(question=value)
        if isinstance(value, dict):
            return cls(
                question=value.get("question", ""),
                metric=value.get("metric", ""),
                unit=value.get("unit", ""),
            )
        return cls(question=str(value))


@dataclass(frozen=True)
class Scenario:
    """A complete simulation scenario definition."""

    name: str
    description: str
    personas: tuple[PersonaConfig, ...]
    variables: dict[str, Any]
    duration: timedelta
    tick: timedelta
    data_feeds: tuple[str, ...]
    hypotheses: tuple[Hypothesis, ...]
    start_time: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def tick_count(self) -> int:
        """Total number of ticks in the simulation."""
        if self.tick.total_seconds() == 0:
            return 1
        return max(1, int(self.duration.total_seconds() / self.tick.total_seconds()))

    @property
    def persona_names(self) -> list[str]:
        return [p.name for p in self.personas]

    def tick_times(self) -> list[datetime]:
        """Generate the datetime for each tick."""
        return [self.start_time + self.tick * i for i in range(self.tick_count)]

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON output."""
        return {
            "name": self.name,
            "description": self.description,
            "personas": [
                {"name": p.name, "role": p.role, "perspective": p.perspective}
                for p in self.personas
            ],
            "variables": dict(self.variables),
            "duration": str(self.duration),
            "tick": str(self.tick),
            "tick_count": self.tick_count,
            "data_feeds": list(self.data_feeds),
            "hypotheses": [
                {"question": h.question, "metric": h.metric, "unit": h.unit}
                for h in self.hypotheses
            ],
            "start_time": self.start_time.isoformat(),
        }


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_scenario(path: Path | str) -> Scenario:
    """Load a scenario from a YAML file.

    Args:
        path: Path to the scenario YAML file.

    Returns:
        A Scenario object ready for execution.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    # Support both top-level and nested under 'scenario' key
    data = raw.get("scenario", raw)

    personas = tuple(
        PersonaConfig.from_dict(p) for p in data.get("personas", [])
    )

    hypotheses = tuple(
        Hypothesis.from_value(h) for h in data.get("hypotheses", [])
    )

    variables = data.get("variables", {})
    if not isinstance(variables, dict):
        variables = {}

    data_feeds = data.get("data_feeds", [])
    if isinstance(data_feeds, str):
        data_feeds = [data_feeds]

    return Scenario(
        name=data.get("name", path.stem),
        description=data.get("description", ""),
        personas=personas,
        variables=variables,
        duration=_parse_duration(data.get("duration", "7d")),
        tick=_parse_duration(data.get("tick", "1d")),
        data_feeds=tuple(data_feeds),
        hypotheses=hypotheses,
        start_time=datetime.now(),
        metadata=data.get("metadata", {}),
    )


def scenario_from_dict(data: dict[str, Any]) -> Scenario:
    """Create a Scenario from an in-memory dict (for programmatic use)."""
    sc = data.get("scenario", data)

    personas = tuple(PersonaConfig.from_dict(p) for p in sc.get("personas", []))
    hypotheses = tuple(Hypothesis.from_value(h) for h in sc.get("hypotheses", []))

    data_feeds = sc.get("data_feeds", [])
    if isinstance(data_feeds, str):
        data_feeds = [data_feeds]

    return Scenario(
        name=sc.get("name", "unnamed"),
        description=sc.get("description", ""),
        personas=personas,
        variables=sc.get("variables", {}),
        duration=_parse_duration(sc.get("duration", "7d")),
        tick=_parse_duration(sc.get("tick", "1d")),
        data_feeds=tuple(data_feeds),
        hypotheses=hypotheses,
        start_time=datetime.now(),
        metadata=sc.get("metadata", {}),
    )
