"""cli_commands.py

CLI subcommands for the Super_Agents orchestrator.

These are plain functions (not a class) that can be wired into the existing
argparse-based CLI in super_agents/cli.py, or called directly from scripts.

Usage (standalone):
    from super_agents.orchestrator.cli_commands import cmd_fleet_status
    cmd_fleet_status()
"""

from __future__ import annotations

import logging
import sys
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fleet / agent commands
# ---------------------------------------------------------------------------

def cmd_fleet_status() -> None:
    """Print a formatted table of all running agent sessions."""
    from super_agents.orchestrator.orchestrator import get_orchestrator

    orch = get_orchestrator()
    try:
        fleet = orch.fleet_status()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return

    if not fleet:
        print("No active agent sessions.")
        return

    header = f"{'SESSION':<35} {'AGENT':<15} {'SKILL':<20} {'ALIVE':<6} PREVIEW"
    print(header)
    print("-" * len(header))
    for entry in fleet:
        alive_str = "yes" if entry["alive"] else "no"
        preview = entry["last_output_preview"][:60] if entry["last_output_preview"] else ""
        print(
            f"{entry['name']:<35} {entry['agent']:<15} {entry['skill']:<20} {alive_str:<6} {preview}"
        )


def cmd_spawn(agent: str, skill: str, script: str, args: list[str]) -> None:
    """Spawn a single agent and print the session name.

    Args:
        agent: Agent name.
        skill: Skill name.
        script: Script name (without .py).
        args: Extra CLI arguments to pass to the script.
    """
    from super_agents.orchestrator.orchestrator import get_orchestrator

    orch = get_orchestrator()
    try:
        session = orch.spawn_agent(agent, skill, script, args=args or None)
        print(f"Spawned: {session}")
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)


def cmd_read(session: str, lines: int = 50) -> None:
    """Print captured output from an agent session.

    Args:
        session: Session name (sa_ prefix optional).
        lines: Number of output lines to capture.
    """
    from super_agents.orchestrator.orchestrator import get_orchestrator

    orch = get_orchestrator()
    output = orch.read_agent(session, lines=lines)
    if output:
        print(output)
    else:
        print(f"(No output from session {session!r})")


def cmd_send(session: str, message: str) -> None:
    """Send a message/command to a running agent session.

    Args:
        session: Session name.
        message: Text to send (Enter key appended automatically).
    """
    from super_agents.orchestrator.orchestrator import get_orchestrator

    orch = get_orchestrator()
    try:
        orch.send_to_agent(session, message)
        print(f"Sent to {session!r}: {message!r}")
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)


def cmd_stop(session: str | None = None) -> None:
    """Stop one or all agent sessions.

    Args:
        session: Session name to stop. If None, stops ALL sa_-prefixed sessions.
    """
    from super_agents.orchestrator.orchestrator import get_orchestrator

    orch = get_orchestrator()
    try:
        if session is None:
            count = orch.stop_all()
            print(f"Stopped {count} session(s).")
        else:
            killed = orch.stop_agent(session)
            if killed:
                print(f"Stopped: {session}")
            else:
                print(f"Session not found or already stopped: {session}")
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Schedule commands
# ---------------------------------------------------------------------------

def cmd_schedule_list() -> None:
    """Print all registered schedules in a formatted table."""
    from super_agents.orchestrator.scheduler import get_scheduler

    sched = get_scheduler()
    schedules = sched.list_schedules()

    if not schedules:
        print("No schedules registered.")
        return

    header = f"{'NAME':<25} {'CRON':<12} {'AGENT':<12} {'SKILL':<20} {'ENABLED':<8} ARGS"
    print(header)
    print("-" * len(header))
    for s in schedules:
        enabled_str = "yes" if s.enabled else "no"
        args_str = " ".join(s.args) if s.args else ""
        print(
            f"{s.name:<25} {s.cron_expr:<12} {s.agent:<12} {s.skill:<20} {enabled_str:<8} {args_str}"
        )


def cmd_schedule_add(
    name: str,
    cron: str,
    agent: str,
    skill: str,
    script: str,
    args: list[str] | None = None,
) -> None:
    """Add a schedule and persist it.

    Args:
        name: Unique schedule name.
        cron: Cron expression (e.g. ``*/30``, ``06:00``, ``0 6 * * *``).
        agent: Agent name.
        skill: Skill name.
        script: Script name (without .py).
        args: Optional extra CLI arguments.
    """
    from super_agents.orchestrator.scheduler import get_scheduler

    sched = get_scheduler()
    try:
        schedule = sched.add(name, cron, agent, skill, script, args=args)
        sched.save_schedules()
        print(f"Added schedule {schedule.name!r}: {agent}/{skill} @ {cron}")
    except (ValueError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)


def cmd_schedule_run() -> None:
    """Start the scheduler loop (blocks until Ctrl+C)."""
    from super_agents.orchestrator.scheduler import get_scheduler

    sched = get_scheduler()
    # Auto-load persisted schedules before starting
    try:
        sched.load_schedules()
    except Exception as exc:  # noqa: BLE001
        logger.warning("cmd_schedule_run: could not load schedules: %s", exc)

    count = len(sched.list_schedules())
    print(f"Starting scheduler with {count} schedule(s). Press Ctrl+C to stop.")
    sched.run()


# ---------------------------------------------------------------------------
# Monitor command
# ---------------------------------------------------------------------------

def cmd_monitor() -> None:
    """Start the fleet monitoring loop (blocks until Ctrl+C)."""
    from super_agents.orchestrator.orchestrator import get_orchestrator

    orch = get_orchestrator()

    def _print_status(fleet: list[dict[str, Any]]) -> None:
        alive = sum(1 for s in fleet if s["alive"])
        print(f"[fleet] {len(fleet)} sessions | {alive} alive")
        for entry in fleet:
            state = "UP  " if entry["alive"] else "DOWN"
            preview = entry["last_output_preview"][:60] if entry["last_output_preview"] else ""
            print(f"  [{state}] {entry['name']:<35} {preview}")
        print()

    print("Starting monitor (Ctrl+C to stop)...")
    orch.monitor(interval_seconds=30, callback=_print_status)
