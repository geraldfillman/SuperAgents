"""
Normalize certification or rating-board snapshots into gaming tracker records.
"""

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAW_DIR = Path("data/raw/certifications")
OUT_DIR = Path("data/processed/certifications")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()) or "unknown"


def _load_input_files(input_file: Path | None, days: int | None) -> list[Path]:
    if input_file is not None:
        return [input_file]

    if not RAW_DIR.exists():
        return []

    files = sorted(RAW_DIR.glob("*.json"))
    if days is None:
        return files

    cutoff = datetime.now() - timedelta(days=days)
    return [path for path in files if datetime.fromtimestamp(path.stat().st_mtime) >= cutoff]


def _normalize(record: dict) -> dict:
    title = record.get("title") or record.get("game_title") or record.get("name") or ""
    registry = record.get("registry_name") or record.get("registry") or "unknown_registry"
    date_value = (
        record.get("signal_date")
        or record.get("rating_date")
        or record.get("date")
        or datetime.now().date().isoformat()
    )
    return {
        "certification_id": record.get("certification_id") or f"{_slug(registry)}_{_slug(title)}_{_slug(str(date_value))}",
        "title": title,
        "title_id": record.get("title_id", ""),
        "registry_name": registry,
        "territory": record.get("territory", ""),
        "rating_or_status": record.get("rating_or_status") or record.get("rating") or record.get("status") or "",
        "signal_type": record.get("signal_type") or "rating_registry_entry",
        "signal_date": str(date_value),
        "source_url": record.get("source_url") or record.get("url") or "",
        "source_confidence": record.get("source_confidence") or "primary",
        "notes": record.get("notes", ""),
    }


def _read_records(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [_normalize(item) for item in payload]
    if isinstance(payload, dict) and "results" in payload and isinstance(payload["results"], list):
        return [_normalize(item) for item in payload["results"]]
    if isinstance(payload, dict):
        return [_normalize(payload)]
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize certification snapshots")
    parser.add_argument("--input", type=Path, help="Single JSON file to normalize")
    parser.add_argument("--days", type=int, default=None, help="Filter raw files by modification age")
    args = parser.parse_args()

    files = _load_input_files(args.input, args.days)
    if not files:
        print("No certification snapshot files found in data/raw/certifications/")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_records: list[dict] = []
    for path in files:
        all_records.extend(_read_records(path))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = OUT_DIR / f"certifications_{timestamp}.json"
    out_path.write_text(json.dumps(all_records, indent=2), encoding="utf-8")
    print(f"Normalized {len(all_records)} certification records to {out_path}")


if __name__ == "__main__":
    main()
