"""
SEC Filings Parser -- Extract Energy Catalysts
Parse cached SEC filings for energy-specific catalysts
(PPA signing, interconnection advance, IRA credit, COD).
"""

import argparse
import re
import json
import os
import warnings
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

load_dotenv()

RAW_METADATA_DIR = Path("data/raw/renewable_energy/sec")
RAW_DIR = Path("data/raw/renewable_energy/sec/filings_text")
PROCESSED_DIR = Path("data/processed/renewable_energy/energy_catalysts")

USER_AGENT = os.getenv(
    "SEC_EDGAR_USER_AGENT",
    "RenewableEnergyTracker research@example.com",
)

# Energy-specific catalyst patterns
ENERGY_CATALYST_PATTERNS = {
    "ppa_signing": [
        r"(?:entered into|executed|signed)\s+(?:a\s+)?(?:power\s+purchase\s+agreement|PPA)",
        r"(?:PPA|power\s+purchase\s+agreement)\s+(?:with|for)\s+(\d+)\s*(?:MW|megawatt)",
        r"offtake\s+agreement\s+(?:with|for)",
    ],
    "interconnection_advance": [
        r"interconnection\s+(?:agreement|approval|study)\s+(?:completed|approved|executed)",
        r"generator\s+interconnection\s+(?:agreement|GIA)",
        r"(?:LGIA|large\s+generator\s+interconnection)",
        r"interconnection\s+queue\s+(?:position|number|advanced)",
    ],
    "ira_credit": [
        r"(?:investment\s+tax\s+credit|ITC)\s+(?:of|totaling|estimated)",
        r"(?:production\s+tax\s+credit|PTC)\s+(?:of|totaling|estimated)",
        r"(?:Section\s+)?45X\s+(?:credit|manufacturing)",
        r"(?:Section\s+)?48C\s+(?:credit|advanced\s+energy)",
        r"Inflation\s+Reduction\s+Act\s+(?:benefit|credit|incentive)",
    ],
    "cod_milestone": [
        r"commercial\s+operation(?:s)?\s+date\s*(?:of|is|:)?\s*(\w+\s+\d{1,2},?\s*\d{4})",
        r"(?:achieved|reached|commenced)\s+commercial\s+operation",
        r"COD\s+(?:of|expected|achieved|targeted)\s+",
    ],
    "construction_milestone": [
        r"(?:commenced|began|started)\s+construction",
        r"notice\s+to\s+proceed\s+(?:issued|received)",
        r"groundbreaking\s+(?:ceremony|event|for)",
        r"mechanical\s+completion\s+(?:achieved|reached)",
    ],
    "capacity_expansion": [
        r"(\d+)\s*(?:MW|GW|megawatt|gigawatt)\s+(?:expansion|addition|increase)",
        r"expand(?:ing)?\s+(?:capacity|production)\s+(?:by|to)\s+(\d+)",
    ],
    "doe_funding": [
        r"(?:DOE|Department\s+of\s+Energy)\s+(?:loan|grant|award|funding)",
        r"Loan\s+Programs?\s+Office\s+(?:conditional|final)\s+(?:commitment|approval)",
        r"(?:ATVM|Title\s+XVII)\s+(?:loan|program)",
    ],
    "permit_approval": [
        r"(?:received|obtained|granted)\s+(?:building\s+)?permit",
        r"(?:environmental|EIS|NEPA)\s+(?:review|approval|clearance)\s+(?:completed|approved)",
        r"zoning\s+(?:approval|variance|permit)",
    ],
}


def _normalize_cik(cik: str) -> tuple[str, str]:
    """Return (unpadded, padded-to-10) CIK strings."""
    digits = "".join(ch for ch in str(cik) if ch.isdigit())
    if not digits:
        raise ValueError("CIK must contain at least one digit")
    unpadded = digits.lstrip("0") or "0"
    padded = digits.zfill(10)
    return unpadded, padded


