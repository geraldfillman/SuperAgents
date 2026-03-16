"""
SEC Filings Parser -- Extract Mining Catalysts
Parse 8-K, 10-Q, 10-K filing text to extract mining-specific catalyst
disclosures such as resource estimates, feasibility studies, permit
approvals, and offtake signings.
"""

import re
import json
import httpx
import os
import warnings
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

load_dotenv()

RAW_METADATA_DIR = Path("data/raw/rare_earth/sec")
RAW_DIR = Path("data/raw/rare_earth/sec/filings_text")
PROCESSED_DIR = Path("data/processed/rare_earth/catalysts")

USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "RareEarthTracker research@example.com")

# Mining-specific catalyst patterns
CATALYST_PATTERNS = {
    "resource_estimate": [
        r"(?:mineral\s+)?resource\s+estimate\s+(?:of|totaling|comprising)",
        r"(?:measured|indicated|inferred)\s+(?:mineral\s+)?resource",
        r"NI\s+43-101\s+(?:compliant\s+)?(?:technical\s+)?report",
        r"S-K\s+1300\s+(?:compliant\s+)?(?:technical\s+)?report",
        r"JORC\s+(?:compliant\s+)?resource",
    ],
    "feasibility_study": [
        r"(?:preliminary\s+economic\s+assessment|PEA)",
        r"(?:pre-feasibility|prefeasibility)\s+study",
        r"(?:definitive|bankable)\s+feasibility\s+study",
        r"DFS\s+(?:completed|released|announced)",
    ],
    "permit_approval": [
        r"(?:record\s+of\s+decision|ROD)\s+(?:issued|received|granted)",
        r"(?:environmental\s+impact\s+statement|EIS)\s+(?:approved|completed|finalized)",
        r"(?:mining\s+)?permit\s+(?:approved|granted|received|issued)",
        r"(?:water|air)\s+(?:quality\s+)?permit\s+(?:approved|granted)",
        r"NEPA\s+(?:approval|clearance|review\s+completed)",
    ],
    "offtake_signing": [
        r"offtake\s+agreement\s+(?:signed|executed|entered|announced)",
        r"(?:binding|definitive)\s+(?:offtake|supply)\s+agreement",
        r"(?:letter\s+of\s+intent|LOI)\s+(?:for|regarding)\s+(?:offtake|supply)",
    ],
    "dpa_award": [
        r"(?:Defense\s+Production\s+Act|DPA)\s+(?:Title\s+III\s+)?(?:award|grant|funding)",
        r"(?:Department\s+of\s+(?:Defense|Energy))\s+(?:award|grant|contract)",
        r"critical\s+minerals?\s+(?:award|grant|funding|investment)",
    ],
    "production_milestone": [
        r"(?:first|initial)\s+(?:production|concentrate|output)",
        r"(?:commercial\s+)?production\s+(?:commenced|started|began|achieved)",
        r"(?:nameplate|design)\s+capacity\s+(?:reached|achieved)",
    ],
    "construction_update": [
        r"construction\s+(?:commenced|started|began|completed|on\s+schedule)",
        r"(?:EPCM|EPC)\s+(?:contract|agreement)\s+(?:awarded|signed)",
        r"(?:mechanical|substantial)\s+completion\s+(?:achieved|reached)",
    ],
}


from super_agents.common.cik import normalize_cik  # noqa: E402 -- centralized CIK util


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
    Download a filing and extract mining-specific catalyst mentions.

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
                    "source_url": filing_url,
                    "source_confidence": "secondary",
                    "extracted_at": datetime.now().isoformat(),
                }

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
    """Extract mining catalysts from the latest cached SEC filings for each company."""
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

    parser = argparse.ArgumentParser(description="Extract mining catalysts from SEC filings")
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
        print(f"Extracted {len(catalysts)} mining catalyst mentions")
        for catalyst in catalysts:
            print(f"  [{catalyst['catalyst_type']}] {catalyst['matched_text'][:80]}")
    elif args.batch:
        catalysts = extract_catalysts_from_cached_filings(
            filing_types=args.types,
            limit_per_company=args.limit_per_company,
        )
        print(f"Extracted {len(catalysts)} mining catalyst mentions from cached SEC filings")
    else:
        parser.error("Provide either --url for a single filing or --batch for cached filings")
