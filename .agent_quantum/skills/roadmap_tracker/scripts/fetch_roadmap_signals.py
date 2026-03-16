"""
Roadmap Tracker -- Fetch Roadmap Signals
Search SEC EDGAR for 10-K/8-K filings with quantum roadmap language
(qubit count targets, error correction milestones, system release timelines).
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/quantum/roadmap")
EDGAR_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "QuantumTracker research@example.com")

ROADMAP_KEYWORDS = [
    "qubit roadmap",
    "quantum roadmap",
    "error correction milestone",
    "logical qubit target",
    "quantum advantage timeline",
    "quantum-centric supercomputing",
    "fault-tolerant quantum",
    "qubit count target",
    "quantum processor generation",
    "quantum system release",
]


def fetch_roadmap_signals(cik: str = "", days: int = 30) -> list[dict]:
    """
    Search SEC EDGAR EFTS for filings containing quantum roadmap language.

    Args:
        cik: Optional CIK filter for a specific company.
        days: Lookback window in days.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    headers = {"User-Agent": USER_AGENT}

    results = []
    for keyword in ROADMAP_KEYWORDS:
        params = {
            "q": f'"{keyword}"',
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "forms": "8-K,10-K,10-Q,S-1,20-F",
        }

        if cik:
            params["q"] = f'"{keyword}" AND entityId:"{cik}"'

        try:
            response = httpx.get(
                EDGAR_EFTS_BASE, params=params, headers=headers, timeout=30
            )
            response.raise_for_status()
            hits = response.json().get("hits", {}).get("hits", [])
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            print(f"EDGAR search failed for '{keyword}': {exc}")
            continue

        for hit in hits:
            source_data = hit.get("_source", {})
            entity_id = source_data.get("entity_id", "")
            record = {
                "roadmap_keyword": keyword,
                "company_name": source_data.get("display_names", [""])[0],
                "cik": entity_id,
                "filing_type": source_data.get("form_type", ""),
                "filing_date": source_data.get("file_date", ""),
                "file_num": source_data.get("file_num", ""),
                "source_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={entity_id}&type=&dateb=&owner=include&count=40",
                "source_type": "SEC",
                "source_confidence": "secondary",
                "fetched_at": datetime.now().isoformat(),
            }
            results.append(record)

    # Deduplicate by filing
    seen = set()
    unique_results = []
    for r in results:
        key = (r["cik"], r["filing_date"], r["filing_type"])
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    return unique_results


def run(cik: str = "", days: int = 30) -> None:
    """Fetch roadmap signals and save to disk."""
    results = fetch_roadmap_signals(cik=cik, days=days)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if results:
        out_path = RAW_DIR / f"roadmap_signals_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Saved {len(results)} roadmap signal records to {out_path}")
        for r in results[:10]:
            print(f"  [{r['filing_date']}] {r['company_name']} ({r['filing_type']}): {r['roadmap_keyword']}")
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more.")
    else:
        print("No roadmap signals found.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch quantum roadmap signals from SEC EDGAR")
    parser.add_argument("--cik", type=str, default="", help="Company CIK number (optional)")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days")
    args = parser.parse_args()

    run(cik=args.cik, days=args.days)
