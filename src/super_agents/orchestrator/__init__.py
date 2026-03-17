"""orchestrator — tmux-based agent orchestration for Super_Agents.

Re-exports the primary public API so callers can do:
    from super_agents.orchestrator import TmuxManager, Orchestrator, Scheduler, get_orchestrator
"""

from __future__ import annotations

from super_agents.orchestrator.tmux_manager import TmuxManager
from super_agents.orchestrator.orchestrator import Orchestrator, get_orchestrator
from super_agents.orchestrator.scheduler import Scheduler, get_scheduler

__all__ = [
    "TmuxManager",
    "Orchestrator",
    "get_orchestrator",
    "Scheduler",
    "get_scheduler",
]
