"""Simulation Engine — tick-based loop that drives personas through a scenario.

The engine is the core orchestrator:
  1. Accepts a Scenario (from YAML) and optional Signals (from Crucix)
  2. Creates Persona instances from the scenario's PersonaConfig entries
  3. Runs a tick loop: build TickContext → each persona assesses → merge updates
  4. Collects all Assessments into a chronological timeline

Usage:
    scenario = load_scenario("scenarios/hormuz.yaml")
    engine = SimulationEngine(scenario)
    engine.inject_signals(signals_from_crucix)
    result = engine.run()
    # result.assessments = all persona outputs across all ticks
    # result.timeline = chronological list of events
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from super_agents.common.data_result import Signal

from .persona import Assessment, Persona, ReasoningFn, TickContext
from .scenario import PersonaConfig, Scenario

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Simulation result (immutable output)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TickResult:
    """Output of a single tick across all personas."""

    tick_number: int
    tick_time: datetime
    assessments: tuple[Assessment, ...]
    variables_before: dict[str, Any]
    variables_after: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick_number,
            "time": self.tick_time.isoformat(),
            "assessments": [a.to_dict() for a in self.assessments],
            "variables_before": dict(self.variables_before),
            "variables_after": dict(self.variables_after),
        }


@dataclass(frozen=True)
class SimulationResult:
    """Complete output of a simulation run."""

    scenario_name: str
    scenario_description: str
    tick_count: int
    tick_results: tuple[TickResult, ...]
    final_variables: dict[str, Any]
    hypotheses: tuple[str, ...]
    started_at: datetime
    completed_at: datetime
    signal_count: int = 0

    @property
    def all_assessments(self) -> list[Assessment]:
        """Flatten all assessments across all ticks."""
        return [a for tr in self.tick_results for a in tr.assessments]

    @property
    def all_alerts(self) -> list[dict[str, Any]]:
        """Extract all alerts with their tick context."""
        alerts: list[dict[str, Any]] = []
        for tr in self.tick_results:
            for assessment in tr.assessments:
                for alert_text in assessment.alerts:
                    alerts.append({
                        "tick": tr.tick_number,
                        "time": tr.tick_time.isoformat(),
                        "persona": assessment.persona_name,
                        "alert": alert_text,
                        "confidence": assessment.confidence,
                    })
        return alerts

    @property
    def all_predictions(self) -> list[dict[str, Any]]:
        """Extract all predictions with their tick context."""
        predictions: list[dict[str, Any]] = []
        for tr in self.tick_results:
            for assessment in tr.assessments:
                for pred in assessment.predictions:
                    predictions.append({
                        "tick": tr.tick_number,
                        "time": tr.tick_time.isoformat(),
                        "persona": assessment.persona_name,
                        "confidence": assessment.confidence,
                        **pred,
                    })
        return predictions

    @property
    def variable_history(self) -> list[dict[str, Any]]:
        """Track how variables changed across ticks."""
        return [
            {
                "tick": tr.tick_number,
                "time": tr.tick_time.isoformat(),
                "variables": dict(tr.variables_after),
            }
            for tr in self.tick_results
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario_name,
            "description": self.scenario_description,
            "tick_count": self.tick_count,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "signal_count": self.signal_count,
            "hypotheses": list(self.hypotheses),
            "final_variables": dict(self.final_variables),
            "ticks": [tr.to_dict() for tr in self.tick_results],
            "alerts": self.all_alerts,
            "predictions": self.all_predictions,
            "variable_history": self.variable_history,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SimulationEngine:
    """Tick-based simulation engine.

    Drives personas through a scenario one tick at a time, feeding each
    persona the current world state and collecting their assessments.

    Usage:
        engine = SimulationEngine(scenario)
        engine.inject_signals(crucix_signals)
        engine.register_rules("energy_analyst", [my_oil_rule, my_gas_rule])
        result = engine.run()
    """

    def __init__(self, scenario: Scenario) -> None:
        self._scenario = scenario
        self._signals: list[Signal] = []
        self._personas: dict[str, Persona] = {}
        self._custom_rules: dict[str, list[tuple[str, ReasoningFn]]] = {}

        # Initialize personas from scenario config
        for pc in scenario.personas:
            self._personas[pc.name] = Persona(pc)

    @property
    def scenario(self) -> Scenario:
        return self._scenario

    @property
    def persona_names(self) -> list[str]:
        return list(self._personas.keys())

    def inject_signals(self, signals: list[Signal]) -> None:
        """Add signals (e.g. from Crucix) to feed into the simulation.

        Signals are matched to ticks by timestamp during the run.
        """
        self._signals.extend(signals)
        logger.info("Injected %d signals (total: %d)", len(signals), len(self._signals))

    def register_rules(
        self,
        persona_name: str,
        rules: list[tuple[str, ReasoningFn]],
    ) -> None:
        """Register reasoning rules for a specific persona.

        Args:
            persona_name: Name of the persona (must match scenario config).
            rules: List of (rule_name, rule_fn) tuples.
        """
        persona = self._personas.get(persona_name)
        if not persona:
            available = ", ".join(self._personas.keys())
            raise ValueError(
                f"Persona '{persona_name}' not found. Available: {available}"
            )
        for rule_name, rule_fn in rules:
            persona.register_rule(rule_name, rule_fn)

    def set_llm_reasoning(self, persona_name: str, fn: ReasoningFn) -> None:
        """Set LLM-based reasoning for a persona (replaces rules)."""
        persona = self._personas.get(persona_name)
        if not persona:
            raise ValueError(f"Persona '{persona_name}' not found.")
        persona.set_llm_reasoning(fn)

    def run(self) -> SimulationResult:
        """Execute the full simulation.

        Returns:
            SimulationResult with all tick outputs and aggregated data.
        """
        started_at = datetime.now()
        tick_times = self._scenario.tick_times()
        variables = dict(self._scenario.variables)  # mutable copy for evolution
        tick_results: list[TickResult] = []
        previous_assessments: list[dict[str, Any]] = []

        logger.info(
            "Starting simulation '%s': %d ticks, %d personas, %d signals",
            self._scenario.name,
            len(tick_times),
            len(self._personas),
            len(self._signals),
        )

        for tick_num, tick_time in enumerate(tick_times):
            tick_result = self._run_tick(
                tick_number=tick_num,
                tick_time=tick_time,
                variables=variables,
                previous_assessments=tuple(previous_assessments),
            )
            tick_results.append(tick_result)

            # Evolve variables based on persona updates (immutable merge)
            variables = dict(tick_result.variables_after)

            # Carry forward assessments for context
            previous_assessments = [
                a.to_dict() for a in tick_result.assessments
            ]

            logger.info(
                "Tick %d/%d complete: %d assessments, %d alerts",
                tick_num + 1,
                len(tick_times),
                len(tick_result.assessments),
                sum(len(a.alerts) for a in tick_result.assessments),
            )

        completed_at = datetime.now()

        return SimulationResult(
            scenario_name=self._scenario.name,
            scenario_description=self._scenario.description,
            tick_count=len(tick_times),
            tick_results=tuple(tick_results),
            final_variables=dict(variables),
            hypotheses=tuple(h.question for h in self._scenario.hypotheses),
            started_at=started_at,
            completed_at=completed_at,
            signal_count=len(self._signals),
        )

    # -- Internal -----------------------------------------------------------

    def _run_tick(
        self,
        tick_number: int,
        tick_time: datetime,
        variables: dict[str, Any],
        previous_assessments: tuple[dict[str, Any], ...],
    ) -> TickResult:
        """Execute a single tick: all personas assess the current state."""
        variables_before = dict(variables)
        tick_signals = self._signals_for_tick(tick_number, tick_time)

        context = TickContext(
            tick_number=tick_number,
            tick_time=tick_time,
            variables=dict(variables),  # each persona sees a snapshot
            signals=tuple(tick_signals),
            previous_assessments=previous_assessments,
            scenario_name=self._scenario.name,
            scenario_description=self._scenario.description,
            hypotheses=tuple(h.question for h in self._scenario.hypotheses),
        )

        assessments: list[Assessment] = []
        merged_updates: dict[str, Any] = {}

        for persona_name, persona in self._personas.items():
            try:
                assessment = persona.assess(context)
                assessments.append(assessment)

                # Merge variable updates (last-write-wins per variable)
                merged_updates.update(assessment.variable_updates)
            except Exception as exc:
                logger.error(
                    "Persona '%s' failed on tick %d: %s",
                    persona_name, tick_number, exc,
                )
                assessments.append(Assessment(
                    persona_name=persona_name,
                    tick_number=tick_number,
                    tick_time=tick_time,
                    alerts=(f"Persona error: {exc}",),
                    confidence=0.0,
                    reasoning=f"Error during assessment: {exc}",
                ))

        # Apply merged updates to produce next state
        variables_after = {**variables, **merged_updates}

        return TickResult(
            tick_number=tick_number,
            tick_time=tick_time,
            assessments=tuple(assessments),
            variables_before=variables_before,
            variables_after=variables_after,
        )

    def _signals_for_tick(
        self,
        tick_number: int,
        tick_time: datetime,
    ) -> list[Signal]:
        """Select signals relevant to this tick's time window.

        Signals are assigned to the tick whose window they fall into.
        If no timestamps allow matching, all signals go to tick 0
        (useful for pre-loaded signal sets).
        """
        if not self._signals:
            return []

        tick_times = self._scenario.tick_times()
        tick_count = len(tick_times)

        if tick_count <= 1:
            # Single tick gets all signals
            return list(self._signals)

        # Determine this tick's time window
        tick_start = tick_time
        if tick_number < tick_count - 1:
            tick_end = tick_times[tick_number + 1]
        else:
            # Last tick: extend by one tick interval
            tick_end = tick_time + self._scenario.tick

        matching: list[Signal] = []
        unmatched_count = 0

        for signal in self._signals:
            sig_time = signal.timestamp
            if tick_start <= sig_time < tick_end:
                matching.append(signal)
            elif tick_number == 0 and sig_time < tick_start:
                # Pre-simulation signals go to first tick
                matching.append(signal)
                unmatched_count += 1

        if unmatched_count and tick_number == 0:
            logger.debug(
                "%d pre-simulation signals assigned to tick 0", unmatched_count
            )

        return matching
