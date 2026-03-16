"""CISA KEV fetch and normalization helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from .paths import KEV_PROCESSED_DIR, KEV_RAW_DIR, ensure_cybersecurity_directory
from .watchlist import AssetRecord

KEV_CATALOG_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
)
DEFAULT_USER_AGENT = "SuperAgentsCybersecurity/0.1"


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
        timeout=30,
    )


def _parse_iso_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _asset_label(asset: AssetRecord) -> str:
    parts = [asset.vendor.strip(), asset.product.strip(), asset.cve_id.strip()]
    return " | ".join(part for part in parts if part)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _match_assets(item: dict[str, Any], assets: list[AssetRecord]) -> list[AssetRecord]:
    cve_id = _normalize_text(item.get("cveID")).upper()
    vendor = _normalize_text(item.get("vendorProject")).lower()
    product = _normalize_text(item.get("product")).lower()

    matches: list[AssetRecord] = []
    for asset in assets:
        asset_cve = asset.cve_id.strip().upper()
        asset_vendor = asset.vendor.strip().lower()
        asset_product = asset.product.strip().lower()

        if asset_cve and asset_cve == cve_id:
            matches.append(asset)
            continue
        if asset_vendor and asset_vendor in vendor:
            if not asset_product or asset_product in product:
                matches.append(asset)
    return matches


def _severity_for_record(*, watchlist_match: bool, ransomware_value: str) -> str:
    normalized_ransomware = ransomware_value.strip().lower()
    if watchlist_match and normalized_ransomware == "known":
        return "critical"
    if watchlist_match or normalized_ransomware == "known":
        return "high"
    return "medium"


def _record_summary(item: dict[str, Any], *, asset_label: str, watchlist_match: bool) -> str:
    due_date = _normalize_text(item.get("dueDate"))
    ransomware = _normalize_text(item.get("knownRansomwareCampaignUse"))
    summary = (
        f"{_normalize_text(item.get('cveID'))} affects {asset_label or 'an unnamed asset'}; "
        f"due {due_date or 'TBD'}."
    )
    if ransomware:
        summary += f" Ransomware use: {ransomware}."
    if watchlist_match:
        summary += " Matched the cybersecurity watchlist."
    return summary


def fetch_kev_catalog(*, client: httpx.Client | None = None) -> dict[str, Any]:
    """Fetch the latest CISA KEV feed."""
    ensure_cybersecurity_directory(KEV_RAW_DIR)
    ensure_cybersecurity_directory(KEV_PROCESSED_DIR)

    owns_client = client is None
    active_client = client or _make_client()
    try:
        response = active_client.get(KEV_CATALOG_URL)
        response.raise_for_status()
        payload = response.json()
    finally:
        if owns_client:
            active_client.close()

    if not isinstance(payload, dict):
        raise ValueError("CISA KEV feed returned a non-object payload.")
    vulnerabilities = payload.get("vulnerabilities", [])
    if not isinstance(vulnerabilities, list):
        raise ValueError("CISA KEV payload does not contain a vulnerability list.")
    return payload


def normalize_kev_catalog(
    payload: dict[str, Any],
    *,
    assets: list[AssetRecord] | None = None,
) -> list[dict[str, Any]]:
    """Normalize raw KEV feed rows into dashboard-friendly records."""
    vulnerabilities = payload.get("vulnerabilities", [])
    if not isinstance(vulnerabilities, list):
        raise ValueError("KEV payload does not contain a list of vulnerabilities.")

    watchlist = assets or []
    fetched_at = datetime.now(timezone.utc).isoformat()
    records: list[dict[str, Any]] = []

    for item in vulnerabilities:
        if not isinstance(item, dict):
            continue

        matches = _match_assets(item, watchlist)
        vendor = _normalize_text(item.get("vendorProject"))
        product = _normalize_text(item.get("product"))
        cve_id = _normalize_text(item.get("cveID"))
        asset_label = " ".join(part for part in [vendor, product] if part).strip() or cve_id
        ransomware_value = _normalize_text(item.get("knownRansomwareCampaignUse"))
        severity = _severity_for_record(
            watchlist_match=bool(matches),
            ransomware_value=ransomware_value,
        )

        records.append(
            {
                "record_id": f"kev_{cve_id.lower()}",
                "cve_id": cve_id,
                "vendor": vendor,
                "product": product,
                "asset": asset_label,
                "vulnerability_name": _normalize_text(item.get("vulnerabilityName")),
                "short_description": _normalize_text(item.get("shortDescription")),
                "required_action": _normalize_text(item.get("requiredAction")),
                "date_added": _normalize_text(item.get("dateAdded")),
                "due_date": _normalize_text(item.get("dueDate")),
                "known_ransomware_campaign_use": ransomware_value,
                "notes": _normalize_text(item.get("notes")),
                "source_url": KEV_CATALOG_URL,
                "source_type": "CISA KEV",
                "source_confidence": "primary",
                "fetched_at": fetched_at,
                "watchlist_match": bool(matches),
                "watchlist_hits": [_asset_label(match) for match in matches],
                "watchlist_priorities": sorted(
                    {match.priority for match in matches if match.priority.strip()}
                ),
                "severity": severity,
                "finding_time": _normalize_text(item.get("dateAdded")),
                "finding_type": "known_exploited_vulnerability",
                "summary": _record_summary(
                    item,
                    asset_label=asset_label,
                    watchlist_match=bool(matches),
                ),
            }
        )

    records.sort(
        key=lambda record: (record.get("date_added", ""), record.get("cve_id", "")),
        reverse=True,
    )
    return records


def select_recent_records(
    records: list[dict[str, Any]],
    *,
    days: int,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Keep KEV rows added within the requested lookback window."""
    if days < 1:
        raise ValueError("days must be positive")

    today = reference_date or datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days)
    recent: list[dict[str, Any]] = []
    for record in records:
        added = _parse_iso_date(_normalize_text(record.get("date_added")))
        if added is None:
            continue
        if added >= cutoff:
            recent.append(record)
    return recent


def build_findings(records: list[dict[str, Any]], *, limit: int = 20) -> list[dict[str, Any]]:
    """Project KEV rows into the shared findings artifact shape."""
    findings: list[dict[str, Any]] = []
    for record in records[:limit]:
        findings.append(
            {
                "severity": record.get("severity", "medium"),
                "asset": record.get("asset", record.get("cve_id", "")),
                "finding_type": record.get("finding_type", "known_exploited_vulnerability"),
                "summary": record.get("summary", ""),
                "source_url": record.get("source_url", ""),
                "confidence": record.get("source_confidence", "primary"),
                "finding_time": record.get("finding_time", ""),
                "watchlist_match": record.get("watchlist_match", False),
                "cve_id": record.get("cve_id", ""),
                "due_date": record.get("due_date", ""),
            }
        )
    return findings
