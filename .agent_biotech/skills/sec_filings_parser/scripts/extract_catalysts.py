"""
SEC Filings Parser — Extract Catalysts
Parse 8-K, 10-Q, 10-K filing text to extract regulatory catalyst disclosures.
"""

import re
import json
import os
import sys
import warnings
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

RAW_METADATA_DIR = Path("data/raw/sec")
RAW_DIR = Path("data/raw/sec/filings_text")
PROCESSED_DIR = Path("data/processed/sec_catalysts")

USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "BiotechTracker research@example.com")

# Regulatory keywords to search for in filings
CATALYST_PATTERNS = {
    "pdufa_date": [
        r"PDUFA\s+(?:target\s+)?(?:action\s+)?date\s*(?:of|is|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})",
        r"action\s+date\s*(?:of|is|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})",
    ],
    "nda_bla_submission": [
        r"(?:submitted|filed|submit)\s+(?:a\s+)?(?:new\s+drug\s+application|NDA|BLA|biologics?\s+license)",
        r"(?:NDA|BLA)\s+(?:has been\s+)?(?:accepted|filed|submitted)",
    ],
    "complete_response_letter": [
        r"complete\s+response\s+letter",
        r"CRL\s+(?:from|received|issued)",
    ],
    "trial_data": [
        r"(?:topline|top-line|interim|preliminary)\s+(?:data|results)",
        r"(?:primary|secondary)\s+endpoint\s+(?:met|achieved|missed|failed)",
    ],
    "fda_approval": [
        r"FDA\s+(?:has\s+)?(?:approved|granted\s+approval)",
        r"received\s+(?:FDA\s+)?approval",
    ],
    "designation": [
        r"(?:fast\s+track|breakthrough\s+therapy|orphan\s+drug|priority\s+review)\s+designation",
        r"accelerated\s+approval\s+pathway",
    ],
    "partnership": [
        r"(?:license|licensing|collaboration|partnership)\s+agreement",
        r"milestone\s+payment",
    ],
}


from super_agents.common.cik import normalize_cik  # noqa: E402 — centralized CIK util


def _cached_sec_files() -> list[Path]:
    """Return the latest SEC submissions cache file for each company."""
    if not RAW_METADATA_DIR.exists():
        return []

    latest_by_cik: dict[str, Path] = {}
    for path in RAW_METADATA_DIR.glob("filings_*.json"):
        data = json.loads(path.read_text())
        _, cik_padded = normalize_cik(str(data.get("cik", "")))
        previous = latest_by_cik.get(cik_padded)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            latest_by_cik[cik_padded] = path

    return sorted(latest_by_cik.values(), key=lambda path: path.stat().st_mtime)


def load_cached_filings(
    filing_types: list[str] | None = None,
    limit_per_company: int = 10,
) -> list[dict]:
    """Load filing metadata from the latest cached SEC submissions per company."""
    filings: list[dict] = []
    filing_types = filing_types or ["8-K", "10-Q", "10-K"]

    for path in _cached_sec_files():
        data = json.loads(path.read_text())
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        cik_unpadded, cik_padded = normalize_cik(str(data.get("cik", "")))

        company_filings = 0
        for i, form_type in enumerate(forms):
            if filing_types and form_type not in filing_types:
                continue

            if company_filings >= limit_per_company:
                break

            accession = accessions[i].replace("-", "") if i < len(accessions) else ""
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{primary_docs[i]}"
                if i < len(primary_docs) else ""
            )
            if not filing_url:
                continue

            filings.append(
                {
                    "cik": cik_padded,
                    "ticker": ",".join(data.get("tickers", [])),
                    "company_name": data.get("name", ""),
                    "form_type": form_type,
                    "filing_date": dates[i] if i < len(dates) else "",
                    "filing_url": filing_url,
                }
            )
            company_filings += 1

    return filings


