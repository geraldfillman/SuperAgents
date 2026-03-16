"""
Normalize a starter list of gaming studios for coverage review.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

INPUT_PATH = Path("data/raw/gaming/studio_candidates.json")
OUT_DIR = Path("data/processed/studio_screener")


def _normalize(record: dict) -> dict:
    return {
        "company_id": record.get("company_id") or record.get("ticker") or record.get("company_name", "").upper().replace(" ", "_"),
        "company_name": record.get("company_name", ""),
        "ticker": record.get("ticker", ""),
        "exchange": record.get("exchange", ""),
        "country": record.get("country", ""),
        "market_cap_bucket": record.get("market_cap_bucket", ""),
        "lead_focus": record.get("lead_focus") or record.get("genre_focus") or "",
        "notes": record.get("notes", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Screen gaming studios from a local candidate file")
    parser.add_argument("--input", type=Path, default=INPUT_PATH, help="Local JSON file with studio candidates")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"No candidate file found at {args.input}. Create it with a JSON array of studio records.")
        return

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = [payload]
    if not isinstance(payload, list):
        print("Candidate file must contain a JSON object or array.")
        return

    records = [_normalize(record) for record in payload if isinstance(record, dict)]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"studio_candidates_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    out_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Normalized {len(records)} studio candidates to {out_path}")


if __name__ == "__main__":
    main()
