"""
Permit Tracker -- Fetch Mining Permits from Federal Register
Query the Federal Register API for BLM/NEPA/EPA documents related to
mining permits, environmental impact statements, and records of decision.
"""

import os
import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Constants
BASE_URL = "https://www.federalregister.gov/api/v1/documents.json"
RAW_DIR = Path("data/raw/rare_earth/permits")

# Search terms for mining-related federal register documents
MINING_SEARCH_TERMS = [
    "mining permit",
    "record of decision mine",
    "environmental impact statement mining",
    "draft environmental impact statement mine",
    "Bureau of Land Management mine",
    "critical minerals",
    "rare earth",
    "lithium mine",
    "cobalt mine",
    "nickel mine",
]

AGENCIES = [
    "bureau-of-land-management",
    "environmental-protection-agency",
    "forest-service",
    "army-corps-of-engineers",
]


def fetch_permits(days: int = 30, limit: int = 100) -> list[dict]:
    """
    Fetch mining permit documents from the Federal Register API.

    Args:
        days: Number of days to look back.
        limit: Maximum number of results to return.

    Returns:
        List of permit event records with source metadata.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")

    all_results = []

    for term in MINING_SEARCH_TERMS:
        params = {
            "conditions[term]": term,
            "conditions[publication_date][gte]": start_date,
            "conditions[publication_date][lte]": end_date,
            "per_page": min(limit, 50),
            "order": "newest",
            "fields[]": [
                "title",
                "abstract",
                "document_number",
                "publication_date",
                "agencies",
                "type",
                "html_url",
                "pdf_url",
            ],
        }

        try:
            response = httpx.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            all_results.extend(results)

        except httpx.HTTPError as exc:
            print(f"Error fetching term '{term}': {exc}")
            continue

        if len(all_results) >= limit:
            break

    # Deduplicate by document number
    seen = set()
    unique_results = []
    for doc in all_results:
        doc_num = doc.get("document_number", "")
        if doc_num and doc_num not in seen:
            seen.add(doc_num)
            unique_results.append(doc)

    unique_results = unique_results[:limit]

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"federal_register_{timestamp}.json"
    raw_path.write_text(json.dumps(unique_results, indent=2))

    # Transform to standard format
    transformed = _transform(unique_results)

    # Save transformed
    processed_path = RAW_DIR / f"permits_processed_{timestamp}.json"
    processed_path.write_text(json.dumps(transformed, indent=2))

    return transformed


def _transform(raw: list[dict]) -> list[dict]:
    """Transform raw Federal Register results to standard schema format."""
    records = []
    for doc in raw:
        agencies = doc.get("agencies", [])
        agency_names = [a.get("name", "") for a in agencies] if agencies else []

        permit_type = _classify_permit_type(
            doc.get("title", ""),
            doc.get("abstract", ""),
            doc.get("type", ""),
        )

        records.append({
            "document_number": doc.get("document_number", ""),
            "title": doc.get("title", ""),
            "abstract": doc.get("abstract", ""),
            "publication_date": doc.get("publication_date", ""),
            "document_type": doc.get("type", ""),
            "agencies": agency_names,
            "permit_type": permit_type,
            "source_url": doc.get("html_url", ""),
            "pdf_url": doc.get("pdf_url", ""),
            "source_type": "Federal Register",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        })
    return records


def _classify_permit_type(title: str, abstract: str, doc_type: str) -> str:
    """Classify the permit type based on document text."""
    text = (title + " " + (abstract or "")).lower()
    if "record of decision" in text:
        return "ROD"
    if "draft environmental impact" in text:
        return "DEIS"
    if "final environmental impact" in text or "environmental impact statement" in text:
        return "EIS"
    if "water" in text and ("permit" in text or "discharge" in text):
        return "water"
    if "air quality" in text or "air permit" in text:
        return "air"
    if "notice of intent" in text:
        return "NOI"
    return "other"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch mining permit documents from the Federal Register"
    )
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=100, help="Maximum results")
    args = parser.parse_args()

    results = fetch_permits(days=args.days, limit=args.limit)
    print(f"Found {len(results)} permit documents")
    for r in results[:5]:
        print(f"  [{r['publication_date']}] {r['permit_type']} - {r['title'][:80]}")
