"""Crucix integration — bridge between Crucix OSINT engine and Super_Agents.

Crucix is a Node.js sidecar that sweeps 27 data sources every 15 minutes,
producing structured JSON briefings. This package:

  - Parses Crucix output into Signal objects (bridge.py)
  - Maps Crucix sources to agent sectors (source_map.py)
  - Routes signals to matching agents (router.py)
  - Stores signals in SQLite for replay (store.py)
  - Manages the Crucix sidecar process (runner.py)
"""

from .bridge import parse_briefing, parse_delta
from .router import SignalRouter
from .source_map import CRUCIX_SOURCE_MAP, sectors_for_source

__all__ = [
    "parse_briefing",
    "parse_delta",
    "SignalRouter",
    "CRUCIX_SOURCE_MAP",
    "sectors_for_source",
]
