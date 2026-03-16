"""
Resource Estimate Parser -- Fetch NI 43-101 and S-K 1300 Technical Reports
Query SEC EDGAR EFTS for technical reports containing mineral resource
estimates filed under NI 43-101 or S-K 1300 standards.
"""

import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Constants
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
RAW_DIR = Path("data/raw/rare_earth/resource_estimates")

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "RareEarthTracker research@example.com",
)

SEARCH_QUERIES = [
    '"NI 43-101" technical report',
    '"S-K 1300" technical report',
    '"mineral resource estimate"',
    '"measured and indicated" mineral',
    '"preliminary economic assessment"',
    '"pre-feasibility study"',
    '"definitive feasibility study"',
]


def fetch_resource_estimates(cik: str | None = None, limit: int = 100) -> list[dict]:
    """
    Search SEC EDGAR for NI 43-101 and S-K 1300 technical reports.

    Args:
        cik: Optional CIK to filter by company. If None, searches broadly.
        limit: Maximum number of results to return.

    Returns:
        List of resource estimate filing records with source metadata.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    all_results = []

    for query in SEARCH_QUERIES:
        params = {
            "q": query,
            "dateRange": "custom",
            "startdt": "2020-01-01",
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }

        if cik:
            params["ciks"] = cik

        try:
            response = httpx.get(
                EDGAR_SEARCH_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            all_results.extend(hits)
        except httpx.HTTPError as exc:
            print(f"Error searching for '{query}': {exc}")
            continue

        if len(all_results) >= limit:
            break

    # Deduplicate by accession number
    seen = set()
    unique = []
    for hit in all_results:
        source = hit.get("_source", {})
        accession = source.get("file_num", "") or source.get("accession_no", "")
        if accession and accession not in seen:
            seen.add(accession)
            unique.append(hit)

    unique = unique[:limit]

    # Save raw
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"edgar_search_{timestamp}.json"
    raw_path.write_text(json.dumps(unique, indent=2))

    # Transform
    transformed = _transform(unique)

    processed_path = RAW_DIR / f"estimates_processed_{timestamp}.json"
    processed_path.write_text(json.dumps(transformed, indent=2))

    return transformed


def _transform(raw: list[dict]) -> list[dict]:
    """Transform raw EDGAR search results to standard schema format."""
    records = []
    for hit in raw:
        source = hit.get("_source", {})

        report_type = _classify_report_type(
            source.get("form_type", ""),
            str(source.get("file_description", "")),
        )

        filing_url = ""
        accession = source.get("accession_no", "")
        entity_id = source.get("entity_id", "")
        if accession and entity_id:
            clean_accession = accession.replace("-", "")
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/"
                f"{entity_id}/{clean_accession}"
            )

        records.append({
            "accession_number": accession,
            "entity_name": source.get("entity_name", ""),
            "entity_id": entity_id,
            "form_type": source.get("form_type", ""),
            "filing_date": source.get("file_date", ""),
            "report_type": report_type,
            "description": source.get("file_description", ""),
            "source_url": filing_url,
            "source_type": "SEC",
            "source_confidence": "secondary",
            "fetched_at": datetime.now().isoformat(),
        })
    return records


def _classify_report_type(form_type: str, description: str) -> str:
    """Classify what kind of technical report this is."""
    text = (form_type + " " + description).lower()
    if "43-101" in text:
        return "NI_43_101"
    if "1300" in text or "s-k 1300" in text:
        return "S-K_1300"
    if "jorc" in text:
        return "JORC"
    if "feasibility" in text:
        return "feasibility_study"
    if "pea" in text or "preliminary economic" in text:
        return "PEA"
    return "technical_report"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch NI 43-101 and S-K 1300 technical reports from EDGAR"
    )
    parser.add_argument("--cik", type=str, default=None, help="Company CIK number")
    parser.add_argument("--limit", type=int, default=100, help="Maximum results")
    args = parser.parse_args()

    results = fetch_resource_estimates(cik=args.cik, limit=args.limit)
    print(f"Found {len(results)} resource estimate filings")
    for r in results[:5]:
        print(f"  [{r['filing_date']}] {r['report_type']} - {r['entity_name']}")
