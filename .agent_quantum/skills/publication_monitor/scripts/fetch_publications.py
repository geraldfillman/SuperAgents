"""
Publication Monitor -- Fetch Publications
Query the arXiv API for recent quantum computing papers by company-affiliated authors.
"""

import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

RAW_DIR = Path("data/raw/quantum/publications")
ARXIV_API_BASE = "http://export.arxiv.org/api/query"


def fetch_publications(
    company: str = "",
    days: int = 30,
    limit: int = 50,
) -> list[dict]:
    """
    Query arXiv for recent quantum computing papers, optionally filtered
    by company-affiliated author name.

    Args:
        company: Company or author affiliation keyword (e.g. 'IBM', 'Google Quantum').
        days: Lookback window in days.
        limit: Maximum number of results.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # Build search query
    base_query = "cat:quant-ph"
    if company:
        # Search for company name in author affiliations or abstracts
        base_query = f"cat:quant-ph+AND+au:{company.replace(' ', '+')}"

    params = {
        "search_query": base_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(limit),
    }

    try:
        response = httpx.get(ARXIV_API_BASE, params=params, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        print(f"arXiv API request failed: {exc}")
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ElementTree.fromstring(response.text)

    cutoff = datetime.now() - timedelta(days=days)
    results = []

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

        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", ns)
        ]

        title = (entry.findtext("atom:title", "", ns) or "").strip().replace("\n", " ")
        summary = (entry.findtext("atom:summary", "", ns) or "").strip()[:500]

        # Derive topic tags from title and categories
        topic_tags = _derive_topic_tags(title, summary, categories)

        record = {
            "publication_id": f"arxiv_{arxiv_id.replace('/', '_').replace('.', '_')}",
            "title": title,
            "arxiv_id": arxiv_id,
            "authors": ", ".join(authors[:10]),
            "publication_date": published_str[:10],
            "categories": ", ".join(categories),
            "topic_tags": ", ".join(topic_tags),
            "summary": summary,
            "citation_count": 0,
            "source_url": f"https://arxiv.org/abs/{arxiv_id}",
            "source_type": "arXiv",
            "source_confidence": "primary",
            "fetched_at": datetime.now().isoformat(),
        }
        results.append(record)

    return results


def _derive_topic_tags(title: str, summary: str, categories: list[str]) -> list[str]:
    """Derive topic tags from paper title, summary, and arXiv categories."""
    tags = []
    text = (title + " " + summary).lower()

    tag_keywords = {
        "error_correction": ["error correction", "error-correction", "surface code", "stabilizer", "fault-tolerant"],
        "algorithms": ["algorithm", "variational", "qaoa", "vqe", "grover", "shor"],
        "hardware": ["qubit", "transmon", "ion trap", "photonic", "superconducting", "neutral atom"],
        "software": ["compiler", "transpiler", "qiskit", "cirq", "sdk", "framework"],
        "benchmarking": ["benchmark", "quantum volume", "clops", "eplg", "fidelity"],
        "simulation": ["simulation", "emulation", "tensor network"],
        "cryptography": ["cryptograph", "post-quantum", "qkd", "key distribution"],
        "optimization": ["optimization", "annealing", "combinatorial"],
    }

    for tag, keywords in tag_keywords.items():
        if any(kw in text for kw in keywords):
            tags.append(tag)

    return tags


def run(company: str = "", days: int = 30, limit: int = 50) -> None:
    """Fetch publications and save to disk."""
    results = fetch_publications(company=company, days=days, limit=limit)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if results:
        suffix = f"_{company.replace(' ', '_').lower()}" if company else ""
        out_path = RAW_DIR / f"publications{suffix}_{timestamp}.json"
        out_path.write_text(json.dumps(results, indent=2))
        print(f"Saved {len(results)} publications to {out_path}")
        for pub in results[:5]:
            print(f"  [{pub['publication_date']}] {pub['title'][:80]}")
        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more.")
    else:
        print("No publications found matching criteria.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch quantum computing publications from arXiv")
    parser.add_argument("--company", type=str, default="", help="Company or author affiliation keyword")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of results")
    args = parser.parse_args()

    run(company=args.company, days=args.days, limit=args.limit)
