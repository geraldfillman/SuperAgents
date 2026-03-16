"""
Benchmark Tracker -- Fetch Benchmarks
Search SEC EDGAR EFTS and arXiv API for quantum benchmark announcements
(quantum volume, CLOPS, EPLG, custom metrics).
"""

import json
import os
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = Path("data/raw/quantum/benchmarks")
EDGAR_EFTS_BASE = "https://efts.sec.gov/LATEST/search-index"
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "QuantumTracker research@example.com")

BENCHMARK_KEYWORDS = [
    "quantum volume",
    "CLOPS",
    "error per layered gate",
    "EPLG",
    "logical qubit",
    "error correction threshold",
    "two-qubit gate fidelity",
    "quantum advantage",
    "quantum supremacy",
]


def fetch_benchmarks_from_edgar(days: int = 7, limit: int = 50) -> list[dict]:
    """
    Search SEC EDGAR full-text search for quantum benchmark disclosures.

    Args:
        days: Lookback window in days.
        limit: Maximum results to return.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    headers = {"User-Agent": USER_AGENT}

    results = []
    for keyword in BENCHMARK_KEYWORDS:
        params = {
            "q": f'"{keyword}"',
            "dateRange": "custom",
            "startdt": start_date,
            "enddt": end_date,
            "forms": "8-K,10-K,10-Q",
        }

        try:
            response = httpx.get(
                EDGAR_EFTS_BASE, params=params, headers=headers, timeout=30
            )
            response.raise_for_status()
            hits = response.json().get("hits", {}).get("hits", [])
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            print(f"EDGAR search failed for '{keyword}': {exc}")
            continue

        for hit in hits[:limit]:
            source_data = hit.get("_source", {})
            record = {
                "benchmark_keyword": keyword,
                "company_name": source_data.get("display_names", [""])[0],
                "filing_type": source_data.get("form_type", ""),
                "filing_date": source_data.get("file_date", ""),
                "file_num": source_data.get("file_num", ""),
                "source_url": f"https://www.sec.gov/Archives/edgar/data/{source_data.get('entity_id', '')}",
                "source_type": "SEC",
                "source_confidence": "secondary",
                "fetched_at": datetime.now().isoformat(),
            }
            results.append(record)

    return results


def fetch_benchmarks_from_arxiv(days: int = 7, limit: int = 50) -> list[dict]:
    """
    Search arXiv for recent quantum benchmark papers.

    Args:
        days: Lookback window in days.
        limit: Maximum results to return.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    query_terms = "+OR+".join(
        f'all:"{kw}"' for kw in ["quantum volume", "CLOPS", "EPLG", "gate fidelity"]
    )
    search_query = f"cat:quant-ph+AND+({query_terms})"

    params = {
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(limit),
    }

    results = []
    try:
        response = httpx.get(ARXIV_API_BASE, params=params, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"arXiv API request failed: {exc}")
        return results

    # Parse Atom XML response
    from xml.etree import ElementTree

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ElementTree.fromstring(response.text)

    cutoff = datetime.now() - timedelta(days=days)

    for entry in root.findall("atom:entry", ns):
        published_str = (entry.findtext("atom:published", "", ns) or "").strip()
        try:
            published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if published.replace(tzinfo=None) < cutoff:
            continue

        arxiv_id_raw = entry.findtext("atom:id", "", ns) or ""
        arxiv_id = arxiv_id_raw.split("/abs/")[-1] if "/abs/" in arxiv_id_raw else arxiv_id_raw

        authors = [
            a.findtext("atom:name", "", ns)
            for a in entry.findall("atom:author", ns)
        ]

        record = {
            "title": (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " "),
            "arxiv_id": arxiv_id,
            "authors": ", ".join(authors[:5]),
            "published": published_str,
            "summary": (entry.findtext("atom:summary", "", ns) or "").strip()[:500],
            "source_url": f"https://arxiv.org/abs/{arxiv_id}",
            "source_type": "arXiv",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    return results


def run(days: int = 7, limit: int = 50) -> None:
    """Fetch benchmarks from all sources and save to disk."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    edgar_results = fetch_benchmarks_from_edgar(days=days, limit=limit)
    arxiv_results = fetch_benchmarks_from_arxiv(days=days, limit=limit)

    all_results = edgar_results + arxiv_results

    if all_results:
        out_path = RAW_DIR / f"benchmarks_{timestamp}.json"
        out_path.write_text(json.dumps(all_results, indent=2))
        print(f"Saved {len(all_results)} benchmark records to {out_path}")
        print(f"  EDGAR hits: {len(edgar_results)}")
        print(f"  arXiv hits: {len(arxiv_results)}")
    else:
        print("No benchmark records found.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch quantum benchmark announcements")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=50, help="Max results per source")
    args = parser.parse_args()

    run(days=args.days, limit=args.limit)
