"""
Company Screener — Discover new biotech/pharma/medtech companies.
"""

import os
import json
import httpx
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/screener")
PROCESSED_DIR = Path("data/processed/screener")

SEC_EDGAR_USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "BiotechTracker research@example.com")

# SIC codes relevant to biotech/pharma/medtech
RELEVANT_SIC_CODES = {
    "2833": "Pharmaceutical Preparations",
    "2834": "Pharmaceutical Preparations",
    "2835": "In Vitro & In Vivo Diagnostic Substances",
    "2836": "Biological Products (No Diagnostic Substances)",
    "3841": "Surgical & Medical Instruments & Apparatus",
    "3842": "Orthopedic, Prosthetic & Surgical Supplies",
    "3844": "X-Ray Apparatus & Tubes",
    "3845": "Electromedical & Electrotherapeutic Apparatus",
    "3851": "Ophthalmic Goods",
    "5047": "Medical & Hospital Equipment & Supplies",
    "8071": "Health Services",
    "8731": "Commercial Physical & Biological Research",
    "8734": "Testing Laboratories",
}

MARKET_CAP_BUCKETS = {
    "nano": (0, 50_000_000),
    "micro": (50_000_000, 300_000_000),
    "small": (300_000_000, 2_000_000_000),
    "mid": (2_000_000_000, 10_000_000_000),
}


def screen_companies(
    sic_codes: list[str] | None = None,
    max_market_cap: str | None = None,
) -> list[dict]:
    """
    Screen SEC EDGAR for biotech/pharma/medtech companies.

    Args:
        sic_codes: Optional specific SIC codes to search
        max_market_cap: Max market cap bucket ("nano", "micro", "small", "mid")
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if sic_codes is None:
        sic_codes = list(RELEVANT_SIC_CODES.keys())

    companies = []

    for sic in sic_codes:
        url = f"https://efts.sec.gov/LATEST/search-index?q=%22{sic}%22&dateRange=custom&startdt=&enddt="
        headers = {"User-Agent": SEC_EDGAR_USER_AGENT}

        try:
            response = httpx.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", {}).get("hits", [])
                for hit in hits:
                    source = hit.get("_source", {})
                    companies.append({
                        "company_name": source.get("display_names", [""])[0] if source.get("display_names") else "",
                        "cik": source.get("entity_id", ""),
                        "sic_code": sic,
                        "sic_description": RELEVANT_SIC_CODES.get(sic, ""),
                        "filing_date": source.get("file_date", ""),
                        "form_type": source.get("form_type", ""),
                    })
        except httpx.RequestError:
            continue

    # Deduplicate by CIK
    seen_ciks = set()
    unique_companies = []
    for c in companies:
        cik = c.get("cik", "")
        if cik and cik not in seen_ciks:
            seen_ciks.add(cik)
            unique_companies.append(c)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = PROCESSED_DIR / f"screened_companies_{timestamp}.json"
    out_path.write_text(json.dumps(unique_companies, indent=2))

    return unique_companies


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Screen for biotech/pharma companies")
    parser.add_argument("--sic", nargs="+", help="Specific SIC codes to search")
    parser.add_argument("--max-market-cap", choices=["nano", "micro", "small", "mid"])
    args = parser.parse_args()

    results = screen_companies(sic_codes=args.sic, max_market_cap=args.max_market_cap)
    print(f"Found {len(results)} unique companies")
    for c in results[:10]:
        print(f"  {c['company_name']} | CIK: {c['cik']} | {c['sic_description']}")
