"""Timeline — format simulation results for human and machine consumption.

Converts a SimulationResult into:
  1. JSON (full structured output for programmatic use)
  2. Markdown (human-readable narrative with tick-by-tick progression)
  3. Summary dict (compact overview for CLI display)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .engine import SimulationResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def write_json(result: SimulationResult, path: Path) -> Path:
    """Write full simulation result as JSON.

    Args:
        result: The simulation output.
        path: Destination file path.

    Returns:
        The path written to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_dict(), indent=2, default=str),
        encoding="utf-8",
    )
    logger.info("Simulation JSON written to %s", path)
    return path


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def write_markdown(result: SimulationResult, path: Path) -> Path:
    """Write a human-readable Markdown narrative of the simulation.

    Args:
        result: The simulation output.
        path: Destination file path.

    Returns:
        The path written to.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"# Simulation: {result.scenario_name}")
    lines.append("")
    lines.append(f"> {result.scenario_description}")
    lines.append("")
    lines.append(f"**Ticks:** {result.tick_count} | "
                 f"**Signals:** {result.signal_count} | "
                 f"**Run time:** {result.started_at:%H:%M:%S} - {result.completed_at:%H:%M:%S}")
    lines.append("")

    # Hypotheses
    if result.hypotheses:
        lines.append("## Hypotheses")
        lines.append("")
        for h in result.hypotheses:
            lines.append(f"- {h}")
        lines.append("")

    # Tick-by-tick narrative
    lines.append("## Timeline")
    lines.append("")

    for tr in result.tick_results:
        lines.append(f"### Tick {tr.tick_number} - {tr.tick_time:%Y-%m-%d %H:%M}")
        lines.append("")

        # Variable changes
        changed = _variable_diff(tr.variables_before, tr.variables_after)
        if changed:
            lines.append("**Variable changes:**")
            for var_name, (old_val, new_val) in changed.items():
                lines.append(f"- `{var_name}`: {old_val} -> {new_val}")
            lines.append("")

        # Per-persona assessments
        for assessment in tr.assessments:
            lines.append(f"#### {assessment.persona_name} (confidence: {assessment.confidence:.1%})")
            lines.append("")

            if assessment.observations:
                for obs in assessment.observations[:10]:
                    lines.append(f"- {obs}")
                lines.append("")

            if assessment.predictions:
                lines.append("**Predictions:**")
                for pred in assessment.predictions:
                    text = pred.get("text", str(pred))
                    lines.append(f"- {text}")
                lines.append("")

            if assessment.alerts:
                lines.append("**ALERTS:**")
                for alert in assessment.alerts:
                    lines.append(f"- {alert}")
                lines.append("")

            if assessment.reasoning:
                lines.append(f"*{assessment.reasoning}*")
                lines.append("")

    # Final state
    lines.append("## Final State")
    lines.append("")
    lines.append("| Variable | Value |")
    lines.append("|----------|-------|")
    for var_name, var_value in sorted(result.final_variables.items()):
        lines.append(f"| `{var_name}` | {var_value} |")
    lines.append("")

    # Alerts summary
    alerts = result.all_alerts
    if alerts:
        lines.append(f"## Alerts ({len(alerts)} total)")
        lines.append("")
        for alert in alerts:
            lines.append(
                f"- **Tick {alert['tick']}** [{alert['persona']}]: {alert['alert']}"
            )
        lines.append("")

    # Predictions summary
    predictions = result.all_predictions
    if predictions:
        lines.append(f"## Predictions ({len(predictions)} total)")
        lines.append("")
        for pred in predictions:
            text = pred.get("text", "")
            lines.append(
                f"- **Tick {pred['tick']}** [{pred['persona']}] "
                f"(conf: {pred['confidence']:.0%}): {text}"
            )
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Simulation Markdown written to %s", path)
    return path


# ---------------------------------------------------------------------------
# Summary (for CLI display)
# ---------------------------------------------------------------------------

def build_summary(result: SimulationResult) -> dict[str, Any]:
    """Build a compact summary dict suitable for CLI display.

    Returns:
        Dict with key stats, top alerts, top predictions, and variable deltas.
    """
    alerts = result.all_alerts
    predictions = result.all_predictions

    # Find variables that changed
    initial = result.tick_results[0].variables_before if result.tick_results else {}
    final = result.final_variables
    changed_vars = _variable_diff(initial, final)

    # Per-persona confidence trend
    persona_stats: dict[str, dict[str, Any]] = {}
    for assessment in result.all_assessments:
        name = assessment.persona_name
        if name not in persona_stats:
            persona_stats[name] = {
                "assessments": 0,
                "avg_confidence": 0.0,
                "total_alerts": 0,
                "total_predictions": 0,
                "confidences": [],
            }
        stats = persona_stats[name]
        stats["assessments"] += 1
        stats["confidences"].append(assessment.confidence)
        stats["total_alerts"] += len(assessment.alerts)
        stats["total_predictions"] += len(assessment.predictions)

    # Compute averages
    for stats in persona_stats.values():
        confs = stats.pop("confidences")
        stats["avg_confidence"] = round(sum(confs) / len(confs), 3) if confs else 0.0

    return {
        "scenario": result.scenario_name,
        "ticks": result.tick_count,
        "signals_injected": result.signal_count,
        "total_alerts": len(alerts),
        "total_predictions": len(predictions),
        "top_alerts": alerts[:5],
        "top_predictions": predictions[:5],
        "variable_changes": {
            k: {"from": v[0], "to": v[1]} for k, v in changed_vars.items()
        },
        "persona_stats": persona_stats,
        "duration_seconds": (
            result.completed_at - result.started_at
        ).total_seconds(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _variable_diff(
    before: dict[str, Any],
    after: dict[str, Any],
) -> dict[str, tuple[Any, Any]]:
    """Find variables that changed between two states."""
    changed: dict[str, tuple[Any, Any]] = {}
    all_keys = set(before) | set(after)
    for key in sorted(all_keys):
        old = before.get(key)
        new = after.get(key)
        if old != new:
            changed[key] = (old, new)
    return changed
