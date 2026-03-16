"""Crucix Bridge — parse Crucix sweep output into Signal objects.

Crucix's fullBriefing() produces a single JSON blob with per-source results:
  {
    "crucix": { "timestamp": "...", "sourcesQueried": 27, ... },
    "results": [
      { "name": "GDELT", "status": "ok", "data": { ... } },
      { "name": "FRED",  "status": "ok", "data": { ... } },
      ...
    ]
  }

This module decomposes that blob into individual Signal objects,
one per meaningful observation, ready for routing to agents.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from super_agents.common.data_result import Signal
from super_agents.common.io_utils import read_json
from .source_map import CRUCIX_SOURCE_MAP, confidence_for_source, sectors_for_source

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Main parse functions
# ---------------------------------------------------------------------------

def parse_briefing(briefing_path: Path | str) -> list[Signal]:
    """Parse a Crucix briefing JSON file into a list of Signal objects.

    Args:
        briefing_path: Path to a Crucix briefing JSON (e.g. runs/latest.json).

    Returns:
        List of Signal objects, one per meaningful observation.
    """
    path = Path(briefing_path)
    if not path.exists():
        logger.warning("Crucix briefing not found: %s", path)
        return []

    data = read_json(path)
    return parse_briefing_data(data)


def parse_briefing_data(data: dict[str, Any]) -> list[Signal]:
    """Parse a Crucix briefing dict (already loaded) into Signal objects."""
    signals: list[Signal] = []

    meta = data.get("crucix", {})
    timestamp_str = meta.get("timestamp", "")
    try:
        sweep_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        sweep_time = datetime.now()

    results = data.get("results", [])
    for result in results:
        source_name = result.get("name", "unknown")
        status = result.get("status", "error")

        if status != "ok":
            # Emit a signal for source failure — agents may care
            signals.append(Signal(
                source="crucix",
                topic=f"source_failure.{source_name.lower()}",
                payload={"source": source_name, "error": result.get("error", "unknown")},
                timestamp=sweep_time,
                confidence="secondary",
                sectors=sectors_for_source(source_name),
            ))
            continue

        source_data = result.get("data", {})
        extractor = _EXTRACTORS.get(source_name)

        if extractor:
            extracted = extractor(source_name, source_data, sweep_time)
            signals.extend(extracted)
        else:
            # Generic: emit one signal with the raw data
            signals.append(Signal(
                source="crucix",
                topic=f"sweep.{source_name.lower()}",
                payload=_compact_payload(source_data),
                timestamp=sweep_time,
                confidence=confidence_for_source(source_name),
                sectors=sectors_for_source(source_name),
            ))

    logger.info("Parsed Crucix briefing: %d signals from %d sources", len(signals), len(results))
    return signals


def parse_delta(delta: dict[str, Any] | None, sweep_time: datetime | None = None) -> list[Signal]:
    """Parse a Crucix delta (from MemoryManager) into escalation/de-escalation signals.

    Delta structure:
      { "signals": { "new": [...], "escalated": [...], "deescalated": [...] },
        "summary": { "direction": "risk-on"|"risk-off"|"mixed", "criticalChanges": N } }
    """
    if not delta:
        return []

    sweep_time = sweep_time or datetime.now()
    signals: list[Signal] = []

    delta_signals = delta.get("signals", {})

    # Escalations — something got worse
    for item in delta_signals.get("escalated", []):
        signals.append(Signal(
            source="crucix.delta",
            topic=f"escalation.{item.get('key', 'unknown')}",
            payload={
                "label": item.get("label", ""),
                "from": item.get("from"),
                "to": item.get("to"),
                "change": item.get("change"),
                "pct_change": item.get("pctChange"),
                "severity": item.get("severity", "moderate"),
                "direction": "up",
            },
            timestamp=sweep_time,
            confidence="primary",
            sectors=_sectors_for_metric(item.get("key", "")),
        ))

    # De-escalations — something improved
    for item in delta_signals.get("deescalated", []):
        signals.append(Signal(
            source="crucix.delta",
            topic=f"deescalation.{item.get('key', 'unknown')}",
            payload={
                "label": item.get("label", ""),
                "from": item.get("from"),
                "to": item.get("to"),
                "change": item.get("change"),
                "pct_change": item.get("pctChange"),
                "severity": item.get("severity", "moderate"),
                "direction": "down",
            },
            timestamp=sweep_time,
            confidence="primary",
            sectors=_sectors_for_metric(item.get("key", "")),
        ))

    # New items (e.g., new urgent Telegram posts)
    for item in delta_signals.get("new", []):
        signals.append(Signal(
            source="crucix.delta",
            topic="new_item",
            payload=item if isinstance(item, dict) else {"value": item},
            timestamp=sweep_time,
            confidence="secondary",
            sectors=(),  # broadcast
        ))

    # Summary-level signal
    summary = delta.get("summary", {})
    if summary.get("criticalChanges", 0) > 0:
        signals.append(Signal(
            source="crucix.delta",
            topic="critical_change_detected",
            payload={
                "direction": summary.get("direction", "mixed"),
                "critical_count": summary.get("criticalChanges", 0),
            },
            timestamp=sweep_time,
            confidence="primary",
            sectors=(),  # broadcast critical changes to all
        ))

    return signals


# ---------------------------------------------------------------------------
# Per-source extractors — convert raw Crucix data into focused signals
# ---------------------------------------------------------------------------

def _extract_fred(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract FRED economic indicators as individual signals."""
    signals: list[Signal] = []
    if not isinstance(data, list):
        return signals

    for series in data:
        series_id = series.get("id", "")
        value = series.get("value")
        if value is None:
            continue

        signals.append(Signal(
            source="crucix",
            topic=f"economic.{series_id.lower()}",
            payload={"series_id": series_id, "value": value, "label": series.get("label", "")},
            timestamp=ts,
            confidence="primary",
            sectors=sectors_for_source(source),
        ))
    return signals


