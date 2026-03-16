"""Reusable risk badge component for Streamlit."""

import streamlit as st
from typing import Literal, TypedDict, Optional

# Define the RiskContext based on the documentation's intended schema
class RiskContext(TypedDict):
    entity_name: str
    country_code: str
    overall_severity: Literal["critical", "high", "medium", "low", "clear"]
    sanctions_hit: bool
    conflict_nearby: bool
    cyber_alert: bool
    weather_hazard: bool
    description: str

def get_risk_context_mock(entity_name: str, country_code: str) -> RiskContext:
    """Mock implementation of get_risk_context until the backend is ready."""
    # Simple deterministic mock for demonstration purposes
    severity: Literal["critical", "high", "medium", "low", "clear"] = "clear"
    description = f"No active risk signals detected for {entity_name} ({country_code})."
    
    # Just some sample logic to show different states in the UI
    if "Cyber" in entity_name:
        severity = "medium"
        description = "Active DDoS campaigns targeting this entity's ASN."
    elif "Sanction" in entity_name or "Iran" in country_code or "Russia" in country_code:
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
        "description": description
    }

def render_risk_badge(entity_name: str, country_code: str = "US"):
    """
    Renders a colored risk badge for a given entity.
    
    In the future, this will call:
    from super_agents.common.risk_layer import get_risk_context
    """
    
    # Use mock for now
    risk = get_risk_context_mock(entity_name, country_code)
    severity = risk["overall_severity"]
    
    # Style mapping
    styles = {
        "critical": {"color": "red", "icon": "🔴", "label": "CRITICAL"},
        "high": {"color": "orange", "icon": "🟠", "label": "HIGH"},
        "medium": {"color": "yellow", "icon": "🟡", "label": "MEDIUM"},
        "low": {"color": "blue", "icon": "🔵", "label": "LOW"},
        "clear": {"color": "green", "icon": "🟢", "label": "CLEAR"},
    }
    
    style = styles.get(severity, styles["clear"])
    
    # Render with a tooltip showing the description
    st.markdown(
        f'<span title="{risk["description"]}" style="cursor: help; background-color: {style["color"]}; '
        f'color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold; '
        f'font-size: 0.8em; margin-right: 5px;">'
        f'{style["icon"]} {style["label"]}'
        f'</span>',
        unsafe_allow_html=True
    )
