"""Crucix Sidecar Runner — manage the Crucix Node.js process.

Two modes:
  1. Sidecar: Start Crucix server (port 3117), auto-sweep every 15 min
  2. One-shot: Run a single briefing sweep, save JSON, exit

The runner manages the lifecycle: start, health check, stop, and
reads output from the runs/ directory.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from super_agents.common.env import optional_env
from super_agents.common.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CRUCIX_DIR = Path(optional_env("CRUCIX_DIR", str(PROJECT_ROOT / "crucix")))
CRUCIX_PORT = int(optional_env("CRUCIX_PORT", "3117"))
CRUCIX_NODE = optional_env("CRUCIX_NODE", "node")
CRUCIX_RUNS_DIR = CRUCIX_DIR / "runs"

# Windows requires .cmd extension for npm/npx
_IS_WINDOWS = platform.system() == "Windows"
_NPM = "npm.cmd" if _IS_WINDOWS else "npm"


def is_crucix_installed() -> bool:
    """Check if Crucix is cloned and has node_modules."""
    return (
        (CRUCIX_DIR / "package.json").exists()
        and (CRUCIX_DIR / "node_modules").exists()
    )


def is_crucix_cloned() -> bool:
    """Check if Crucix repo is cloned (but maybe not installed)."""
    return (CRUCIX_DIR / "package.json").exists()


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def clone_crucix(target_dir: Path | None = None) -> Path:
    """Clone the Crucix repository.

    Args:
        target_dir: Where to clone. Defaults to PROJECT_ROOT/crucix.

    Returns:
        Path to the cloned directory.
    """
    target = target_dir or CRUCIX_DIR
    if target.exists():
        logger.info("Crucix directory already exists: %s", target)
        return target

    logger.info("Cloning Crucix to %s ...", target)
    result = subprocess.run(
        ["git", "clone", "https://github.com/calesthio/Crucix.git", str(target)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to clone Crucix: {result.stderr}")

    logger.info("Crucix cloned successfully")
    return target


def install_crucix() -> None:
    """Run npm install in the Crucix directory."""
    if not is_crucix_cloned():
        raise RuntimeError(f"Crucix not found at {CRUCIX_DIR}. Run clone_crucix() first.")

    logger.info("Installing Crucix dependencies...")
    result = subprocess.run(
        [_NPM, "install"],
        cwd=str(CRUCIX_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"npm install failed: {result.stderr}")

    logger.info("Crucix dependencies installed")


def setup_crucix_env(api_keys: dict[str, str] | None = None) -> None:
    """Create or update the Crucix .env file from Super_Agents env vars.

    Crucix reads API keys from its own .env. This function copies relevant
    keys from our environment into Crucix's .env file.

    Args:
        api_keys: Optional dict of KEY=VALUE to write. If None, copies
                  from current environment based on .env.example.
    """
    env_example = CRUCIX_DIR / ".env.example"
    env_file = CRUCIX_DIR / ".env"

    if api_keys:
        lines = [f"{k}={v}" for k, v in api_keys.items()]
    elif env_example.exists():
        # Parse .env.example for key names, fill from our environment
        lines = []
        for line in env_example.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                lines.append(line)
                continue
            key = line.split("=", 1)[0].strip()
            value = os.getenv(key, "")
            lines.append(f"{key}={value}")
    else:
        logger.warning("No .env.example found in Crucix, skipping env setup")
        return

    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Crucix .env configured with %d entries", len([l for l in lines if "=" in l and not l.startswith("#")]))


# ---------------------------------------------------------------------------
# One-shot sweep
# ---------------------------------------------------------------------------

def run_sweep() -> Path | None:
    """Run a single Crucix briefing sweep and return the output path.

    Executes `node apis/save-briefing.mjs` which saves to runs/latest.json.

    Returns:
        Path to the saved briefing JSON, or None on failure.
    """
    if not is_crucix_installed():
        raise RuntimeError(
            "Crucix not installed. Run 'python -m super_agents crucix setup' first."
        )

    # Pre-check: verify Node.js is available
    if shutil.which(CRUCIX_NODE) is None:
        raise RuntimeError(
            f"Node.js ({CRUCIX_NODE!r}) not found on PATH. "
            "Install Node.js 18+ to use Crucix."
        )

    # Pre-check: verify the sweep script exists
    sweep_script = CRUCIX_DIR / "apis" / "save-briefing.mjs"
    if not sweep_script.exists():
        raise RuntimeError(
            f"Crucix sweep script not found: {sweep_script}. "
            "Run 'python -m super_agents crucix setup' to re-install."
        )

    logger.info("Running Crucix sweep...")
    try:
        result = subprocess.run(
            [CRUCIX_NODE, "apis/save-briefing.mjs"],
            cwd=str(CRUCIX_DIR),
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        logger.error("Crucix sweep timed out after 120s")
        return None

    if result.returncode != 0:
        logger.error("Crucix sweep failed: %s", result.stderr[:500])
        return None

    latest = CRUCIX_RUNS_DIR / "latest.json"
    if latest.exists():
        logger.info("Crucix sweep complete: %s", latest)
        return latest

    logger.warning("Sweep completed but latest.json not found")
    return None


# ---------------------------------------------------------------------------
# Sidecar mode
# ---------------------------------------------------------------------------

_sidecar_process: subprocess.Popen | None = None


def start_sidecar() -> subprocess.Popen:
    """Start Crucix as a background sidecar process.

    Returns:
        The subprocess.Popen object for lifecycle management.
    """
    global _sidecar_process

    if not is_crucix_installed():
        raise RuntimeError("Crucix not installed. Run setup first.")

    if _sidecar_process and _sidecar_process.poll() is None:
        logger.info("Crucix sidecar already running (PID %d)", _sidecar_process.pid)
        return _sidecar_process

    logger.info("Starting Crucix sidecar on port %d...", CRUCIX_PORT)
    env = {**os.environ, "PORT": str(CRUCIX_PORT)}

    _sidecar_process = subprocess.Popen(
        [CRUCIX_NODE, "server.mjs"],
        cwd=str(CRUCIX_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait briefly for startup
    time.sleep(3)

    if _sidecar_process.poll() is not None:
        stderr = _sidecar_process.stderr.read().decode() if _sidecar_process.stderr else ""
        raise RuntimeError(f"Crucix sidecar failed to start: {stderr[:500]}")

    logger.info("Crucix sidecar started (PID %d)", _sidecar_process.pid)
    return _sidecar_process


def stop_sidecar() -> None:
    """Stop the Crucix sidecar process."""
    global _sidecar_process

    if _sidecar_process is None:
        return

    if _sidecar_process.poll() is None:
        logger.info("Stopping Crucix sidecar (PID %d)...", _sidecar_process.pid)
        _sidecar_process.terminate()
        try:
            _sidecar_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _sidecar_process.kill()
            _sidecar_process.wait()
        logger.info("Crucix sidecar stopped")

    _sidecar_process = None


def is_sidecar_running() -> bool:
    """Check if the sidecar process is alive."""
    return _sidecar_process is not None and _sidecar_process.poll() is None


# ---------------------------------------------------------------------------
# Read latest output
# ---------------------------------------------------------------------------

def get_latest_briefing() -> dict[str, Any] | None:
    """Read the latest Crucix briefing from disk.

    Returns:
        The parsed briefing dict, or None if not available.
    """
    latest = CRUCIX_RUNS_DIR / "latest.json"
    if not latest.exists():
        return None

    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read latest briefing: %s", exc)
        return None


def get_status() -> dict[str, Any]:
    """Return Crucix integration status."""
    return {
        "installed": is_crucix_installed(),
        "cloned": is_crucix_cloned(),
        "sidecar_running": is_sidecar_running(),
        "crucix_dir": str(CRUCIX_DIR),
        "port": CRUCIX_PORT,
        "latest_briefing_exists": (CRUCIX_RUNS_DIR / "latest.json").exists(),
    }
