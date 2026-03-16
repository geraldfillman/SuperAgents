"""
Catalyst Calendar — Build rolling catalyst calendar from all data sources.
"""

import csv
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.biotech.io_utils import load_json_records, write_json
from super_agents.biotech.paths import DASHBOARDS_DIR, PROCESSED_DIR, ensure_biotech_directory

OUTPUT_DIR = DASHBOARDS_DIR


def build_catalyst_calendar(
    days: int = 90,
    ticker: str | None = None,
    format: str = "json",
    output_path: str | None = None,
) -> list[dict]:
    """
    Build a rolling catalyst calendar by merging data from:
    - regulatory_events (PDUFA dates, submissions)
    - clinical_trials (completion dates, topline windows)
    - advisory_meetings (scheduled adcoms)
    - postmarketing (PMR deadlines)

    Args:
        days: Number of days to look ahead
        ticker: Optional ticker filter
        format: Output format ("json" or "csv")
        output_path: Optional file path for output
    """
    ensure_biotech_directory(OUTPUT_DIR)

    cutoff_date = datetime.now() + timedelta(days=days)
    today = datetime.now()

    catalysts = []

    # 1. Regulatory events (PDUFA dates, pending decisions)
    catalysts.extend(_load_regulatory_catalysts(today, cutoff_date, ticker))

    # 2. Clinical trial milestones
    catalysts.extend(_load_trial_catalysts(today, cutoff_date, ticker))

    # 3. Advisory meetings
    catalysts.extend(_load_adcom_catalysts(today, cutoff_date, ticker))

    # 4. Postmarketing deadlines
    catalysts.extend(_load_pmr_catalysts(today, cutoff_date, ticker))

    # Sort by date
    catalysts.sort(key=lambda x: x.get("date", "9999-99-99"))

    # Output
    if output_path or format == "csv":
        out = Path(output_path) if output_path else OUTPUT_DIR / f"catalyst_calendar_{days}d.csv"
        if format == "csv":
            _write_csv(catalysts, out)
        else:
            write_json(out, catalysts)
        print(f"Saved {len(catalysts)} catalysts to {out}")
    else:
        out = OUTPUT_DIR / f"catalyst_calendar_{days}d.json"
        write_json(out, catalysts)

    return catalysts


def _parse_date(value: str) -> date | None:
    """Parse supported date formats into a date object."""
    if not value:
        return None

    candidate = value.strip()
    for parser in (datetime.fromisoformat,):
        try:
            return parser(candidate).date()
        except ValueError:
            pass

    for fmt in ("%Y-%m-%d", "%Y-%m", "%B %d, %Y", "%b %d, %Y"):
        try:
            parsed = datetime.strptime(candidate, fmt)
        except ValueError:
            continue
        if fmt == "%Y-%m":
            return parsed.date().replace(day=1)
        return parsed.date()

    return None


def _is_in_window(value: str, start: datetime, end: datetime) -> bool:
    """Return True when the date falls within the requested rolling window."""
    parsed = _parse_date(value)
    if parsed is None:
        return False
    return start.date() <= parsed <= end.date()


def _load_regulatory_catalysts(start: datetime, end: datetime, ticker: str | None) -> list[dict]:
    """Load catalysts from regulatory_events data."""
    events_dir = PROCESSED_DIR / "regulatory_events"
    if not events_dir.exists():
        return []

    catalysts = []
    records = load_json_records(events_dir)
    for record in records:
        event_date = record.get("next_expected_date") or record.get("event_date", "")
        if not event_date:
            continue

        if ticker and record.get("ticker", "").upper() != ticker.upper():
            continue

        if not _is_in_window(event_date, start, end):
            continue

        catalysts.append({
            "date": _parse_date(event_date).isoformat(),
            "ticker": record.get("ticker", ""),
            "company": record.get("company_name", ""),
            "product": record.get("product_name", ""),
            "indication": record.get("indication", ""),
            "catalyst_type": record.get("event_type", "regulatory"),
            "source_confidence": record.get("source_confidence", ""),
            "official_vs_sponsor": (
                "official" if record.get("official_fda_source_present") else "sponsor"
            ),
            "next_step_after_outcome": record.get("next_expected_step", ""),
        })

    return catalysts


def _load_trial_catalysts(start: datetime, end: datetime, ticker: str | None) -> list[dict]:
    """Load catalysts from clinical_trials data (completion dates, topline windows)."""
    trials_dir = PROCESSED_DIR / "clinical_trials"
    if not trials_dir.exists():
        return []

    catalysts = []
    records = load_json_records(trials_dir)
    for record in records:
        date = record.get("estimated_primary_completion") or record.get("topline_expected_window", "")
        if not date:
            continue

        if ticker and record.get("ticker", "").upper() != ticker.upper():
            continue

        if not _is_in_window(date, start, end):
            continue

        catalysts.append({
            "date": _parse_date(date).isoformat(),
            "ticker": record.get("ticker", ""),
            "company": record.get("sponsor", ""),
            "product": record.get("product_name", ""),
            "indication": record.get("indication", ""),
            "catalyst_type": "trial_readout",
            "source_confidence": "primary",
            "official_vs_sponsor": "official",
            "next_step_after_outcome": "NDA/BLA submission if positive",
        })

    return catalysts


def _load_adcom_catalysts(start: datetime, end: datetime, ticker: str | None) -> list[dict]:
    """Load catalysts from advisory_meetings data."""
    adcom_dir = PROCESSED_DIR / "advisory_meetings"
    if not adcom_dir.exists():
        return []
    return []  # TODO: Implement adcom catalyst loading when advisory meeting data is ingested


def _load_pmr_catalysts(start: datetime, end: datetime, ticker: str | None) -> list[dict]:
    """Load catalysts from postmarketing deadlines."""
    pmr_dir = PROCESSED_DIR / "postmarketing"
    if not pmr_dir.exists():
        return []
    return []  # TODO: Implement PMR catalyst loading when postmarketing data is ingested


def _write_csv(catalysts: list[dict], path: Path) -> None:
    """Write catalysts to CSV."""
    if not catalysts:
        return

    fieldnames = [
        "date", "ticker", "company", "product", "indication",
        "catalyst_type", "source_confidence", "official_vs_sponsor",
        "next_step_after_outcome",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(catalysts)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build rolling catalyst calendar")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--ticker", type=str, help="Filter by ticker")
    parser.add_argument("--format", choices=["json", "csv"], default="json")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()

    results = build_catalyst_calendar(
        days=args.days,
        ticker=args.ticker,
        format=args.format,
        output_path=args.output,
    )
    print(f"Built calendar with {len(results)} catalysts over next {args.days} days")
