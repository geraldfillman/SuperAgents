"""Award-query helpers for the blueprint."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify
from .watchlist import CompanyRecord, find_company, load_company_watchlist

DEFAULT_QUERY_DIR = project_path("data", "raw", "awards", "queries")


def build_award_query_manifest(
    company: CompanyRecord,
    *,
    agency: str | None = None,
    days: int = 30,
) -> dict:
    """Build a saved-query manifest for a tracked company."""
    return {
        "company_name": company.company_name,
        "ticker": company.ticker,
        "cik": company.cik,
        "cage_code": company.cage_code,
        "ueid": company.ueid,
        "primary_domain": company.primary_domain,
        "primary_customer": company.primary_customer,
        "agency_filter": agency or "",
        "days": days,
        "search_terms": [
            term for term in [company.company_name, company.ticker, company.cage_code, company.ueid] if term
        ],
        "source_type": "query_manifest",
        "source_confidence": "manual",
        "created_at": datetime.now().isoformat(),
    }


def build_manual_award_query(
    company_name: str,
    *,
    ticker: str = "",
    cage_code: str = "",
    ueid: str = "",
    agency: str | None = None,
    days: int = 30,
) -> dict:
    """Build a manifest when the company is not yet present in the watchlist."""
    company = CompanyRecord(
        company_name=company_name,
        ticker=ticker,
        cage_code=cage_code,
        ueid=ueid,
    )
    return build_award_query_manifest(company, agency=agency, days=days)


def save_award_query_manifest(manifest: dict, output_dir: Path | None = None) -> Path:
    """Persist a manifest and return its path."""
    destination = ensure_directory(output_dir or DEFAULT_QUERY_DIR)
    name = slugify(f"{manifest.get('ticker', '')}_{manifest['company_name']}")
    out_path = destination / f"award_query_{name}.json"
    write_json(out_path, manifest)
    return out_path


def build_watchlist_manifests(
    *,
    ticker: str | None = None,
    company_name: str | None = None,
    agency: str | None = None,
    days: int = 30,
    output_dir: Path | None = None,
) -> list[Path]:
    """Generate query manifests from the tracked watchlist."""
    companies = load_company_watchlist()
    if ticker or company_name:
        company = find_company(ticker=ticker, company_name=company_name, companies=companies)
        if company is None:
            return []
        companies = [company]

    written_paths: list[Path] = []
    for company in companies:
        manifest = build_award_query_manifest(company, agency=agency, days=days)
        written_paths.append(save_award_query_manifest(manifest, output_dir=output_dir))
    return written_paths
