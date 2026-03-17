"""orchestrator.py

High-level agent orchestrator for Super_Agents.

Spawns, monitors, and manages agent processes running inside tmux sessions.
Each agent runs as ``python -m super_agents run`` inside its own session so
it is fully isolated, observable, and killable.

Usage:
    orch = get_orchestrator()
    session = orch.spawn_agent("biotech", "fda_tracker", "fetch_drug_approvals", args=["--days", "30"])
    print(orch.read_agent(session))
    orch.stop_agent(session)
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable
from typing import Any

from super_agents.orchestrator.tmux_manager import TmuxManager, SESSION_PREFIX
from super_agents.data.events import EventBus, get_bus
from super_agents.data.unified_store import UnifiedStore, get_store

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Spawn and manage agents running inside tmux sessions."""

    def __init__(
        self,
        tmux: TmuxManager | None = None,
        store: UnifiedStore | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._tmux = tmux or TmuxManager()
        self._store = store or get_store()
        self._bus = bus or get_bus()

    # -- Spawning -----------------------------------------------------------

    def spawn_agent(
        self,
        agent_name: str,
        skill: str,
        script: str,
        *,
        args: list[str] | None = None,
    ) -> str:
        """Spawn a single agent in a new tmux session.

        Args:
            agent_name: Agent identifier (e.g. ``biotech``).
            skill: Skill name (e.g. ``fda_tracker``).
            script: Script name without .py (e.g. ``fetch_drug_approvals``).
            args: Optional extra CLI arguments passed after the script name.

        Returns:
            The tmux session name (e.g. ``sa_biotech_fda_tracker``).

        Raises:
            RuntimeError: If tmux is not available.
        """
        if not self._tmux.has_tmux():
            raise RuntimeError("tmux is required but not found on PATH")

        safe_skill = skill.replace("_", "-")
        session_label = f"{agent_name}_{safe_skill}"

        # Build the command
        extra = " ".join(args) if args else ""
        cmd = (
            f"{sys.executable} -m super_agents run "
            f"--agent {agent_name} --skill {skill} --script {script}"
        )
        if extra:
            cmd = f"{cmd} -- {extra}"

        try:
            session_name = self._tmux.create_session(session_label, command=cmd)
        except RuntimeError as exc:
            logger.error("spawn_agent: failed to create session for %s/%s: %s", agent_name, skill, exc)
            raise

        try:
            self._bus.emit("agent_spawned", {
                "session": session_name,
                "agent": agent_name,
                "skill": skill,
                "script": script,
                "args": args or [],
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("spawn_agent: event emit failed: %s", exc)

        logger.info("Spawned agent %s/%s in session %s", agent_name, skill, session_name)
        return session_name

    def spawn_batch(self, tasks: list[dict[str, Any]]) -> list[str]:
        """Spawn multiple agents in parallel (best-effort).

        Each task dict must have keys: agent, skill, script.
        Optional key: args (list[str]).

        Returns:
            List of session names for successfully spawned agents.
        """
        sessions: list[str] = []
        for task in tasks:
            try:
                session = self.spawn_agent(
                    task["agent"],
                    task["skill"],
                    task["script"],
                    args=task.get("args"),
                )
                sessions.append(session)
            except (KeyError, RuntimeError) as exc:
                logger.error("spawn_batch: failed task %r: %s", task, exc)
        return sessions

    # -- Reading / writing --------------------------------------------------

    def read_agent(self, session_name: str, *, lines: int = 50) -> str:
        """Capture current pane output from an agent session.

        Args:
            session_name: Full or partial session name (sa_ prefix optional).
            lines: Number of lines to capture.

        Returns:
            Multi-line string, or empty string if session is not found.
        """
        return self._tmux.capture_pane(session_name, lines=lines)

    def send_to_agent(self, session_name: str, message: str) -> None:
        """Send a line of input to an agent session's pane."""
        self._tmux.send_keys(session_name, message, enter=True)

    # -- Stopping -----------------------------------------------------------

    def stop_agent(self, session_name: str) -> bool:
        """Kill a single agent session.

        Returns:
            True if killed, False if session was not found.
        """
        killed = self._tmux.kill_session(session_name)
        if killed:
            try:
                self._bus.emit("agent_stopped", {"session": session_name})
            except Exception as exc:  # noqa: BLE001
                logger.warning("stop_agent: event emit failed: %s", exc)
        return killed

    def stop_all(self) -> int:
        """Kill all sa_-prefixed sessions.

        Returns:
            Count of sessions killed.
        """
        sessions = self._tmux.list_sessions()
        count = 0
        for session in sessions:
            name = session["name"]
            if self._tmux.kill_session(name):
                count += 1
        logger.info("stop_all: killed %d sessions", count)
        return count

    # -- Status / monitoring ------------------------------------------------

    def fleet_status(self) -> list[dict[str, Any]]:
        """Return status of all running agent sessions.

        Returns:
            List of dicts with keys: name, agent, skill, alive, last_output_preview.
        """
        sessions = self._tmux.list_sessions()
        result: list[dict[str, Any]] = []
        for session in sessions:
            name = session["name"]
            # Parse agent/skill from session name: sa_{agent}_{skill}
            stripped = name.removeprefix(SESSION_PREFIX)
            parts = stripped.split("_", 1)
            agent = parts[0] if parts else ""
            skill = parts[1].replace("-", "_") if len(parts) > 1 else ""

            alive = self._tmux.is_session_alive(name)
            preview = ""
            if alive:
                output = self._tmux.capture_pane(name, lines=3)
                # Take last non-empty line as preview
                lines = [l for l in output.splitlines() if l.strip()]
                preview = lines[-1].strip() if lines else ""

            result.append({
                "name": name,
                "agent": agent,
                "skill": skill,
                "alive": alive,
                "last_output_preview": preview,
            })
        return result

    def monitor(
        self,
        *,
        interval_seconds: int = 30,
        callback: Callable[[list[dict[str, Any]]], None] | None = None,
    ) -> None:
        """Polling loop that checks all sessions and logs status.

        Runs until KeyboardInterrupt. Calls ``callback`` with fleet_status()
        on each tick if provided.

        Args:
            interval_seconds: Seconds between status checks.
            callback: Optional function called with fleet_status() each tick.
        """
        logger.info("monitor: starting (interval=%ds, Ctrl+C to stop)", interval_seconds)
        try:
            while True:
                status = self.fleet_status()
                alive_count = sum(1 for s in status if s["alive"])
                logger.info("monitor: %d sessions, %d alive", len(status), alive_count)
                for entry in status:
                    state = "alive" if entry["alive"] else "dead"
                    logger.info(
                        "  [%s] %s | %s",
                        state,
                        entry["name"],
                        entry["last_output_preview"][:80] if entry["last_output_preview"] else "(no output)",
                    )
                if callback is not None:
                    try:
                        callback(status)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("monitor: callback raised: %s", exc)
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("monitor: stopped by user")

    # -- Workflows ----------------------------------------------------------

    def run_workflow(
        self,
        workflow_name: str,
        tasks: list[dict[str, Any]],
        *,
        sequential: bool = False,
    ) -> dict[str, Any]:
        """Execute a named workflow (batch of tasks).

        Args:
            workflow_name: Human-readable name for logging.
            tasks: List of task dicts (same format as spawn_batch).
            sequential: If True, wait for each session to finish before spawning next.

        Returns:
            Summary dict with keys: workflow, spawned, failed, sessions.
        """
        logger.info("run_workflow: starting %r (%d tasks, sequential=%s)", workflow_name, len(tasks), sequential)
        spawned: list[str] = []
        failed: int = 0

        for task in tasks:
            try:
                session = self.spawn_agent(
                    task["agent"],
                    task["skill"],
                    task["script"],
                    args=task.get("args"),
                )
                spawned.append(session)
                if sequential:
                    _wait_for_session_end(self._tmux, session)
            except (KeyError, RuntimeError) as exc:
                logger.error("run_workflow: task failed %r: %s", task, exc)
                failed += 1

        summary = {
            "workflow": workflow_name,
            "spawned": len(spawned),
            "failed": failed,
            "sessions": spawned,
        }
        logger.info("run_workflow: %r complete — spawned=%d failed=%d", workflow_name, len(spawned), failed)
        return summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _wait_for_session_end(tmux: TmuxManager, session: str, *, poll_interval: int = 5, max_wait: int = 3600) -> None:
    """Block until the session is dead or max_wait seconds have passed."""
    elapsed = 0
    while elapsed < max_wait:
        if not tmux.is_session_alive(session):
            return
        time.sleep(poll_interval)
        elapsed += poll_interval
    logger.warning("_wait_for_session_end: timeout waiting for %s", session)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_default_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Return the module-level singleton Orchestrator (creates on first call)."""
    global _default_orchestrator  # noqa: PLW0603
    if _default_orchestrator is None:
        _default_orchestrator = Orchestrator()
    return _default_orchestrator
