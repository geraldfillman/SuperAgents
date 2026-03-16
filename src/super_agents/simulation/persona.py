"""Simulation Personas - agent roles that reason about each tick.

A persona represents a specific perspective in the simulation:
  - "Energy Analyst" tracks oil prices and supply disruptions
  - "Logistics Officer" models shipping routes and container rates
  - "Bond Trader" watches yield curves and central bank signals

Each persona:
  1. Receives the current tick's context (variables, signals, history)
  2. Produces an assessment (observations, predictions, confidence)
  3. Optionally modifies variables for the next tick

v1: Rule-based reasoning with structured output
v2 (future): LLM-powered reasoning per persona
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from super_agents.common.data_result import Signal
from .scenario import PersonaConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tick context - what each persona sees
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TickContext:
    """The world state at a single simulation tick."""

    tick_number: int
    tick_time: datetime
    variables: dict[str, Any]
    signals: tuple[Signal, ...] = ()
    previous_assessments: tuple[dict[str, Any], ...] = ()
    scenario_name: str = ""
    scenario_description: str = ""
    hypotheses: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Assessment - what each persona produces
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Assessment:
    """A persona's output for a single tick."""

    persona_name: str
    tick_number: int
    tick_time: datetime
    observations: tuple[str, ...] = ()
    predictions: tuple[dict[str, Any], ...] = ()
    variable_updates: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5  # 0.0 to 1.0
    reasoning: str = ""
    alerts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona": self.persona_name,
            "tick": self.tick_number,
            "time": self.tick_time.isoformat(),
            "observations": list(self.observations),
            "predictions": list(self.predictions),
            "variable_updates": dict(self.variable_updates),
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alerts": list(self.alerts),
        }


# ---------------------------------------------------------------------------
# Persona
# ---------------------------------------------------------------------------

# Type for custom reasoning functions
ReasoningFn = Callable[[PersonaConfig, TickContext], Assessment]


class Persona:
    """A simulation actor that reasons about each tick.

    Can operate in two modes:
      1. Rule-based: Uses registered reasoning functions
      2. LLM-based: Sends tick context to an LLM for reasoning (future)

    Usage:
        persona = Persona(config)
        persona.register_rule("oil_price_threshold", my_rule_fn)
        assessment = persona.assess(tick_context)
    """

    def __init__(self, config: PersonaConfig) -> None:
        self._config = config
        self._rules: list[tuple[str, ReasoningFn]] = []
        self._llm_fn: ReasoningFn | None = None

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def config(self) -> PersonaConfig:
        return self._config

    def register_rule(self, name: str, fn: ReasoningFn) -> None:
        """Register a rule-based reasoning function."""
        self._rules.append((name, fn))

    def set_llm_reasoning(self, fn: ReasoningFn) -> None:
        """Set an LLM-based reasoning function (replaces rule-based)."""
        self._llm_fn = fn

    def assess(self, context: TickContext) -> Assessment:
        """Produce an assessment for the current tick.

        If an LLM function is set, uses that. Otherwise aggregates rule-based
        assessments.
        """
        if self._llm_fn:
            return self._llm_fn(self._config, context)

        if self._rules:
            return self._aggregate_rules(context)

        # Default: basic assessment from context
        return self._default_assessment(context)

    def _aggregate_rules(self, context: TickContext) -> Assessment:
        """Run all registered rules and merge their outputs."""
        all_observations: list[str] = []
        all_predictions: list[dict[str, Any]] = []
        all_updates: dict[str, Any] = {}
        all_alerts: list[str] = []
        confidences: list[float] = []
        reasonings: list[str] = []

        for rule_name, rule_fn in self._rules:
            try:
                result = rule_fn(self._config, context)
                all_observations.extend(result.observations)
                all_predictions.extend(result.predictions)
                all_updates.update(result.variable_updates)
                all_alerts.extend(result.alerts)
                confidences.append(result.confidence)
                if result.reasoning:
                    reasonings.append(f"[{rule_name}] {result.reasoning}")
            except Exception as exc:
                logger.warning("Rule '%s' failed for %s: %s", rule_name, self.name, exc)
                all_alerts.append(f"Rule '{rule_name}' failed: {exc}")

        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        return Assessment(
            persona_name=self.name,
            tick_number=context.tick_number,
            tick_time=context.tick_time,
            observations=tuple(all_observations),
            predictions=tuple(all_predictions),
            variable_updates=all_updates,
            confidence=round(avg_confidence, 3),
            reasoning="; ".join(reasonings),
            alerts=tuple(all_alerts),
        )

    def _default_assessment(self, context: TickContext) -> Assessment:
        """Generate a basic assessment by scanning signals for relevance."""
        observations: list[str] = []
        predictions: list[dict[str, Any]] = []
        alerts: list[str] = []

        # Scan signals for anything related to this persona's sector/expertise
        sector = self._config.sector
        for signal in context.signals:
            if signal.matches_sector(sector) or not signal.sectors:
                severity = signal.payload.get("severity", "")
                if severity in ("critical", "high"):
                    alerts.append(f"{signal.topic}: {signal.payload.get('label', '')}")
                else:
                    observations.append(f"[{signal.source}] {signal.topic}")

        # Note variable states
        for var_name, var_value in context.variables.items():
            observations.append(f"{var_name} = {var_value}")

        return Assessment(
            persona_name=self.name,
            tick_number=context.tick_number,
            tick_time=context.tick_time,
            observations=tuple(observations[:20]),
            predictions=tuple(predictions),
            confidence=0.5,
            reasoning=f"Default assessment for {self.name} ({self._config.role})",
            alerts=tuple(alerts),
        )


