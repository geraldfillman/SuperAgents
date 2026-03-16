"""
Adoption Monitor -- Fetch Adoption Metrics
Search SEC EDGAR EFTS for 10-Q/10-K filings with TPV, active user,
revenue run rate, and merchant count disclosures.
"""

import json
import os
import sys
import httpx
import re
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.fintech.io_utils import write_json
from super_agents.fintech.paths import ADOPTION_RAW_DIR, ensure_fintech_directory

load_dotenv()

EDGAR_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
EDGAR_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
RAW_DIR = ADOPTION_RAW_DIR

USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "FintechTracker research@example.com")

# Patterns for extracting adoption metrics from filing text
ADOPTION_PATTERNS = {
    "tpv": [
        r"total\s+payment\s+volume\s*(?:of|was|reached|grew\s+to)?\s*\$?([\d,.]+)\s*(billion|million|B|M)",
        r"TPV\s*(?:of|was|reached|grew\s+to)?\s*\$?([\d,.]+)\s*(billion|million|B|M)",
    ],
    "active_users": [
        r"([\d,.]+)\s*(million|M)?\s*(?:monthly\s+)?active\s+(?:users|accounts|customers)",
        r"active\s+(?:users|accounts|customers)\s*(?:of|reached|grew\s+to)?\s*([\d,.]+)\s*(million|M)?",
    ],
    "revenue_run_rate": [
        r"(?:revenue|net\s+revenue)\s*(?:of|was|reached)?\s*\$?([\d,.]+)\s*(billion|million|B|M)",
        r"annualized\s+(?:revenue|run\s+rate)\s*(?:of|was)?\s*\$?([\d,.]+)\s*(billion|million|B|M)",
    ],
    "merchant_count": [
        r"([\d,.]+)\s*(million|M|thousand|K)?\s*(?:active\s+)?merchants",
        r"merchant\s+(?:base|count)\s*(?:of|reached|grew\s+to)?\s*([\d,.]+)\s*(million|M|thousand|K)?",
    ],
}


def fetch_adoption_from_filings(cik: str, limit: int = 5) -> list[dict]:
    """
    Fetch 10-Q/10-K filings from EDGAR and extract adoption metric disclosures.

    Args:
        cik: SEC CIK number
        limit: Maximum filings to inspect
    """
    ensure_fintech_directory(RAW_DIR)

    cik_padded = cik.zfill(10)
    url = f"{EDGAR_SUBMISSIONS_BASE}/CIK{cik_padded}.json"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw response
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"submissions_{cik_padded}_{timestamp}.json"
    write_json(raw_path, data)

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    cik_unpadded = cik.lstrip("0") or "0"
    ticker = ",".join(data.get("tickers", []))
    company_name = data.get("name", "")

    metrics = []
    inspected = 0
    for i, form_type in enumerate(forms):
        if form_type not in ("10-Q", "10-K"):
            continue
        if inspected >= limit:
            break
        inspected += 1

        accession = accessions[i].replace("-", "") if i < len(accessions) else ""
        doc = primary_docs[i] if i < len(primary_docs) else ""
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{doc}"
        filing_date = dates[i] if i < len(dates) else ""

        # Attempt to download and parse filing text
        try:
            text_resp = httpx.get(filing_url, headers=headers, timeout=60, follow_redirects=True)
            text_resp.raise_for_status()
            filing_text = text_resp.text
        except httpx.HTTPError:
            continue

        # Extract metrics from filing text
        for metric_type, patterns in ADOPTION_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, filing_text, re.IGNORECASE)
                for match in matches:
                    raw_value = match.group(1).replace(",", "")
                    try:
                        value = float(raw_value)
                    except ValueError:
                        continue

                    metric = {
                        "cik": cik_padded,
                        "ticker": ticker,
                        "company_name": company_name,
                        "metric_type": metric_type,
                        "raw_value": match.group(0),
                        "value": value,
                        "period": filing_date[:7] if filing_date else "",
                        "form_type": form_type,
                        "filing_date": filing_date,
                        "source_url": filing_url,
                        "source_type": "SEC",
                        "source_confidence": "secondary",
                        "extracted_at": datetime.now().isoformat(),
                    }
                    metrics.append(metric)
                    break  # One match per pattern per filing is sufficient

    # Save extracted metrics
    if metrics:
        out_path = RAW_DIR / f"adoption_{cik_padded}_{timestamp}.json"
        write_json(out_path, metrics)

    return metrics


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch adoption metrics from SEC filings")
    parser.add_argument("--cik", type=str, required=True, help="Company CIK number")
    parser.add_argument("--limit", type=int, default=5, help="Max filings to inspect")
    args = parser.parse_args()

    results = fetch_adoption_from_filings(cik=args.cik, limit=args.limit)
    print(f"Extracted {len(results)} adoption metric records for CIK {args.cik}")
    for m in results[:10]:
        print(f"  {m['filing_date']} | {m['metric_type']} | {m['raw_value']}")
