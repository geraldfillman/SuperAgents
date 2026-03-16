"""
Partnership Tracker -- Fetch Partnerships
Search SEC EDGAR for 8-K filings mentioning partnership or collaboration
announcements for fintech companies.
"""

import json
import os
import sys
import httpx
import re
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from super_agents.fintech.io_utils import write_json
from super_agents.fintech.paths import PARTNERSHIPS_RAW_DIR, ensure_fintech_directory

load_dotenv()

EDGAR_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
RAW_DIR = PARTNERSHIPS_RAW_DIR

USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "FintechTracker research@example.com")

PARTNERSHIP_KEYWORDS = [
    r"(?:strategic\s+)?partnership\s+(?:agreement|with)",
    r"collaboration\s+agreement",
    r"distribution\s+agreement",
    r"white[\s-]?label\s+agreement",
    r"(?:banking|payments?)\s+as\s+a\s+service",
    r"co[\s-]?brand(?:ed|ing)\s+(?:card|agreement|partnership)",
    r"technology\s+(?:licensing|partnership|integration)\s+agreement",
    r"merchant\s+(?:acquiring|processing)\s+agreement",
    r"referral\s+(?:agreement|partnership)",
]


def fetch_partnership_filings(cik: str, days: int = 30) -> list[dict]:
    """
    Fetch 8-K filings from EDGAR and extract partnership mentions.

    Args:
        cik: SEC CIK number
        days: Look back N days for recent 8-Ks
    """
    ensure_fintech_directory(RAW_DIR)

    cik_padded = cik.zfill(10)
    cik_unpadded = cik.lstrip("0") or "0"
    url = f"{EDGAR_SUBMISSIONS_BASE}/CIK{cik_padded}.json"
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    response = httpx.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    # Save raw submission index
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = RAW_DIR / f"submissions_{cik_padded}_{timestamp}.json"
    write_json(raw_path, data)

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    ticker = ",".join(data.get("tickers", []))
    company_name = data.get("name", "")

    partnerships = []
    for i, form_type in enumerate(forms):
        if form_type != "8-K":
            continue

        filing_date = dates[i] if i < len(dates) else ""
        if filing_date < cutoff:
            continue

        accession = accessions[i].replace("-", "") if i < len(accessions) else ""
        doc = primary_docs[i] if i < len(primary_docs) else ""
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{doc}"

        # Download and check for partnership keywords
        try:
            text_resp = httpx.get(filing_url, headers=headers, timeout=60, follow_redirects=True)
            text_resp.raise_for_status()
            raw_text = text_resp.text
        except httpx.HTTPError:
            continue

        parser = "xml" if raw_text.lstrip().startswith("<?xml") else "lxml"
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
            soup = BeautifulSoup(raw_text, parser)
        clean_text = soup.get_text(separator=" ", strip=True)

        for pattern in PARTNERSHIP_KEYWORDS:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                # Extract context around the match
                start = max(0, match.start() - 200)
                end = min(len(clean_text), match.end() + 200)
                context = clean_text[start:end].strip()

                # Try to identify partner name from context
                partner_match = re.search(
                    r"(?:with|and)\s+([A-Z][A-Za-z\s&,.]+?)(?:\s+to\s+|\s+for\s+|\s+that\s+|,|\.|$)",
                    context,
                )
                partner_name = partner_match.group(1).strip() if partner_match else "UNKNOWN"

                partnership = {
                    "cik": cik_padded,
                    "ticker": ticker,
                    "company_name": company_name,
                    "partner_name": partner_name,
                    "partnership_type": _classify_partnership(match.group(0)),
                    "matched_text": match.group(0),
                    "context": context,
                    "announced_date": filing_date,
                    "form_type": form_type,
                    "source_url": filing_url,
                    "source_type": "SEC",
                    "source_confidence": "secondary",
                    "extracted_at": datetime.now().isoformat(),
                }
                partnerships.append(partnership)
                break  # One match per filing is sufficient

    # Save extracted partnerships
    if partnerships:
        out_path = RAW_DIR / f"partnerships_{cik_padded}_{timestamp}.json"
        write_json(out_path, partnerships)

    return partnerships


def _classify_partnership(matched_text: str) -> str:
    """Classify partnership type based on matched text."""
    text_lower = matched_text.lower()
    if "white" in text_lower and "label" in text_lower:
        return "white_label"
    if "co" in text_lower and "brand" in text_lower:
        return "co_brand"
    if "distribution" in text_lower:
        return "distribution"
    if "technology" in text_lower or "integration" in text_lower:
        return "technology"
    if "banking" in text_lower and "service" in text_lower:
        return "banking_as_a_service"
    if "merchant" in text_lower:
        return "distribution"
    if "referral" in text_lower:
        return "distribution"
    return "strategic"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch partnership announcements from 8-K filings")
    parser.add_argument("--cik", type=str, required=True, help="Company CIK number")
    parser.add_argument("--days", type=int, default=30, help="Look back N days")
    args = parser.parse_args()

    results = fetch_partnership_filings(cik=args.cik, days=args.days)
    print(f"Found {len(results)} partnership mentions for CIK {args.cik}")
    for p in results[:10]:
        print(f"  {p['announced_date']} | {p['partnership_type']} | {p['partner_name']}")
