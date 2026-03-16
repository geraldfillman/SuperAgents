"""Map Crucix's 27 data sources to Super_Agents sectors.

Each Crucix source produces data relevant to one or more agent sectors.
An empty sectors tuple means "broadcast to all agents" (global signal).

Crucix Source Tiers:
  Tier 1: Core OSINT & Geopolitical (GDELT, OpenSky, FIRMS, Maritime, etc.)
  Tier 2: Economic & Financial (FRED, Treasury, BLS, EIA, etc.)
  Tier 3: Weather, Environment, Technology, Social
  Tier 4: Space & Satellites
  Tier 5: Live Market Data (yfinance)
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Source → Sector mapping
# ---------------------------------------------------------------------------

CRUCIX_SOURCE_MAP: dict[str, dict[str, Any]] = {
    # === Tier 1: Core OSINT & Geopolitical ===
    "GDELT": {
        "sectors": ("aerospace", "cybersecurity", "rare_earth", "renewable_energy"),
        "signal_types": ("geopolitical_event", "conflict", "protest", "policy_change"),
        "confidence": "secondary",
        "description": "Global Event, Language, and Tone database  - news-based event detection",
    },
    "OpenSky": {
        "sectors": ("aerospace", "autonomous_vehicles"),
        "signal_types": ("air_traffic_anomaly", "military_activity", "flight_pattern_change"),
        "confidence": "primary",
        "description": "Real-time ADS-B flight tracking  - 4,000 credits/day",
    },
    "FIRMS": {
        "sectors": ("renewable_energy", "rare_earth"),
        "signal_types": ("wildfire", "industrial_fire", "thermal_anomaly"),
        "confidence": "primary",
        "description": "NASA FIRMS  - satellite-detected thermal hotspots",
    },
    "Maritime": {
        "sectors": ("rare_earth", "renewable_energy", "fintech"),
        "signal_types": ("shipping_disruption", "port_congestion", "route_change", "sanctions_evasion"),
        "confidence": "primary",
        "description": "AIS ship tracking  - vessel positions and movements",
    },
    "Safecast": {
        "sectors": ("renewable_energy",),
        "signal_types": ("radiation_anomaly", "environmental_alert"),
        "confidence": "primary",
        "description": "Citizen radiation monitoring network",
    },
    "ACLED": {
        "sectors": ("rare_earth", "renewable_energy", "aerospace"),
        "signal_types": ("armed_conflict", "protest", "political_violence"),
        "confidence": "primary",
        "description": "Armed Conflict Location & Event Data",
    },
    "ReliefWeb": {
        "sectors": (),  # broadcast
        "signal_types": ("humanitarian_crisis", "disaster", "emergency"),
        "confidence": "primary",
        "description": "UN OCHA humanitarian updates",
    },
    "WHO": {
        "sectors": ("biotech",),
        "signal_types": ("disease_outbreak", "health_emergency", "pandemic_signal"),
        "confidence": "primary",
        "description": "World Health Organization disease outbreak news",
    },
    "OFAC": {
        "sectors": ("fintech", "rare_earth", "cybersecurity"),
        "signal_types": ("sanctions_update", "sdn_list_change", "compliance_alert"),
        "confidence": "primary",
        "description": "US Treasury OFAC sanctions lists",
    },
    "OpenSanctions": {
        "sectors": ("fintech", "rare_earth", "cybersecurity"),
        "signal_types": ("sanctions_update", "pep_change", "entity_flagged"),
        "confidence": "primary",
        "description": "Global sanctions and PEP database",
    },
    "ADS-B": {
        "sectors": ("aerospace",),
        "signal_types": ("military_aircraft", "surveillance_pattern", "emergency_squawk"),
        "confidence": "primary",
        "description": "ADS-B Exchange  - military and special aircraft tracking",
    },

    # === Tier 2: Economic & Financial ===
    "FRED": {
        "sectors": ("fintech", "renewable_energy", "biotech"),
        "signal_types": ("rate_change", "yield_curve", "economic_indicator"),
        "confidence": "primary",
        "description": "Federal Reserve Economic Data  - VIX, yields, spreads",
    },
    "Treasury": {
        "sectors": ("fintech",),
        "signal_types": ("auction_result", "debt_issuance", "fiscal_data"),
        "confidence": "primary",
        "description": "US Treasury auction results and fiscal data",
    },
    "BLS": {
        "sectors": ("fintech",),
        "signal_types": ("jobs_report", "cpi_release", "wage_data"),
        "confidence": "primary",
        "description": "Bureau of Labor Statistics  - employment and CPI",
    },
    "EIA": {
        "sectors": ("renewable_energy", "rare_earth"),
        "signal_types": ("energy_supply", "inventory_change", "production_data"),
        "confidence": "primary",
        "description": "Energy Information Administration  - oil, gas, renewables",
    },
    "GSCPI": {
        "sectors": ("rare_earth", "renewable_energy", "fintech"),
        "signal_types": ("supply_chain_pressure", "logistics_stress"),
        "confidence": "secondary",
        "description": "Global Supply Chain Pressure Index (NY Fed)",
    },
    "USAspending": {
        "sectors": ("aerospace", "cybersecurity", "quantum"),
        "signal_types": ("contract_award", "grant_award", "spending_change"),
        "confidence": "primary",
        "description": "Federal spending on contracts and grants",
    },
    "Comtrade": {
        "sectors": ("rare_earth", "renewable_energy"),
        "signal_types": ("trade_flow_change", "export_restriction", "import_surge"),
        "confidence": "primary",
        "description": "UN Comtrade  - international commodity trade flows",
    },

    # === Tier 3: Weather, Environment, Technology, Social ===
    "NOAA": {
        "sectors": ("renewable_energy",),
        "signal_types": ("severe_weather", "climate_event", "hurricane_track"),
        "confidence": "primary",
        "description": "National weather alerts and climate data",
    },
    "EPA": {
        "sectors": ("renewable_energy", "rare_earth"),
        "signal_types": ("regulatory_action", "enforcement", "permit_change"),
        "confidence": "primary",
        "description": "EPA enforcement actions and regulatory updates",
    },
    "Patents": {
        "sectors": ("quantum", "biotech", "aerospace", "cybersecurity"),
        "signal_types": ("patent_filing", "technology_signal", "ip_activity"),
        "confidence": "secondary",
        "description": "USPTO patent filings and grants",
    },
    "Bluesky": {
        "sectors": (),  # broadcast  - social signals are cross-sector
        "signal_types": ("social_sentiment", "trending_topic", "expert_post"),
        "confidence": "sponsor",
        "description": "Bluesky social network posts",
    },
    "Reddit": {
        "sectors": ("gaming", "biotech", "quantum", "cybersecurity"),
        "signal_types": ("community_sentiment", "product_discussion", "leak"),
        "confidence": "sponsor",
        "description": "Reddit community discussions",
    },
    "Telegram": {
        "sectors": (),  # broadcast  - OSINT channels are cross-sector
        "signal_types": ("urgent_osint", "channel_alert", "breaking_news"),
        "confidence": "secondary",
        "description": "Telegram OSINT channels  - urgent intelligence posts",
    },
    "KiwiSDR": {
        "sectors": ("aerospace",),
        "signal_types": ("rf_anomaly", "signal_detection", "spectrum_change"),
        "confidence": "secondary",
        "description": "Software-defined radio monitoring network",
    },

    # === Tier 4: Space & Satellites ===
    "Space": {
        "sectors": ("aerospace", "quantum"),
        "signal_types": ("launch_event", "satellite_maneuver", "debris_alert"),
        "confidence": "primary",
        "description": "Space-Track and launch provider data",
    },

    # === Tier 5: Live Market Data ===
    "yfinance": {
        "sectors": ("fintech", "biotech", "gaming", "aerospace", "renewable_energy", "rare_earth"),
        "signal_types": ("price_move", "volume_spike", "earnings_surprise"),
        "confidence": "primary",
        "description": "Yahoo Finance  - real-time market data",
    },
}


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def sectors_for_source(source_name: str) -> tuple[str, ...]:
    """Return the sectors that care about a given Crucix source.

    Empty tuple means broadcast to all.
    """
    entry = CRUCIX_SOURCE_MAP.get(source_name, {})
    return tuple(entry.get("sectors", ()))


def sources_for_sector(sector: str) -> list[str]:
    """Return all Crucix sources relevant to a given sector."""
    matches: list[str] = []
    for source_name, mapping in CRUCIX_SOURCE_MAP.items():
        sectors = mapping.get("sectors", ())
        if not sectors or sector in sectors:
            matches.append(source_name)
    return matches


def confidence_for_source(source_name: str) -> str:
    """Return the default confidence level for a Crucix source."""
    entry = CRUCIX_SOURCE_MAP.get(source_name, {})
    return entry.get("confidence", "secondary")


def all_source_names() -> list[str]:
    """Return all known Crucix source names."""
    return sorted(CRUCIX_SOURCE_MAP.keys())
