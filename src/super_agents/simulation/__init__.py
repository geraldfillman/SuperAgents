"""Simulation Engine - scenario-based what-if analysis.

Runs structured scenarios with agent personas, real-world signals from
Crucix, and tick-based progression to produce prediction timelines.

Four layers:
  1. Scenario: YAML-defined setup (actors, variables, duration, data feeds)
  2. Persona: Agent roles that reason about each tick from their perspective
  3. Engine: Tick loop that feeds signals + context to personas, merges outputs
  4. Timeline: Chronological output of predictions, pivots, and confidence scores
"""

from .scenario import Scenario, load_scenario, scenario_from_dict
from .persona import (
    Assessment,
    Persona,
    TickContext,
    threshold_rule,
    signal_watcher_rule,
)
from .engine import SimulationEngine, SimulationResult, TickResult
from .timeline import write_json, write_markdown, build_summary

__all__ = [
    "Scenario",
    "load_scenario",
    "scenario_from_dict",
    "Assessment",
    "Persona",
    "TickContext",
    "threshold_rule",
    "signal_watcher_rule",
    "SimulationEngine",
    "SimulationResult",
    "TickResult",
    "write_json",
    "write_markdown",
    "build_summary",
]
