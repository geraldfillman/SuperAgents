"""Filesystem helpers shared across all sector agents."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"
SCHEMA_DIR = PROJECT_ROOT / "schema"


def project_path(*parts: str) -> Path:
    """Resolve a path relative to the project root."""
    return PROJECT_ROOT.joinpath(*parts)


def ensure_directory(path: Path) -> Path:
    """Create a directory if needed and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def agent_data_dir(sector: str, kind: str = "raw") -> Path:
    """Return the data directory for a specific sector agent.

    Args:
        sector: Agent sector name (e.g. 'biotech', 'gaming', 'aerospace').
        kind: Either 'raw' or 'processed'.
    """
    return ensure_directory(DATA_DIR / kind / sector)


def slugify(value: str) -> str:
    """Generate a stable filesystem-safe label."""
    safe = "".join(char.lower() if char.isalnum() else "_" for char in value.strip())
    return safe.strip("_") or "item"