# ---------------------------------------------------------------------------
# Built-in reasoning rules (reusable across simulations)
# ---------------------------------------------------------------------------

def threshold_rule(
    variable: str,
    threshold: float,
    direction: str = "above",
    prediction_text: str = "",
    alert_text: str = "",
) -> ReasoningFn:
    """Factory: create a rule that fires when a variable crosses a threshold.

    Args:
        variable: Variable name to watch.
        threshold: The threshold value.
        direction: "above" or "below".
        prediction_text: Text to emit as a prediction when triggered.
        alert_text: Text to emit as an alert when triggered.
    """
    def rule(config: PersonaConfig, context: TickContext) -> Assessment:
        value = context.variables.get(variable)
        predictions: list[dict[str, Any]] = []
        alerts: list[str] = []
        observations: list[str] = []

        if value is not None:
            triggered = (
                (direction == "above" and float(value) > threshold)
                or (direction == "below" and float(value) < threshold)
            )

            observations.append(f"{variable} = {value} (threshold: {direction} {threshold})")

            if triggered:
                if prediction_text:
                    predictions.append({
                        "text": prediction_text,
                        "variable": variable,
                        "value": value,
                        "threshold": threshold,
                    })
                if alert_text:
                    alerts.append(alert_text)

        return Assessment(
            persona_name=config.name,
            tick_number=context.tick_number,
            tick_time=context.tick_time,
            observations=tuple(observations),
            predictions=tuple(predictions),
            confidence=0.7 if predictions else 0.5,
            alerts=tuple(alerts),
        )

    return rule


def signal_watcher_rule(
    topic_pattern: str,
    prediction_text: str = "",
) -> ReasoningFn:
    """Factory: create a rule that watches for signals matching a topic pattern."""
    def rule(config: PersonaConfig, context: TickContext) -> Assessment:
        matching = [s for s in context.signals if topic_pattern in s.topic]
        observations = [f"Signal: {s.topic} from {s.source}" for s in matching[:10]]
        predictions: list[dict[str, Any]] = []

        if matching and prediction_text:
            predictions.append({
                "text": prediction_text,
                "triggered_by": [s.topic for s in matching[:5]],
                "signal_count": len(matching),
            })

        return Assessment(
            persona_name=config.name,
            tick_number=context.tick_number,
            tick_time=context.tick_time,
            observations=tuple(observations),
            predictions=tuple(predictions),
            confidence=min(0.9, 0.5 + len(matching) * 0.1),
        )

    return rule
