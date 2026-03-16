"""
License Tracker -- Fetch Licenses
Search the NMLS Consumer Access API for money transmitter license data.
Also check OCC charter lists for banking charter status.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.common.run_summary import write_run_summary
from super_agents.common.status import write_current_status
from super_agents.fintech.io_utils import write_json
from super_agents.fintech.paths import LICENSES_RAW_DIR, ensure_fintech_directory
from super_agents.fintech.watchlist import load_company_watchlist

load_dotenv()

NMLS_BASE = "https://www.nmlsconsumeraccess.org/api/Search"
OCC_CHARTER_URL = "https://www.occ.gov/topics/charters-and-licensing/financial-institution-lists/national-banks/national-banks-list.json"
AGENT_NAME = "fintech"
WORKFLOW_NAME = "daily_update"
TASK_NAME = "fetch_licenses"
RAW_DIR = LICENSES_RAW_DIR

USER_AGENT = os.getenv("FINTECH_USER_AGENT", "FintechTracker research@example.com")


def fetch_nmls_licenses(company: str, state: str | None = None, limit: int = 50) -> list[dict]:
    """
    Search NMLS Consumer Access for money transmitter license data.

    Args:
        company: Company name to search
        state: Optional two-letter state code filter
        limit: Maximum results to return
    """
    ensure_fintech_directory(RAW_DIR)

    params = {
        "searchText": company,
        "pageSize": limit,
    }
    if state:
        params["state"] = state.upper()

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    response = httpx.get(NMLS_BASE, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = company.replace(" ", "_")[:30]
    raw_path = RAW_DIR / f"nmls_{safe_name}_{timestamp}.json"
    write_json(raw_path, data)

    results = data.get("results", data) if isinstance(data, dict) else data
    if not isinstance(results, list):
        results = [results] if results else []

    return _transform_nmls_results(results, company)


def _transform_nmls_results(raw_results: list[dict], company: str) -> list[dict]:
    """Transform NMLS results into licensing_events format."""
    events = []
    for result in raw_results:
        licenses = result.get("licenses", [result])
        if not isinstance(licenses, list):
            licenses = [licenses]

        for lic in licenses:
            event = {
                "company_name": result.get("companyName", company),
                "nmls_id": str(result.get("nmlsId", "")),
                "license_type": "MTL",
                "state": lic.get("regulator", {}).get("state", ""),
                "status": lic.get("status", ""),
                "event_date": lic.get("statusDate", ""),
                "source_url": f"https://www.nmlsconsumeraccess.org/EntityDetails.aspx/COMPANY/{result.get('nmlsId', '')}",
                "source_type": "NMLS",
                "source_confidence": "primary",
            }
            events.append(event)

    return events


def fetch_occ_charters(company: str | None = None) -> list[dict]:
    """
    Check OCC charter list for banking charter status.

    Args:
        company: Optional company name to filter results
    """
    ensure_fintech_directory(RAW_DIR)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    response = httpx.get(OCC_CHARTER_URL, headers=headers, timeout=30, follow_redirects=True)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        raise httpx.HTTPError(
            "OCC returned a non-JSON response for the charter list; the current endpoint likely needs to be updated."
        ) from exc

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"occ_charters_{timestamp}.json"
    write_json(raw_path, data)

    results = data if isinstance(data, list) else data.get("results", [])
    events = []
    for entry in results:
        name = entry.get("bankName", entry.get("name", ""))
        if company and company.lower() not in name.lower():
            continue

        event = {
            "company_name": name,
            "license_type": "banking_charter",
            "charter_number": str(entry.get("charterNumber", "")),
            "state": entry.get("state", ""),
            "status": entry.get("status", "active"),
            "event_date": entry.get("effectiveDate", ""),
            "source_url": "https://www.occ.gov/topics/charters-and-licensing/financial-institution-lists/index-financial-institution-lists.html",
            "source_type": "OCC",
            "source_confidence": "primary",
        }
        events.append(event)

    return events


def _load_company_targets(company: str | None, batch: bool) -> list[str]:
    if company:
        return [company]
    if batch:
        return [record.company_name for record in load_company_watchlist()]
    return []


def _build_findings(records: list[dict], limit: int = 5) -> list[dict]:
    findings: list[dict] = []
    for record in records[:limit]:
        asset = record.get("company_name", "") or "fintech entity"
        license_type = record.get("license_type", "")
        findings.append(
            {
                "severity": "info",
                "asset": asset,
                "finding_type": "license_status",
                "summary": f"{asset} | {license_type} | {record.get('status', '')} | {record.get('state', '')}",
                "source_url": record.get("source_url", ""),
                "confidence": record.get("source_confidence", ""),
            }
        )
    return findings


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Fetch fintech license data")
    parser.add_argument("--company", type=str, help="Company name to search")
    parser.add_argument("--batch", action="store_true", help="Run against the seed watchlist")
    parser.add_argument("--state", type=str, default=None, help="Two-letter state code filter")
    parser.add_argument("--limit", type=int, default=50, help="Max results")
    args = parser.parse_args()

    companies = _load_company_targets(args.company, args.batch)
    if not companies:
        parser.error("Provide --company or use --batch.")

    started_at = datetime.now()
    run_id = started_at.strftime("%Y%m%d_%H%M%S")
    write_current_status(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status="running",
        input_scope=companies,
        active_source="NMLS, OCC",
        progress_completed=0,
        progress_total=len(companies),
        current_focus="Fetching fintech licensing signals",
        latest_message=f"Starting license checks for {len(companies)} company targets",
    )

    all_records: list[dict] = []
    blockers: list[str] = []
    successful_sources = 0
    companies_with_activity = 0
    completed = 0
    for company_name in companies:
        company_records: list[dict] = []

        try:
            print(f"Searching NMLS for '{company_name}'...")
            nmls_results = fetch_nmls_licenses(company_name, state=args.state, limit=args.limit)
            print(f"Found {len(nmls_results)} NMLS license records")
            for rec in nmls_results[:5]:
                print(f"  {rec['state']} | {rec['status']} | {rec['license_type']}")
            company_records.extend(nmls_results)
            successful_sources += 1
        except httpx.HTTPError as exc:
            blockers.append(f"{company_name} | NMLS: {exc}")
            print(f"License fetch failed for '{company_name}' via NMLS: {exc}")

        try:
            print(f"\nChecking OCC charters for '{company_name}'...")
            occ_results = fetch_occ_charters(company=company_name)
            print(f"Found {len(occ_results)} OCC charter records")
            for rec in occ_results[:5]:
                print(f"  {rec['charter_number']} | {rec['state']} | {rec['status']}")
            company_records.extend(occ_results)
            successful_sources += 1
        except httpx.HTTPError as exc:
            blockers.append(f"{company_name} | OCC: {exc}")
            print(f"License fetch failed for '{company_name}' via OCC: {exc}")

        all_records.extend(company_records)
        if company_records:
            companies_with_activity += 1
        completed += 1
        write_current_status(
            agent_name=AGENT_NAME,
            run_id=run_id,
            workflow_name=WORKFLOW_NAME,
            task_name=TASK_NAME,
            status="running",
            input_scope=companies,
            active_source="NMLS, OCC",
            progress_completed=completed,
            progress_total=len(companies),
            current_focus=f"Processed {company_name}",
            latest_message=f"Collected {len(all_records)} total fintech licensing records so far",
            blocker=blockers[-1] if blockers else None,
        )

    final_status = "completed" if successful_sources > 0 else "failed"
    final_message = (
        f"Collected {len(all_records)} licensing records across {len(companies)} company targets"
        if final_status == "completed"
        else "Fintech license collection failed for all requested company targets"
    )
    write_current_status(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status=final_status,
        input_scope=companies,
        active_source="NMLS, OCC",
        progress_completed=completed,
        progress_total=len(companies),
        current_focus="Fintech licensing run finished",
        latest_message=final_message,
        blocker="; ".join(blockers[:3]) if blockers else None,
    )
    write_run_summary(
        agent_name=AGENT_NAME,
        run_id=run_id,
        workflow_name=WORKFLOW_NAME,
        task_name=TASK_NAME,
        status=final_status,
        started_at=started_at,
        inputs={
            "companies": len(companies),
            "state_filters": 1 if args.state else 0,
            "request_limit": args.limit,
        },
        outputs={
            "records_written": len(all_records),
            "companies_with_activity": companies_with_activity,
            "companies_with_errors": len(blockers),
            "sources_checked": 2,
            "successful_source_requests": successful_sources,
        },
        findings=_build_findings(all_records),
        blockers=blockers,
        next_actions=[
            "Review the latest fintech licensing summary in the dashboard",
            "Follow up on companies with no current licensing signals or request errors",
        ],
    )

    if final_status == "failed":
        raise SystemExit(blockers[0] if blockers else "Fintech license collection failed.")


if __name__ == "__main__":
    main()