def _extract_acled(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract ACLED conflict data."""
    if not isinstance(data, dict):
        return []

    signals: list[Signal] = []
    total_events = data.get("totalEvents", 0)
    total_fatalities = data.get("totalFatalities", 0)

    if total_events > 0:
        signals.append(Signal(
            source="crucix",
            topic="conflict.summary",
            payload={
                "total_events": total_events,
                "total_fatalities": total_fatalities,
                "regions": data.get("byRegion", {}),
            },
            timestamp=ts,
            confidence="primary",
            sectors=sectors_for_source(source),
        ))

    # Individual high-fatality events
    for event in data.get("events", [])[:10]:
        if event.get("fatalities", 0) >= 5:
            signals.append(Signal(
                source="crucix",
                topic="conflict.event",
                payload=event,
                timestamp=ts,
                confidence="primary",
                sectors=sectors_for_source(source),
            ))

    return signals


def _extract_maritime(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract maritime/shipping signals."""
    if not isinstance(data, dict):
        return []

    signals: list[Signal] = []

    # Port congestion
    for port in data.get("congestion", []):
        signals.append(Signal(
            source="crucix",
            topic="maritime.congestion",
            payload=port,
            timestamp=ts,
            confidence="primary",
            sectors=sectors_for_source(source),
        ))

    # Strait transits
    for strait in data.get("straits", []):
        signals.append(Signal(
            source="crucix",
            topic=f"maritime.strait.{strait.get('name', 'unknown').lower().replace(' ', '_')}",
            payload=strait,
            timestamp=ts,
            confidence="primary",
            sectors=sectors_for_source(source),
        ))

    return signals


def _extract_who(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract WHO health alerts."""
    signals: list[Signal] = []
    items = data if isinstance(data, list) else data.get("alerts", []) if isinstance(data, dict) else []

    for alert in items[:20]:
        signals.append(Signal(
            source="crucix",
            topic="health.alert",
            payload=alert if isinstance(alert, dict) else {"text": str(alert)},
            timestamp=ts,
            confidence="primary",
            sectors=("biotech",),
        ))
    return signals


def _extract_telegram(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract urgent Telegram OSINT posts."""
    signals: list[Signal] = []
    if not isinstance(data, dict):
        return signals

    for post in data.get("urgent", [])[:20]:
        signals.append(Signal(
            source="crucix",
            topic="osint.urgent",
            payload=post if isinstance(post, dict) else {"text": str(post)},
            timestamp=ts,
            confidence="secondary",
            sectors=(),  # broadcast
        ))
    return signals


def _extract_yfinance(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract market data signals."""
    signals: list[Signal] = []
    items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []

    for item in items:
        ticker = item.get("symbol", item.get("ticker", ""))
        if not ticker:
            continue
        signals.append(Signal(
            source="crucix",
            topic=f"market.{ticker.lower()}",
            payload=item,
            timestamp=ts,
            confidence="primary",
            sectors=sectors_for_source(source),
        ))
    return signals


def _extract_eia(source: str, data: Any, ts: datetime) -> list[Signal]:
    """Extract EIA energy data."""
    signals: list[Signal] = []
    items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []

    for item in items:
        series_id = item.get("series", item.get("id", "energy"))
        signals.append(Signal(
            source="crucix",
            topic=f"energy.{series_id.lower().replace(' ', '_')}",
            payload=item,
            timestamp=ts,
            confidence="primary",
            sectors=sectors_for_source(source),
        ))
    return signals


# Extractor registry — add new extractors here as Crucix sources grow
_EXTRACTORS: dict[str, Any] = {
    "FRED": _extract_fred,
    "ACLED": _extract_acled,
    "Maritime": _extract_maritime,
    "WHO": _extract_who,
    "Telegram": _extract_telegram,
    "yfinance": _extract_yfinance,
    "EIA": _extract_eia,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compact_payload(data: Any, max_items: int = 20) -> dict[str, Any]:
    """Compact large payloads to prevent bloated signals."""
    if isinstance(data, list):
        return {"items": data[:max_items], "total": len(data)}
    if isinstance(data, dict):
        return {k: v for k, v in list(data.items())[:30]}
    return {"value": data}


# Metric key → relevant sectors (for delta signals)
_METRIC_SECTOR_MAP: dict[str, tuple[str, ...]] = {
    "vix": ("fintech",),
    "hy_spread": ("fintech",),
    "10y2y": ("fintech",),
    "wti": ("renewable_energy", "rare_earth", "fintech"),
    "brent": ("renewable_energy", "rare_earth", "fintech"),
    "natgas": ("renewable_energy",),
    "unemployment": ("fintech",),
    "fed_funds": ("fintech", "biotech"),
    "10y_yield": ("fintech",),
    "usd_index": ("fintech", "rare_earth"),
    "mortgage": ("fintech",),
    "urgent_posts": (),  # broadcast
    "thermal_total": ("renewable_energy", "rare_earth"),
    "air_total": ("aerospace",),
    "who_alerts": ("biotech",),
    "conflict_events": ("rare_earth", "renewable_energy", "aerospace"),
    "conflict_fatalities": ("rare_earth", "renewable_energy"),
    "sdr_online": ("aerospace",),
    "news_count": (),  # broadcast
    "sources_ok": (),  # broadcast
}


def _sectors_for_metric(key: str) -> tuple[str, ...]:
    """Return sectors interested in a delta metric."""
    return _METRIC_SECTOR_MAP.get(key, ())
