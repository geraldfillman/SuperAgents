"""Signal Router — route Crucix signals to matching agents.

The router sits between the bridge (which produces Signals) and the
agent registry (which knows which agents exist and what sectors they cover).

Flow:
  Crucix sweep → bridge.parse_briefing() → [Signal, ...] → router.route() → {agent: [Signal, ...]}
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable

from super_agents.common.data_result import Signal
from super_agents.common.registry import AgentRegistry

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Filter type
# ---------------------------------------------------------------------------

SignalFilter = Callable[[Signal], bool]


# ---------------------------------------------------------------------------
# Signal Router
# ---------------------------------------------------------------------------

class SignalRouter:
    """Routes signals to agents based on sector matching and optional filters.

    Usage:
        registry = AgentRegistry()
        router = SignalRouter(registry)

        # Optional: add custom filters
        router.add_filter("biotech", lambda s: "health" in s.topic or "fda" in s.topic)

        # Route signals
        routed = router.route(signals)
        # routed = {"biotech": [Signal, ...], "aerospace": [Signal, ...], ...}
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self._registry = registry
        self._filters: dict[str, list[SignalFilter]] = defaultdict(list)
        self._global_filters: list[SignalFilter] = []

    def add_filter(self, agent_name: str, filter_fn: SignalFilter) -> None:
        """Add a custom filter for a specific agent.

        The signal must pass ALL filters for the agent to receive it.
        """
        self._filters[agent_name].append(filter_fn)

    def add_global_filter(self, filter_fn: SignalFilter) -> None:
        """Add a filter applied to all signals before routing."""
        self._global_filters.append(filter_fn)

    def route(self, signals: list[Signal]) -> dict[str, list[Signal]]:
        """Route a batch of signals to matching agents.

        Args:
            signals: List of Signal objects from the bridge.

        Returns:
            Dict mapping agent_name → list of relevant signals.
        """
        routed: dict[str, list[Signal]] = defaultdict(list)
        agent_names = self._registry.agent_names

        for signal in signals:
            # Apply global filters
            if not self._passes_global_filters(signal):
                continue

            # Determine target agents
            if signal.sectors:
                # Signal specifies sectors — match to agents
                targets = [
                    name for name in agent_names
                    if name in signal.sectors
                ]
            else:
                # Broadcast signal — goes to all agents
                targets = list(agent_names)

            # Apply per-agent filters
            for agent_name in targets:
                if self._passes_agent_filters(agent_name, signal):
                    routed[agent_name].append(signal)

        if routed:
            logger.info(
                "Routed %d signals to %d agents: %s",
                sum(len(v) for v in routed.values()),
                len(routed),
                {k: len(v) for k, v in routed.items()},
            )

        return dict(routed)

    def route_single(self, signal: Signal) -> list[str]:
        """Return agent names that would receive this signal."""
        result = self.route([signal])
        return list(result.keys())

    def summary(self, signals: list[Signal]) -> dict[str, Any]:
        """Return a routing summary without actually dispatching.

        Useful for previewing what would happen with a set of signals.
        """
        routed = self.route(signals)
        return {
            "total_signals": len(signals),
            "agents_targeted": len(routed),
            "per_agent": {
                agent: {
                    "signal_count": len(agent_signals),
                    "topics": list({s.topic for s in agent_signals}),
                    "sources": list({s.source for s in agent_signals}),
                }
                for agent, agent_signals in routed.items()
            },
        }

    # -- Internal -----------------------------------------------------------

    def _passes_global_filters(self, signal: Signal) -> bool:
        return all(f(signal) for f in self._global_filters)

    def _passes_agent_filters(self, agent_name: str, signal: Signal) -> bool:
        filters = self._filters.get(agent_name, [])
        if not filters:
            return True
        return all(f(signal) for f in filters)
