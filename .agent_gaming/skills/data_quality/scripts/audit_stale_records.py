"""
Audit gaming processed records for staleness.
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

PROCESSED_DIR = Path("data/processed")
OUTPUT_PATH = Path("dashboards/gaming_stale_records.json")
TARGET_DIRECTORIES = [
    "certifications",
    "storefront_metrics",
    "engagement_metrics",
    "gaming_sec_catalysts",
    "release_events",
    "title_scores",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit stale gaming records")
    parser.add_argument("--days", type=int, default=45, help="Files older than this threshold are flagged")
    args = parser.parse_args()

    cutoff = datetime.now() - timedelta(days=args.days)
    report = []

    for name in TARGET_DIRECTORIES:
        directory = PROCESSED_DIR / name
        if not directory.exists():
            continue

        for path in sorted(directory.glob("*.json")):
            modified = datetime.fromtimestamp(path.stat().st_mtime)
            if modified >= cutoff:
                continue
            age_days = (datetime.now() - modified).days
            report.append(
                {
                    "directory": name,
                    "path": str(path),
                    "last_modified": modified.isoformat(),
                    "age_days": age_days,
                    "severity": "high" if age_days >= (args.days * 2) else "moderate",
                }
            )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Flagged {len(report)} stale files. Report saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
