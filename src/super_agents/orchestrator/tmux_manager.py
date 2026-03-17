"""tmux_manager.py

Low-level tmux wrapper for Super_Agents.

All sessions managed by this module are prefixed with SESSION_PREFIX ("sa_")
to avoid colliding with other tmux sessions on the same host.

Usage:
    mgr = TmuxManager()
    session = mgr.create_session("biotech_fda")
    mgr.send_keys(session, "python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals")
    output = mgr.capture_pane(session, lines=100)
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

SESSION_PREFIX = "sa_"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run(args: list[str], *, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    """Run a subprocess, capturing stdout/stderr as text."""
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _prefixed(name: str) -> str:
    """Return the full session name with SESSION_PREFIX, idempotent."""
    if name.startswith(SESSION_PREFIX):
        return name
    return f"{SESSION_PREFIX}{name}"


# ---------------------------------------------------------------------------
# TmuxManager
# ---------------------------------------------------------------------------

class TmuxManager:
    """Wrapper around tmux CLI for creating and managing agent sessions."""

    SESSION_PREFIX: str = SESSION_PREFIX

    # -- Environment check --------------------------------------------------

    @staticmethod
    def has_tmux() -> bool:
        """Return True if tmux is installed and on PATH."""
        return shutil.which("tmux") is not None

    def _require_tmux(self) -> None:
        if not self.has_tmux():
            import platform as _plat
            if _plat.system() == "Windows":
                raise RuntimeError(
                    "tmux is not available on Windows natively. "
                    "Options: (1) use WSL: wsl -- tmux, "
                    "(2) run individual scripts with 'python -m super_agents run', "
                    "(3) install tmux via MSYS2/Git Bash."
                )
            raise RuntimeError(
                "tmux is not installed or not on PATH. "
                "Install it with: apt-get install tmux (Debian/Ubuntu) "
                "or brew install tmux (macOS)."
            )

    # -- Session listing ----------------------------------------------------

    def list_sessions(self) -> list[dict[str, Any]]:
        """Return all active tmux sessions as a list of dicts.

        Each dict has keys: name, windows, created, attached.
        Only sessions with the SESSION_PREFIX are included.
        """
        self._require_tmux()
        result = _run([
            "tmux", "list-sessions",
            "-F", "#{session_name}|#{session_windows}|#{session_created}|#{session_attached}",
        ])
        if result.returncode != 0:
            # No sessions exist — tmux returns exit 1
            return []

        sessions: list[dict[str, Any]] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            name = parts[0]
            if not name.startswith(SESSION_PREFIX):
                continue
            sessions.append({
                "name": name,
                "windows": _safe_int(parts[1]),
                "created": parts[2],
                "attached": parts[3] == "1",
            })
        return sessions

    # -- Session lifecycle --------------------------------------------------

    def create_session(self, name: str, command: str | None = None) -> str:
        """Create a new detached tmux session named ``sa_{name}``.

        Args:
            name: Logical name (without the sa_ prefix).
            command: Optional shell command to run in the session on startup.

        Returns:
            The full session name (e.g. ``sa_biotech_fda``).

        Raises:
            RuntimeError: If tmux is not installed or the session already exists.
        """
        self._require_tmux()
        full_name = _prefixed(name)

        if self.is_session_alive(name):
            raise RuntimeError(f"Session already exists: {full_name}")

        args = ["tmux", "new-session", "-d", "-s", full_name]
        if command:
            args.extend([command])

        result = _run(args)
        if result.returncode != 0:
            logger.error("create_session failed for %s: %s", full_name, result.stderr.strip())
            raise RuntimeError(f"Failed to create session {full_name}: {result.stderr.strip()}")

        logger.info("Created tmux session: %s", full_name)
        return full_name

    def kill_session(self, name: str) -> bool:
        """Kill session ``sa_{name}``.

        Returns:
            True if the session was killed, False if it did not exist.
        """
        self._require_tmux()
        full_name = _prefixed(name)
        result = _run(["tmux", "kill-session", "-t", full_name])
        if result.returncode == 0:
            logger.info("Killed tmux session: %s", full_name)
            return True
        logger.debug("kill_session: session not found or already dead: %s", full_name)
        return False

    def is_session_alive(self, name: str) -> bool:
        """Return True if the session exists and is running."""
        self._require_tmux()
        full_name = _prefixed(name)
        result = _run(["tmux", "has-session", "-t", full_name])
        return result.returncode == 0

    # -- Key sending / pane capture -----------------------------------------

    def send_keys(self, session: str, keys: str, *, enter: bool = True) -> None:
        """Send keystrokes to the session's active pane.

        Args:
            session: Session name (with or without sa_ prefix).
            keys: The text or keystrokes to send.
            enter: If True, append a Return keystroke after ``keys``.
        """
        self._require_tmux()
        full_name = _prefixed(session)
        args = ["tmux", "send-keys", "-t", full_name, keys]
        if enter:
            args.append("Enter")
        result = _run(args)
        if result.returncode != 0:
            logger.error("send_keys failed for %s: %s", full_name, result.stderr.strip())

    def capture_pane(self, session: str, *, lines: int = 50) -> str:
        """Capture the last ``lines`` lines of output from the session.

        Returns:
            Multi-line string of captured output, or empty string on error.
        """
        self._require_tmux()
        full_name = _prefixed(session)
        # -p prints to stdout; -S -N means start N lines back from the bottom
        result = _run([
            "tmux", "capture-pane", "-p", "-t", full_name,
            "-S", f"-{lines}",
        ])
        if result.returncode != 0:
            logger.debug("capture_pane: failed for %s: %s", full_name, result.stderr.strip())
            return ""
        return result.stdout

    # -- Window management --------------------------------------------------

    def list_windows(self, session: str) -> list[dict[str, Any]]:
        """List all windows in a session.

        Returns:
            List of dicts with keys: index, name, active.
        """
        self._require_tmux()
        full_name = _prefixed(session)
        result = _run([
            "tmux", "list-windows", "-t", full_name,
            "-F", "#{window_index}|#{window_name}|#{window_active}",
        ])
        if result.returncode != 0:
            logger.debug("list_windows: session not found: %s", full_name)
            return []

        windows: list[dict[str, Any]] = []
        for line in result.stdout.strip().splitlines():
            parts = line.strip().split("|")
            if len(parts) < 3:
                continue
            windows.append({
                "index": _safe_int(parts[0]),
                "name": parts[1],
                "active": parts[2] == "1",
            })
        return windows

    def create_window(
        self,
        session: str,
        name: str,
        command: str | None = None,
    ) -> int:
        """Add a new named window to an existing session.

        Args:
            session: Session name (with or without sa_ prefix).
            name: Window name.
            command: Optional command to run in the new window.

        Returns:
            Window index of the newly created window.
        """
        self._require_tmux()
        full_name = _prefixed(session)
        args = ["tmux", "new-window", "-t", full_name, "-n", name, "-P",
                "-F", "#{window_index}"]
        if command:
            args.extend([command])
        result = _run(args)
        if result.returncode != 0:
            logger.error("create_window failed for %s/%s: %s", full_name, name, result.stderr.strip())
            return -1
        index = _safe_int(result.stdout.strip())
        logger.debug("Created window %d (%s) in session %s", index, name, full_name)
        return index


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return default