def extract_catalysts_from_filing(filing_url: str, filing_metadata: dict) -> list[dict]:
    """
    Download a filing and extract regulatory catalyst mentions.

    Args:
        filing_url: URL to the filing document
        filing_metadata: Metadata about the filing (cik, form_type, date, etc.)

    Returns:
        List of extracted catalyst records
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": USER_AGENT}
    response = httpx.get(filing_url, headers=headers, timeout=60, follow_redirects=True)
    response.raise_for_status()
    text = response.text

    # Save raw filing
    safe_name = filing_url.split("/")[-1][:50]
    raw_path = RAW_DIR / f"{filing_metadata.get('cik', 'unknown')}_{safe_name}"
    raw_path.write_text(text)

    # Extract text content while avoiding noisy XML-as-HTML warnings from SEC documents.
    parser = "xml" if text.lstrip().startswith("<?xml") else "lxml"
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(text, parser)
    clean_text = soup.get_text(separator=" ", strip=True)

    catalysts = []
    for catalyst_type, patterns in CATALYST_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, clean_text, re.IGNORECASE)
            for match in matches:
                # Get surrounding context (200 chars before and after)
                start = max(0, match.start() - 200)
                end = min(len(clean_text), match.end() + 200)
                context = clean_text[start:end]

                catalyst = {
                    "catalyst_type": catalyst_type,
                    "matched_text": match.group(0),
                    "context": context.strip(),
                    "filing_url": filing_url,
                    "filing_date": filing_metadata.get("filing_date", ""),
                    "company": filing_metadata.get("company_name", ""),
                    "ticker": filing_metadata.get("ticker", ""),
                    "form_type": filing_metadata.get("form_type", ""),
                    "source_type": "SEC",
                    "source_confidence": "secondary",
                    "extracted_at": datetime.now().isoformat(),
                }

                # Try to extract a date if it's a PDUFA pattern
                if catalyst_type == "pdufa_date" and match.groups():
                    catalyst["sponsor_disclosed_target_date"] = match.group(1)

                catalysts.append(catalyst)

    # Save extracted catalysts
    if catalysts:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = PROCESSED_DIR / f"catalysts_{filing_metadata.get('cik', '')}_{timestamp}.json"
        out_path.write_text(json.dumps(catalysts, indent=2))

    return catalysts


def extract_catalysts_from_cached_filings(
    filing_types: list[str] | None = None,
    limit_per_company: int = 10,
) -> list[dict]:
    """Extract catalysts from the latest cached SEC filings for each company."""
    all_catalysts: list[dict] = []
    seen_urls: set[str] = set()

    for filing in load_cached_filings(filing_types=filing_types, limit_per_company=limit_per_company):
        filing_url = filing["filing_url"]
        if filing_url in seen_urls:
            continue

        seen_urls.add(filing_url)
        try:
            catalysts = extract_catalysts_from_filing(filing_url, filing)
        except httpx.HTTPError as exc:
            print(f"Skipping {filing_url}: {exc}")
            continue

        all_catalysts.extend(catalysts)

    return all_catalysts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract catalysts from SEC filing")
    parser.add_argument("--url", type=str, help="Single filing URL")
    parser.add_argument("--batch", action="store_true", help="Extract from cached SEC submission files")
    parser.add_argument("--cik", type=str, default="")
    parser.add_argument("--ticker", type=str, default="")
    parser.add_argument(
        "--types",
        nargs="+",
        default=["8-K", "10-Q", "10-K"],
        help="Filing types to include when running in batch mode",
    )
    parser.add_argument(
        "--limit-per-company",
        type=int,
        default=10,
        help="Maximum filings to inspect per company in batch mode",
    )
    args = parser.parse_args()

    if args.url:
        metadata = {"cik": args.cik, "ticker": args.ticker, "filing_date": "", "form_type": "", "company_name": ""}
        catalysts = extract_catalysts_from_filing(args.url, metadata)
        print(f"Extracted {len(catalysts)} catalyst mentions")
        for catalyst in catalysts:
            print(f"  [{catalyst['catalyst_type']}] {catalyst['matched_text'][:80]}")
    elif args.batch:
        catalysts = extract_catalysts_from_cached_filings(
            filing_types=args.types,
            limit_per_company=args.limit_per_company,
        )
        print(f"Extracted {len(catalysts)} catalyst mentions from cached SEC filings")
    else:
        parser.error("Provide either --url for a single filing or --batch for cached filings")