def _cached_sec_files() -> list[Path]:
    """Return the latest SEC submissions cache file for each company."""
    if not RAW_METADATA_DIR.exists():
        return []

    latest_by_cik: dict[str, Path] = {}
    for path in RAW_METADATA_DIR.glob("filings_*.json"):
        try:
            data = json.loads(path.read_text())
            _, cik_padded = _normalize_cik(str(data.get("cik", "")))
        except (json.JSONDecodeError, ValueError):
            continue
        previous = latest_by_cik.get(cik_padded)
        if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
            latest_by_cik[cik_padded] = path

    return sorted(latest_by_cik.values(), key=lambda p: p.stat().st_mtime)


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
        cik_unpadded, cik_padded = _normalize_cik(str(data.get("cik", "")))

        company_count = 0
        for i, form_type in enumerate(forms):
            if filing_types and form_type not in filing_types:
                continue
            if company_count >= limit_per_company:
                break

            accession = accessions[i].replace("-", "") if i < len(accessions) else ""
            filing_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{primary_docs[i]}"
                if i < len(primary_docs)
                else ""
            )
            if not filing_url:
                continue

            filings.append({
                "cik": cik_padded,
                "ticker": ",".join(data.get("tickers", [])),
                "company_name": data.get("name", ""),
                "form_type": form_type,
                "filing_date": dates[i] if i < len(dates) else "",
                "filing_url": filing_url,
            })
            company_count += 1

    return filings


def extract_energy_catalysts_from_filing(
    filing_url: str,
    filing_metadata: dict,
) -> list[dict]:
    """
    Download a filing and extract energy-specific catalyst mentions.

    Args:
        filing_url: URL to the filing document
        filing_metadata: Metadata about the filing (cik, form_type, date, etc.)

    Returns:
        List of extracted energy catalyst records
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

    # Extract text content
    parser = "xml" if text.lstrip().startswith("<?xml") else "lxml"
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(text, parser)
    clean_text = soup.get_text(separator=" ", strip=True)

    catalysts = []
    for catalyst_type, patterns in ENERGY_CATALYST_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, clean_text, re.IGNORECASE)
            for match in matches:
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
                    "source_url": filing_url,
                    "source_type": "SEC",
                    "source_confidence": "secondary",
                    "extracted_at": datetime.now().isoformat(),
                }

                # Try to extract a date if it is a COD pattern
                if catalyst_type == "cod_milestone" and match.groups():
                    catalyst["disclosed_cod_date"] = match.group(1)

                catalysts.append(catalyst)

    # Save extracted catalysts
    if catalysts:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = (
            PROCESSED_DIR
            / f"energy_catalysts_{filing_metadata.get('cik', '')}_{timestamp}.json"
        )
        out_path.write_text(json.dumps(catalysts, indent=2))

    return catalysts


def extract_energy_catalysts_batch(
    filing_types: list[str] | None = None,
    limit_per_company: int = 10,
) -> list[dict]:
    """Extract energy catalysts from all cached SEC filings."""
    all_catalysts: list[dict] = []
    seen_urls: set[str] = set()

    for filing in load_cached_filings(
        filing_types=filing_types, limit_per_company=limit_per_company
    ):
        filing_url = filing["filing_url"]
        if filing_url in seen_urls:
            continue
        seen_urls.add(filing_url)

        try:
            catalysts = extract_energy_catalysts_from_filing(filing_url, filing)
        except httpx.HTTPError as exc:
            print(f"Skipping {filing_url}: {exc}")
            continue

        all_catalysts.extend(catalysts)

    return all_catalysts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract energy catalysts from SEC filings"
    )
    parser.add_argument("--url", type=str, help="Single filing URL")
    parser.add_argument(
        "--batch", action="store_true", help="Extract from cached SEC submissions"
    )
    parser.add_argument("--cik", type=str, default="")
    parser.add_argument("--ticker", type=str, default="")
    parser.add_argument(
        "--types",
        nargs="+",
        default=["8-K", "10-Q", "10-K"],
        help="Filing types to include in batch mode",
    )
    parser.add_argument(
        "--limit-per-company",
        type=int,
        default=10,
        help="Max filings per company in batch mode",
    )
    args = parser.parse_args()

    import argparse as _argparse  # already imported above

    if args.url:
        metadata = {
            "cik": args.cik,
            "ticker": args.ticker,
            "filing_date": "",
            "form_type": "",
            "company_name": "",
        }
        catalysts = extract_energy_catalysts_from_filing(args.url, metadata)
        print(f"Extracted {len(catalysts)} energy catalyst mentions")
        for c in catalysts:
            print(f"  [{c['catalyst_type']}] {c['matched_text'][:80]}")
    elif args.batch:
        catalysts = extract_energy_catalysts_batch(
            filing_types=args.types,
            limit_per_company=args.limit_per_company,
        )
        print(
            f"Extracted {len(catalysts)} energy catalyst mentions from cached filings"
        )
    else:
        parser.error(
            "Provide either --url for a single filing or --batch for cached filings"
        )
