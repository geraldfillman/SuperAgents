"""Shared source validation — extracted from duplicated validate_sources.py scripts.

Previously copy-pasted across:
  - .agent_biotech/skills/data_quality/scripts/validate_sources.py
  - .agent_gaming/skills/data_quality/scripts/validate_sources.py
  - .agent_rare_earth/skills/data_quality/scripts/validate_sources.py

Now a single module that any agent can call with its own data directory.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .confidence import REQUIRED_SOURCE_FIELDS, SourceConfidence, validate_source_fields
from .http_client import head_check
from .io_utils import load_json_records, write_json

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------

def _empty_report() -> dict[str, Any]:
    """Create a fresh validation report skeleton."""
    return {
        "validated_at": datetime.now().isoformat(),
        "summary": {
            "tables_scanned": 0,
            "records_scanned": 0,
            "missing_source_url": 0,
            "missing_source_type": 0,
            "missing_source_confidence": 0,
            "invalid_source_confidence": 0,
            "sponsor_only_unverified": 0,
            "broken_urls": 0,
        },
        "issues": [],
    }


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def validate_sources(
    data_dir: Path,
    *,
    check_urls: bool = False,
    check_fda_flag: bool = False,
    reports_dir: Path | None = None,
) -> dict[str, Any]:
    """Validate source integrity across all JSON tables in a data directory.

    Checks every record for:
    - Missing source_url, source_type, source_confidence
    - Invalid source_confidence values
    - Sponsor-only records without external corroboration
    - Optionally: broken URLs via HEAD requests
    - Optionally: missing official_fda_source_present (biotech-specific)

    Args:
        data_dir: Root directory containing subdirectories of JSON records.
        check_urls: If True, verify URLs via HTTP HEAD (slower).
        check_fda_flag: If True, check for missing official_fda_source_present
                        on records that have source_type == 'filing'.
        reports_dir: Where to write the report. Defaults to data_dir/quality_reports.

    Returns:
        The validation report dict.
    """
    if reports_dir is None:
        reports_dir = data_dir / "quality_reports"

    report = _empty_report()

    if not data_dir.exists():
        logger.warning("Data directory does not exist: %s", data_dir)
        return report

    # Scan each subdirectory as a "table"
    for table_dir in sorted(data_dir.iterdir()):
        if not table_dir.is_dir():
            continue
        if table_dir.name.startswith(".") or table_dir.name == "quality_reports":
            continue

        table_name = table_dir.name
        records = load_json_records(table_dir)
        if not records:
            continue

        report["summary"]["tables_scanned"] += 1
        report["summary"]["records_scanned"] += len(records)

        for record in records:
            identifier = _record_identifier(record)
            issues = validate_source_fields(record)

            for issue in issues:
                category = issue.split(":")[0].strip()
                report["summary"][category] = report["summary"].get(category, 0) + 1
                report["issues"].append({
                    "type": category,
                    "table": table_name,
                    "identifier": identifier,
                    "detail": issue,
                })

            # Sponsor-only without corroboration
            if (
                record.get("source_confidence") == SourceConfidence.SPONSOR.value
                and not record.get("corroborated", False)
            ):
                report["summary"]["sponsor_only_unverified"] += 1
                report["issues"].append({
                    "type": "sponsor_only_unverified",
                    "table": table_name,
                    "identifier": identifier,
                    "detail": "Sponsor-only source without external corroboration",
                })

            # Biotech-specific: FDA flag check
            if check_fda_flag and not record.get("official_fda_source_present"):
                if record.get("source_type") == "filing" or "fda" in table_name.lower():
                    report["summary"]["missing_fda_flag"] = report["summary"].get("missing_fda_flag", 0) + 1
                    report["issues"].append({
                        "type": "missing_fda_flag",
                        "table": table_name,
                        "identifier": identifier,
                        "detail": "Missing official_fda_source_present flag",
                    })

            # URL validity check
            if check_urls and record.get("source_url"):
                reachable, status = head_check(record["source_url"])
                if not reachable:
                    report["summary"]["broken_urls"] += 1
                    report["issues"].append({
                        "type": "broken_url",
                        "table": table_name,
                        "identifier": identifier,
                        "url": record["source_url"],
                        "status_code": status,
                    })

    # Write report
    reports_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = reports_dir / f"source_validation_{timestamp}.json"
    write_json(report_path, report)

    logger.info(
        "Validation complete: %d tables, %d records, %d issues",
        report["summary"]["tables_scanned"],
        report["summary"]["records_scanned"],
        len(report["issues"]),
    )

    return report


def print_report(report: dict[str, Any]) -> None:
    """Print a human-readable validation report to stdout."""
    summary = report["summary"]
    print("Source Validation Report")
    print(f"  Tables scanned:            {summary['tables_scanned']}")
    print(f"  Records scanned:           {summary['records_scanned']}")
    print(f"  Missing source URLs:       {summary['missing_source_url']}")
    print(f"  Missing source type:       {summary.get('missing_source_type', 0)}")
    print(f"  Missing source confidence: {summary.get('missing_source_confidence', 0)}")
    print(f"  Invalid confidence values: {summary.get('invalid_source_confidence', 0)}")
    print(f"  Sponsor-only unverified:   {summary['sponsor_only_unverified']}")
    if "missing_fda_flag" in summary:
        print(f"  Missing FDA flag:          {summary['missing_fda_flag']}")
    if summary.get("broken_urls"):
        print(f"  Broken URLs:               {summary['broken_urls']}")
    print(f"  Total issues:              {len(report['issues'])}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_identifier(record: dict[str, Any]) -> str:
    """Extract a human-readable identifier from a record."""
    for key in ("ticker", "company_name", "product_name", "asset_name", "title", "name", "id"):
        value = record.get(key)
        if value:
            return str(value)
    return "unknown"
