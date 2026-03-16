"""
Data Quality -- Audit Stale Records
Scan tables for records with no updates in 90+ days.
Adapted for rare earth and critical minerals data directories.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path("data/processed/rare_earth")
REPORTS_DIR = Path("data/processed/rare_earth/quality_reports")


def audit_stale_records(
    stale_threshold_days: int = 90,
    tables: list[str] | None = None,
) -> dict:
    """
    Scan processed data for stale records.

    Returns a report with staleness severity and recommended actions.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if tables is None:
        tables = [
            "permits",
            "resource_estimates",
            "offtake",
            "dpa_awards",
            "catalysts",
            "financials",
            "insider_trades",
            "scores",
        ]

    now = datetime.now()
    report = {
        "audit_date": now.isoformat(),
        "stale_threshold_days": stale_threshold_days,
        "tables_scanned": [],
        "total_stale": 0,
        "stale_records": [],
    }

    for table in tables:
        table_dir = DATA_DIR / table
        if not table_dir.exists():
            continue

        table_report = {"table": table, "total_records": 0, "stale_count": 0}

        for f in table_dir.glob("*.json"):
            table_report["total_records"] += 1

            # Check file modification time as proxy for last update
            mod_time = datetime.fromtimestamp(f.stat().st_mtime)
            days_old = (now - mod_time).days

            if days_old >= stale_threshold_days:
                severity = _classify_staleness(days_old)

                try:
                    data = json.loads(f.read_text())
                    identifier = (
                        data.get("project_id")
                        or data.get("permit_id")
                        or data.get("award_id")
                        or data.get("estimate_id")
                        or f.stem
                    )
                except (json.JSONDecodeError, AttributeError):
                    identifier = f.stem

                stale_record = {
                    "table": table,
                    "file": str(f),
                    "identifier": identifier,
                    "last_updated": mod_time.isoformat(),
                    "days_stale": days_old,
                    "severity": severity,
                    "recommended_action": _recommend_action(severity),
                }
                report["stale_records"].append(stale_record)
                table_report["stale_count"] += 1

        report["tables_scanned"].append(table_report)

    report["total_stale"] = len(report["stale_records"])

    # Save report
    report_path = REPORTS_DIR / f"stale_audit_{now.strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, indent=2))

    return report


def _classify_staleness(days: int) -> str:
    if days >= 180:
        return "critical"
    elif days >= 120:
        return "high"
    else:
        return "moderate"


def _recommend_action(severity: str) -> str:
    actions = {
        "critical": "Review for archival or discontinuation. Verify if project is still active.",
        "high": "Re-verify against primary sources. Update or flag as uncertain.",
        "moderate": "Schedule verification. Check for recent permit or filing updates.",
    }
    return actions.get(severity, "Review manually.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Audit stale records")
    parser.add_argument("--days", type=int, default=90, help="Staleness threshold in days")
    args = parser.parse_args()

    report = audit_stale_records(stale_threshold_days=args.days)
    print(f"Stale Record Audit ({args.days}+ days)")
    print(f"Total stale: {report['total_stale']}")
    for table in report["tables_scanned"]:
        print(f"  {table['table']}: {table['stale_count']}/{table['total_records']} stale")
