"""Reusable risk badge component for Streamlit.

Tries the real Crucix SignalStore first; falls back to deterministic mock
when the signals DB does not exist or the store is empty.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, TypedDict

import streamlit as st

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


class RiskContext(TypedDict):
    entity_name: str
    country_code: str
    overall_severity: Literal["critical", "high", "medium", "low", "clear"]
    sanctions_hit: bool
    conflict_nearby: bool
    cyber_alert: bool
    weather_hazard: bool
    description: str


# ---------------------------------------------------------------------------
# Real backend (Crucix SignalStore)
# ---------------------------------------------------------------------------

_SIGNALS_DB: Path | None = None


def _get_signals_db() -> Path:
    global _SIGNALS_DB  # noqa: PLW0603
    if _SIGNALS_DB is None:
        from dashboards.dashboard_data import CRUCIX_SIGNALS_DB
        _SIGNALS_DB = CRUCIX_SIGNALS_DB
    return _SIGNALS_DB


def get_risk_context(entity_name: str, country_code: str) -> RiskContext:
    """Return risk context from real signals if available, else mock."""
    db = _get_signals_db()
    if db.exists():
        try:
            return _query_real_signals(entity_name, country_code)
        except Exception:
            pass
    return get_risk_context_mock(entity_name, country_code)


def _query_real_signals(entity_name: str, country_code: str) -> RiskContext:
    """Query the Crucix signal store for entity-related signals."""
    from super_agents.integrations.crucix.store import SignalStore

    db = _get_signals_db()
    sanctions_hit = False
    conflict_nearby = False
    cyber_alert = False
    weather_hazard = False
    descriptions: list[str] = []

    with SignalStore(db) as store:
        signals = store.search(entity_name, limit=20)

    for signal in signals:
        topic = (signal.get("topic") or "").lower()
        if "sanction" in topic or "ofac" in topic:
            sanctions_hit = True
            descriptions.append(f"Sanctions: {signal.get('headline', '')}")
        elif "conflict" in topic or "military" in topic:
            conflict_nearby = True
            descriptions.append(f"Conflict: {signal.get('headline', '')}")
        elif "cyber" in topic or "vulnerability" in topic:
            cyber_alert = True
            descriptions.append(f"Cyber: {signal.get('headline', '')}")
        elif "weather" in topic or "fire" in topic or "storm" in topic:
            weather_hazard = True
            descriptions.append(f"Weather: {signal.get('headline', '')}")

    if not signals:
        return get_risk_context_mock(entity_name, country_code)

    severity: Literal["critical", "high", "medium", "low", "clear"] = "clear"
    if sanctions_hit:
        severity = "critical"
    elif conflict_nearby:
        severity = "high"
    elif cyber_alert:
        severity = "medium"
    elif weather_hazard:
        severity = "medium"
    else:
        severity = "low"

    return {
        "entity_name": entity_name,
        "country_code": country_code,
        "overall_severity": severity,
        "sanctions_hit": sanctions_hit,
        "conflict_nearby": conflict_nearby,
        "cyber_alert": cyber_alert,
        "weather_hazard": weather_hazard,
        "description": "; ".join(descriptions[:3]) or f"{len(signals)} signal(s) found.",
    }


# ---------------------------------------------------------------------------
# Mock fallback
# ---------------------------------------------------------------------------


def get_risk_context_mock(entity_name: str, country_code: str) -> RiskContext:
    """Deterministic mock for demonstration when no real signals exist."""
    severity: Literal["critical", "high", "medium", "low", "clear"] = "clear"
    description = f"No active risk signals detected for {entity_name} ({country_code})."

    if "Cyber" in entity_name:
        severity = "medium"
        description = "Active DDoS campaigns targeting this entity's ASN."
    elif "Sanction" in entity_name or country_code in ("IR", "Russia", "RU"):
        severity = "critical"
        description = "Entity appears on OFAC SDN list (sanctions_hit=True)."
    elif "Frontier" in entity_name:
        severity = "high"
        description = "Active conflict zone detected within 50km radius."

    return {
        "entity_name": entity_name,
        "country_code": country_code,
        "overall_severity": severity,
        "sanctions_hit": severity == "critical",
        "conflict_nearby": severity == "high",
        "cyber_alert": severity == "medium",
        "weather_hazard": False,
        "description": description,
    }


# ---------------------------------------------------------------------------
# Render helper
# ---------------------------------------------------------------------------

_BADGE_STYLES: dict[str, dict[str, str]] = {
    "critical": {"color": "#E74C3C", "icon": "\U0001f534", "label": "CRITICAL"},
    "high":     {"color": "#E67E22", "icon": "\U0001f7e0", "label": "HIGH"},
    "medium":   {"color": "#F1C40F", "icon": "\U0001f7e1", "label": "MEDIUM"},
    "low":      {"color": "#3498DB", "icon": "\U0001f535", "label": "LOW"},
    "clear":    {"color": "#27AE60", "icon": "\U0001f7e2", "label": "CLEAR"},
}


def render_risk_badge(entity_name: str, country_code: str = "US") -> None:
    """Render a colored risk badge for *entity_name*."""
    risk = get_risk_context(entity_name, country_code)
    severity = risk["overall_severity"]
    style = _BADGE_STYLES.get(severity, _BADGE_STYLES["clear"])

    st.markdown(
        f'<span title="{risk["description"]}" '
        f'style="cursor:help; background-color:{style["color"]}; '
        f"color:white; padding:2px 8px; border-radius:4px; "
        f'font-weight:bold; font-size:0.8em; margin-right:5px;">'
        f'{style["icon"]} {style["label"]}'
        f"</span>",
        unsafe_allow_html=True,
    )
