"""
Build a rolling gaming release calendar from processed JSON sources.
"""

import argparse
import csv
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.gaming.io_utils import load_json_records, write_json
from super_agents.gaming.paths import (
    CERTIFICATIONS_DIR,
    DASHBOARDS_DIR,
    GAMING_SEC_CATALYSTS_DIR,
    RELEASE_EVENTS_DIR,
    STOREFRONT_METRICS_DIR,
    ensure_gaming_directory,
)

OUTPUT_DIR = DASHBOARDS_DIR


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None

    candidate = str(value).strip()
    if len(candidate) == 7 and candidate[0] == "Q" and candidate[2] == " ":
        try:
            quarter, year = candidate.split()
            quarter_number = int(quarter[1])
            if quarter_number in (1, 2, 3, 4):
                month = ((quarter_number - 1) * 3) + 1
                return datetime(int(year), month, 1)
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %b, %Y", "%d %B, %Y", "%Y-%m"):
        try:
            parsed = datetime.strptime(candidate, fmt)
            if fmt == "%Y-%m":
                return parsed.replace(day=1)
            return parsed
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None

def _build_release_events(start: datetime, end: datetime) -> list[dict]:
    records = load_json_records(RELEASE_EVENTS_DIR)
    results: list[dict] = []
    for record in records:
        event_date = _parse_date(record.get("expected_release_date") or record.get("event_date"))
        if event_date is None or not (start <= event_date <= end):
            continue
        results.append(
            {
                "date": event_date.date().isoformat(),
                "title": record.get("title", ""),
                "ticker": record.get("ticker", ""),
                "company": record.get("company_name", ""),
                "catalyst_type": record.get("event_type", "release_event"),
                "source_type": record.get("source_type", ""),
                "source_confidence": record.get("source_confidence", ""),
                "summary": record.get("summary", ""),
            }
        )
    return results


def _build_certification_events(start: datetime, end: datetime) -> list[dict]:
    records = load_json_records(CERTIFICATIONS_DIR)
    results: list[dict] = []
    for record in records:
        signal_date = _parse_date(record.get("signal_date"))
        if signal_date is None or not (start <= signal_date <= end):
            continue
        results.append(
            {
                "date": signal_date.date().isoformat(),
                "title": record.get("title", ""),
                "ticker": record.get("ticker", ""),
                "company": record.get("company_name", ""),
                "catalyst_type": record.get("signal_type", "certification_signal"),
                "source_type": record.get("registry_name", ""),
                "source_confidence": record.get("source_confidence", ""),
                "summary": record.get("rating_or_status", ""),
            }
        )
    return results


def _build_storefront_events(start: datetime, end: datetime) -> list[dict]:
    records = load_json_records(STOREFRONT_METRICS_DIR)
    results: list[dict] = []
    for record in records:
        release_date = _parse_date(record.get("release_date"))
        if release_date is None or not (start <= release_date <= end):
            continue
        results.append(
            {
                "date": release_date.date().isoformat(),
                "title": record.get("title", ""),
                "ticker": record.get("ticker", ""),
                "company": record.get("company_name", ""),
                "catalyst_type": "storefront_release_date",
                "source_type": record.get("storefront", ""),
                "source_confidence": record.get("source_confidence", ""),
                "summary": record.get("source_url", ""),
            }
        )
    return results


def _build_sec_events(start: datetime, end: datetime) -> list[dict]:
    records = load_json_records(GAMING_SEC_CATALYSTS_DIR)
    results: list[dict] = []
    for record in records:
        record_date = _parse_date(record.get("sponsor_disclosed_target_date") or record.get("filing_date"))
        if record_date is None or not (start <= record_date <= end):
            continue
        results.append(
            {
                "date": record_date.date().isoformat(),
                "title": record.get("title", ""),
                "ticker": record.get("ticker", ""),
                "company": record.get("company_name", ""),
                "catalyst_type": record.get("catalyst_type", "sec_signal"),
                "source_type": "SEC",
                "source_confidence": record.get("source_confidence", ""),
                "summary": record.get("matched_text", ""),
            }
        )
    return results


def build_calendar(days: int, format_name: str, output_path: str | None) -> list[dict]:
    ensure_gaming_directory(OUTPUT_DIR)
    start = datetime.now()
    end = start + timedelta(days=days)

    rows = []
    rows.extend(_build_release_events(start, end))
    rows.extend(_build_certification_events(start, end))
    rows.extend(_build_storefront_events(start, end))
    rows.extend(_build_sec_events(start, end))
    rows.sort(key=lambda item: item.get("date", "9999-99-99"))

    target = Path(output_path) if output_path else OUTPUT_DIR / f"gaming_release_calendar_{days}d.{format_name}"
    if format_name == "csv":
        with target.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "date",
                    "title",
                    "ticker",
                    "company",
                    "catalyst_type",
                    "source_type",
                    "source_confidence",
                    "summary",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
    else:
        write_json(target, rows)

    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a gaming release calendar")
    parser.add_argument("--days", type=int, default=180)
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", type=str, help="Optional output path")
    args = parser.parse_args()

    rows = build_calendar(args.days, args.format, args.output)
    print(f"Built gaming release calendar with {len(rows)} rows")


if __name__ == "__main__":
    main()
