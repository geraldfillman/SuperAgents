"""SEC Form 4 helpers."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET

import httpx

from .io_utils import write_json
from .paths import ensure_directory, project_path, slugify
from .sec import (
    SEC_TIMEOUT_SECONDS,
    SEC_USER_AGENT,
    build_recent_filings,
    fetch_submissions,
    normalize_cik,
    resolve_cik,
)

RAW_FORM4_DIR = project_path("data", "raw", "sec", "form4")
INSIDER_TRADES_DIR = project_path("data", "processed", "insider_trades")


def _make_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": SEC_USER_AGENT, "Accept": "application/xml,text/xml,text/html"},
        timeout=SEC_TIMEOUT_SECONDS,
        follow_redirects=True,
    )


def _filter_recent_form4_filings(submissions: dict, days: int) -> list[dict]:
    cutoff = date.today() - timedelta(days=days)
    filings = build_recent_filings(submissions, filing_types=("4",), limit=100)
    recent: list[dict] = []
    for filing in filings:
        try:
            filing_date = date.fromisoformat(filing.get("filing_date", ""))
        except ValueError:
            continue
        if filing_date >= cutoff:
            recent.append(filing)
    return recent


def fetch_form4_document(filing: dict, client: httpx.Client | None = None) -> str:
    """Fetch a Form 4 document from the SEC archive."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        response = client.get(filing["filing_url"])
        response.raise_for_status()
        return response.text
    finally:
        if own_client:
            client.close()


def _archive_index_url(filing: dict) -> str:
    cik_unpadded, _ = normalize_cik(filing.get("cik", ""))
    accession = filing.get("accession_number", "").replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/index.json"


def _resolve_form4_xml_url(filing: dict, client: httpx.Client | None = None) -> str:
    """Locate the raw XML attachment for a Form 4 filing."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        response = client.get(_archive_index_url(filing), headers={"User-Agent": SEC_USER_AGENT, "Accept": "application/json"})
        response.raise_for_status()
        items = response.json().get("directory", {}).get("item", [])
    finally:
        if own_client:
            client.close()

    accession = filing.get("accession_number", "").replace("-", "")
    cik_unpadded, _ = normalize_cik(filing.get("cik", ""))
    for item in items:
        name = item.get("name", "")
        if not name.lower().endswith(".xml"):
            continue
        return f"https://www.sec.gov/Archives/edgar/data/{cik_unpadded}/{accession}/{name}"
    return filing.get("filing_url", "")


def save_form4_document(ticker: str, filing: dict, text: str) -> Path:
    """Persist raw Form 4 XML or HTML."""
    destination = ensure_directory(RAW_FORM4_DIR)
    label = slugify(f"{ticker}_{filing.get('filing_date', '')}_{filing.get('accession_number', '')}")
    suffix = ".xml" if text.lstrip().startswith("<?xml") or "<ownershipDocument>" in text else ".txt"
    out_path = destination / f"form4_{label}{suffix}"
    out_path.write_text(text, encoding="utf-8")
    return out_path


def _text(element: ET.Element | None, path: str) -> str:
    if element is None:
        return ""
    node = element.find(path)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _bool_text(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}


def _owner_role(relationship: ET.Element | None) -> str:
    if relationship is None:
        return ""
    parts: list[str] = []
    if _bool_text(_text(relationship, "isDirector")):
        parts.append("Director")
    if _bool_text(_text(relationship, "isOfficer")):
        title = _text(relationship, "officerTitle")
        parts.append(title or "Officer")
    if _bool_text(_text(relationship, "isTenPercentOwner")):
        parts.append("10% Owner")
    if _bool_text(_text(relationship, "isOther")):
        other = _text(relationship, "otherText")
        parts.append(other or "Other")
    return "; ".join(parts)


def _float_or_none(value: str) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_form4_transactions(xml_text: str, *, filing_metadata: dict) -> list[dict]:
    """Parse Form 4 non-derivative transactions into normalized records."""
    root = ET.fromstring(xml_text)
    owner = root.find("reportingOwner")
    owner_name = _text(owner, "reportingOwnerId/rptOwnerName") or filing_metadata.get("company_name", "")
    relationship = owner.find("reportingOwnerRelationship") if owner is not None else None
    owner_role = _owner_role(relationship)

    records: list[dict] = []
    transactions = root.findall(".//nonDerivativeTable/nonDerivativeTransaction")
    for transaction in transactions:
        transaction_date = _text(transaction, "transactionDate/value") or filing_metadata.get("filing_date", "")
        transaction_code = _text(transaction, "transactionCoding/transactionCode")
        shares = _float_or_none(_text(transaction, "transactionAmounts/transactionShares/value"))
        price = _float_or_none(_text(transaction, "transactionAmounts/transactionPricePerShare/value"))
        value_usd = None
        if shares is not None and price is not None:
            value_usd = round(shares * price, 2)

        records.append(
            {
                "company_name": filing_metadata.get("company_name", ""),
                "ticker": filing_metadata.get("ticker", ""),
                "cik": filing_metadata.get("cik", ""),
                "insider_name": owner_name,
                "insider_role": owner_role,
                "transaction_date": transaction_date,
                "transaction_code": transaction_code,
                "shares": shares,
                "price_per_share": price,
                "value_usd": value_usd,
                "source_url": filing_metadata.get("filing_url", ""),
                "source_type": "SEC Form 4",
                "source_confidence": "primary",
                "filing_date": filing_metadata.get("filing_date", ""),
                "accession_number": filing_metadata.get("accession_number", ""),
            }
        )

    return records


def save_insider_trades(ticker: str, records: list[dict]) -> Path:
    """Persist normalized insider-trade records."""
    destination = ensure_directory(INSIDER_TRADES_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = destination / f"insider_trades_{slugify(ticker)}_{timestamp}.json"
    write_json(out_path, records)
    return out_path


def fetch_and_parse_form4s(
    *,
    cik: str | None = None,
    ticker: str | None = None,
    days: int = 180,
    client: httpx.Client | None = None,
) -> dict:
    """Fetch recent Form 4 filings and parse non-derivative transactions."""
    own_client = client is None
    if own_client:
        client = _make_client()

    try:
        assert client is not None
        cik_padded = resolve_cik(cik=cik, ticker=ticker, client=client)
        submissions = fetch_submissions(cik_padded, client=client)
        resolved_ticker = ticker or (submissions.get("tickers") or [""])[0]
        recent_filings = _filter_recent_form4_filings(submissions, days)

        all_records: list[dict] = []
        raw_paths: list[str] = []
        for filing in recent_filings:
            xml_url = _resolve_form4_xml_url(filing, client=client)
            filing_for_fetch = {**filing, "filing_url": xml_url}
            text = fetch_form4_document(filing_for_fetch, client=client)
            raw_paths.append(str(save_form4_document(resolved_ticker, filing, text)))
            if "<ownershipDocument" not in text:
                continue
            all_records.extend(parse_form4_transactions(text, filing_metadata=filing_for_fetch))

        output_path = save_insider_trades(resolved_ticker, all_records)
    finally:
        if own_client:
            client.close()

    return {
        "ticker": resolved_ticker,
        "cik": cik_padded,
        "days": days,
        "filings_considered": len(recent_filings),
        "records": all_records,
        "raw_paths": raw_paths,
        "output_path": str(output_path),
    }
