"""Small JSON helpers shared by the blueprint scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    """Read JSON with UTF-8 encoding."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    """Write JSON with a stable indentation format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_json_records(directory: Path) -> list[dict]:
    """Load JSON records from a directory into a flat list."""
    if not directory.exists():
        return []

    records: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        payload = read_json(path)
        if isinstance(payload, list):
            records.extend(item for item in payload if isinstance(item, dict))
        elif isinstance(payload, dict):
            records.append(payload)
    return records
