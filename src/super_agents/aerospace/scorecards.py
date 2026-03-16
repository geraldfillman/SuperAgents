"""Budget reconciliation and company scorecard helpers."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .io_utils import load_json_records, write_json
from .paths import DASHBOARDS_DIR, ensure_directory, project_path, slugify
from .watchlist import CompanyRecord, SystemRecord, load_company_watchlist, load_system_watchlist

BUDGET_MAPPING_OVERRIDES_PATH = project_path("data", "seeds", "budget_mapping_overrides.csv")
BUDGET_EXPOSURE_DIR = project_path("data", "processed", "budget_exposure")

GENERIC_TOKENS = {
    "and",
    "advanced",
    "agency",
    "budget",
    "capability",
    "communications",
    "civil",
    "defense",
    "development",
    "equipment",
    "for",
    "from",
    "major",
    "management",
    "mission",
    "of",
    "on",
    "program",
    "programs",
    "research",
    "science",
    "sciences",
    "support",
    "system",
    "systems",
    "the",
    "technology",
    "technologies",
    "to",
    "with",
}
CORPORATE_SUFFIXES = {
    "co",
    "company",
    "corp",
    "corporation",
    "group",
    "holdings",
    "inc",
    "incorporated",
    "limited",
    "llc",
    "ltd",
    "plc",
    "technologies",
}
DOMAIN_KEYWORDS = {
    "space": {"space", "launch", "lunar", "orbital", "satellite"},
    "air": {"aerospace", "air", "aircraft", "aviation", "flight"},
    "sea": {"maritime", "naval", "ocean", "sea", "undersea"},
    "electronics": {"electronic", "electronics", "microelectronics", "sensor", "sensors"},
    "software": {"analytics", "command", "communications", "control", "information", "network", "software"},
    "cyber": {"command", "communications", "control", "cyber", "information", "network", "software"},
    "services": {"logistics", "management", "mission", "services", "support"},
    "missile": {"interceptor", "missile", "munition", "munitions", "radar"},
}
CUSTOMER_FAMILY_KEYWORDS = {
    "department of defense": {
        "defense advanced research projects agency",
        "defense-wide",
        "department of defense",
        "department of the air force",
        "department of the army",
        "department of the navy",
        "missile defense agency",
        "office of the secretary of defense",
    },
    "air force": {"air force", "department of the air force"},
    "army": {"army", "department of the army"},
    "navy": {"navy", "department of the navy"},
    "nasa": {"nasa", "national aeronautics"},
    "nro": {"national reconnaissance office", "nro"},
    "space force": {"space force"},
}


def _normalize_text(value: str) -> str:
    lowered = "".join(char.lower() if char.isalnum() or char.isspace() else " " for char in value)
    return " ".join(lowered.split())


def _significant_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for token in _normalize_text(value).split():
        if len(token) <= 2:
            continue
        if token in GENERIC_TOKENS or token in CORPORATE_SUFFIXES:
            continue
        tokens.add(token)
    return tokens


def _budget_line_key(record: dict) -> tuple:
    return (
        _clean_budget_value(str(record.get("agency", ""))),
        str(record.get("fiscal_year", "")),
        _clean_budget_value(str(record.get("program_element", ""))),
        _clean_budget_value(str(record.get("line_item", ""))),
        float(record.get("amount_usd", 0.0) or 0.0),
        str(record.get("source_url", "")),
    )


def _clean_budget_value(value: str) -> str:
    cleaned = _normalize_text(value.replace("UNCLASSIFIED", " "))
    return cleaned


def _clean_budget_line(record: dict) -> dict:
    return {
        **record,
        "agency": _clean_budget_value(str(record.get("agency", ""))),
        "appropriation": _clean_budget_value(str(record.get("appropriation", ""))),
        "program_element": _clean_budget_value(str(record.get("program_element", ""))).upper(),
        "line_item": _clean_budget_value(str(record.get("line_item", ""))),
    }


def _dedupe_budget_lines(records: list[dict]) -> list[dict]:
    deduped: dict[tuple, dict] = {}
    for record in records:
        cleaned = _clean_budget_line(record)
        key = _budget_line_key(cleaned)
        existing = deduped.get(key)
        if existing is None or len(cleaned.get("appropriation", "")) > len(existing.get("appropriation", "")):
            deduped[key] = cleaned
    return list(deduped.values())


def _combined_budget_text(record: dict) -> str:
    return _normalize_text(
        " ".join(
            [
                str(record.get("agency", "")),
                str(record.get("appropriation", "")),
                str(record.get("program_element", "")),
                str(record.get("line_item", "")),
            ]
        )
    )


def load_budget_mapping_overrides(path: Path | None = None) -> list[dict]:
    """Load analyst-approved budget mapping overrides."""
    resolved = path or BUDGET_MAPPING_OVERRIDES_PATH
    if not resolved.exists():
        return []
    with resolved.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _domain_keywords(system: SystemRecord, company: CompanyRecord) -> set[str]:
    keywords: set[str] = set()
    domain_text = f"{system.domain} {company.primary_domain}".lower()
    for label, label_keywords in DOMAIN_KEYWORDS.items():
        if label in domain_text:
            keywords.update(label_keywords)
    if not keywords:
        keywords.update(_significant_tokens(system.domain))
        keywords.update(_significant_tokens(company.primary_domain))
    return keywords


def _system_type_keywords(system: SystemRecord) -> set[str]:
    return _significant_tokens(system.system_type)


def _customer_keywords(system: SystemRecord, company: CompanyRecord) -> set[str]:
    customer_text = (system.primary_customer or company.primary_customer).lower()
    keywords: set[str] = set()
    for label, label_keywords in CUSTOMER_FAMILY_KEYWORDS.items():
        if label in customer_text:
            keywords.update(label_keywords)
    if not keywords:
        keywords.update(_significant_tokens(customer_text))
    return keywords


def _matches_named_entity(name: str, budget_text: str) -> bool:
    normalized_name = _normalize_text(name)
    if not normalized_name:
        return False

    budget_tokens = budget_text.split()
    name_tokens = normalized_name.split()
    if len(name_tokens) >= 2 and normalized_name in budget_text:
        return True

    tokens = _significant_tokens(name)
    if not tokens:
        return False
    budget_token_set = set(budget_tokens)
    if len(tokens) >= 2:
        return tokens.issubset(budget_token_set)
    if len(tokens) == 1 and len(name_tokens) == 1:
        token = next(iter(tokens))
        return token in budget_token_set
    return False


def _text_contains_keyword(keyword: str, budget_text: str, budget_token_set: set[str]) -> bool:
    normalized_keyword = _normalize_text(keyword)
    if not normalized_keyword:
        return False
    if " " in normalized_keyword:
        return normalized_keyword in budget_text
    return normalized_keyword in budget_token_set


def _override_matches(override: dict, system: SystemRecord, budget_line: dict) -> bool:
    if override.get("ticker") and override["ticker"].strip().upper() != system.ticker.upper():
        return False
    if override.get("system_name") and _normalize_text(override["system_name"]) != _normalize_text(system.system_name):
        return False

    for field in ("agency", "appropriation", "program_element", "line_item"):
        candidate = override.get(field, "").strip()
        if candidate and _normalize_text(candidate) != _normalize_text(str(budget_line.get(field, ""))):
            return False

    fiscal_year = override.get("fiscal_year", "").strip()
    if fiscal_year and fiscal_year != str(budget_line.get("fiscal_year", "")):
        return False
    return True


def _build_match_record(
    system: SystemRecord,
    company: CompanyRecord,
    budget_line: dict,
    *,
    match_type: str,
    match_score: float,
    match_confidence: str,
    evidence: list[str],
) -> dict:
    return {
        "company_name": company.company_name,
        "ticker": company.ticker,
        "system_name": system.system_name,
        "domain": system.domain,
        "system_type": system.system_type,
        "primary_customer": system.primary_customer or company.primary_customer,
        "agency": budget_line.get("agency", ""),
        "fiscal_year": budget_line.get("fiscal_year"),
        "appropriation": budget_line.get("appropriation", ""),
        "program_element": budget_line.get("program_element", ""),
        "line_item": budget_line.get("line_item", ""),
        "amount_usd": float(budget_line.get("amount_usd", 0.0) or 0.0),
        "match_type": match_type,
        "match_score": round(match_score, 2),
        "match_confidence": match_confidence,
        "evidence": evidence,
        "source_url": budget_line.get("source_url", ""),
        "source_type": budget_line.get("source_type", ""),
        "source_confidence": budget_line.get("source_confidence", ""),
    }


def build_budget_exposure_matches(
    budget_lines: list[dict],
    *,
    companies: list[CompanyRecord] | None = None,
    systems: list[SystemRecord] | None = None,
    overrides: list[dict] | None = None,
    min_score: float = 0.35,
) -> list[dict]:
    """Map budget lines to tracked systems using overrides plus conservative heuristics."""
    company_rows = companies or load_company_watchlist()
    system_rows = systems or load_system_watchlist()
    override_rows = overrides or load_budget_mapping_overrides()

    company_by_ticker = {company.ticker.upper(): company for company in company_rows if company.ticker}
    deduped_budget_lines = _dedupe_budget_lines(budget_lines)

    matches: list[dict] = []
    for system in system_rows:
        company = company_by_ticker.get(system.ticker.upper())
        if company is None:
            continue

        for budget_line in deduped_budget_lines:
            budget_text = _combined_budget_text(budget_line)
            budget_token_set = set(budget_text.split())
            chosen_match: dict | None = None

            for override in override_rows:
                if not _override_matches(override, system, budget_line):
                    continue
                notes = override.get("notes", "").strip()
                evidence = [f"override:{notes}"] if notes else ["override"]
                chosen_match = _build_match_record(
                    system,
                    company,
                    budget_line,
                    match_type=override.get("match_type", "").strip() or "explicit_override",
                    match_score=1.0,
                    match_confidence="explicit",
                    evidence=evidence,
                )
                break

            if chosen_match is not None:
                matches.append(chosen_match)
                continue

            if _matches_named_entity(system.system_name, budget_text):
                matches.append(
                    _build_match_record(
                        system,
                        company,
                        budget_line,
                        match_type="system_keyword",
                        match_score=0.9,
                        match_confidence="high",
                        evidence=[f"system_name:{system.system_name}"],
                    )
                )
                continue

            if _matches_named_entity(company.company_name, budget_text):
                matches.append(
                    _build_match_record(
                        system,
                        company,
                        budget_line,
                        match_type="company_keyword",
                        match_score=0.8,
                        match_confidence="medium",
                        evidence=[f"company_name:{company.company_name}"],
                    )
                )
                continue

            score = 0.0
            evidence: list[str] = []

            matched_domain_keywords = sorted(
                keyword
                for keyword in _domain_keywords(system, company)
                if _text_contains_keyword(keyword, budget_text, budget_token_set)
            )
            if matched_domain_keywords:
                score += 0.35
                evidence.append("domain_keywords:" + ",".join(matched_domain_keywords[:3]))

            matched_type_keywords = sorted(
                keyword
                for keyword in _system_type_keywords(system)
                if _text_contains_keyword(keyword, budget_text, budget_token_set)
            )
            if matched_type_keywords:
                score += 0.2
                evidence.append("system_type_keywords:" + ",".join(matched_type_keywords[:3]))

            matched_customer_keywords = sorted(
                keyword
                for keyword in _customer_keywords(system, company)
                if _text_contains_keyword(keyword, budget_text, budget_token_set)
            )
            if matched_customer_keywords:
                score += 0.25
                evidence.append("customer_keywords:" + ",".join(matched_customer_keywords[:3]))

            customer_text = (system.primary_customer or company.primary_customer).lower()
            if "department of defense" in customer_text and "defense" in budget_text:
                score += 0.15
                evidence.append("customer_family:defense")

            if score < min_score:
                continue

            matches.append(
                _build_match_record(
                    system,
                    company,
                    budget_line,
                    match_type="thematic_candidate",
                    match_score=min(score, 0.75),
                    match_confidence="candidate" if score < 0.55 else "medium",
                    evidence=evidence,
                )
            )

    deduped_matches: dict[tuple, dict] = {}
    for match in matches:
        key = (
            match["ticker"],
            match["system_name"],
            match["fiscal_year"],
            match["agency"],
            match["appropriation"],
            match["program_element"],
            match["line_item"],
        )
        existing = deduped_matches.get(key)
        if existing is None or match["match_score"] > existing["match_score"]:
            deduped_matches[key] = match
    return sorted(
        deduped_matches.values(),
        key=lambda record: (-record["match_score"], -record["amount_usd"], record["ticker"], record["system_name"]),
    )


def _dedupe_records(records: list[dict], key_fields: tuple[str, ...]) -> list[dict]:
    deduped: dict[tuple, dict] = {}
    for record in records:
        key = tuple(str(record.get(field, "")) for field in key_fields)
        deduped[key] = record
    return list(deduped.values())


def _latest_record_by_ticker(records: list[dict], *, date_field: str, fallback_field: str = "fetched_at") -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for record in records:
        ticker = str(record.get("ticker", "")).upper()
        if not ticker:
            continue
        current = latest.get(ticker)
        candidate_key = (str(record.get(date_field, "")), str(record.get(fallback_field, "")))
        if current is None or candidate_key > (
            str(current.get(date_field, "")),
            str(current.get(fallback_field, "")),
        ):
            latest[ticker] = record
    return latest


def build_company_scorecards(
    *,
    companies: list[CompanyRecord] | None = None,
    systems: list[SystemRecord] | None = None,
    processed_root: Path | None = None,
    min_budget_score: float = 0.35,
) -> dict:
    """Roll up processed records into watchlist scorecards and budget exposure matches."""
    company_rows = companies or load_company_watchlist()
    system_rows = systems or load_system_watchlist()
    root = processed_root or project_path("data", "processed")

    budget_lines = _dedupe_budget_lines(load_json_records(root / "budget_lines"))
    budget_matches = build_budget_exposure_matches(
        budget_lines,
        companies=company_rows,
        systems=system_rows,
        min_score=min_budget_score,
    )

    awards = _dedupe_records(
        load_json_records(root / "contract_awards"),
        ("ticker", "award_number", "source_url"),
    )
    sbir_awards = _dedupe_records(
        load_json_records(root / "sbir_awards"),
        ("ticker", "agency_tracking_number", "contract", "award_title", "source_url"),
    )
    pipeline_signals = _dedupe_records(
        load_json_records(root / "pipeline_signals"),
        ("ticker", "notice_id", "matched_keyword", "source_url"),
    )
    faa_signals = _dedupe_records(
        load_json_records(root / "faa_signals"),
        ("ticker", "signal_type", "source_url"),
    )
    procurement_signals = _dedupe_records(
        load_json_records(root / "sec_signals"),
        ("ticker", "signal_type", "matched_text", "source_url", "context"),
    )
    financial_latest = _latest_record_by_ticker(
        load_json_records(root / "financials"),
        date_field="report_date",
    )
    insider_trades = _dedupe_records(
        load_json_records(root / "insider_trades"),
        ("ticker", "accession_number", "transaction_date", "insider_name", "shares", "price_per_share"),
    )
    trl_signals = _dedupe_records(
        load_json_records(root / "trl_signals"),
        ("ticker", "system_name", "recorded_at", "trl_level"),
    )
    milestones = _dedupe_records(
        load_json_records(root / "program_milestones"),
        ("ticker", "system_name", "milestone_name", "expected_date"),
    )
    test_events = _dedupe_records(
        load_json_records(root / "test_events"),
        ("ticker", "system_name", "event_name", "event_date"),
    )

    systems_by_ticker: dict[str, list[SystemRecord]] = defaultdict(list)
    for system in system_rows:
        systems_by_ticker[system.ticker.upper()].append(system)

    scorecards: list[dict] = []
    for company in company_rows:
        ticker = company.ticker.upper()
        company_awards = [record for record in awards if str(record.get("ticker", "")).upper() == ticker]
        company_sbir_awards = [record for record in sbir_awards if str(record.get("ticker", "")).upper() == ticker]
        company_pipeline_signals = [record for record in pipeline_signals if str(record.get("ticker", "")).upper() == ticker]
        company_faa_signals = [record for record in faa_signals if str(record.get("ticker", "")).upper() == ticker]
        company_signals = [record for record in procurement_signals if str(record.get("ticker", "")).upper() == ticker]
        company_insiders = [record for record in insider_trades if str(record.get("ticker", "")).upper() == ticker]
        company_budget_matches = [record for record in budget_matches if str(record.get("ticker", "")).upper() == ticker]

        company_trl_signals = [record for record in trl_signals if str(record.get("ticker", "")).upper() == ticker]
        company_milestones = [record for record in milestones if str(record.get("ticker", "")).upper() == ticker]
        company_test_events = [record for record in test_events if str(record.get("ticker", "")).upper() == ticker]

        latest_financial = financial_latest.get(ticker, {})
        latest_trl_level = max(
            (int(record.get("trl_level", 0) or 0) for record in company_trl_signals),
            default=None,
        )

        insider_sale_value = round(
            sum(float(record.get("value_usd", 0.0) or 0.0) for record in company_insiders if record.get("transaction_code") == "S"),
            2,
        )
        insider_purchase_value = round(
            sum(float(record.get("value_usd", 0.0) or 0.0) for record in company_insiders if record.get("transaction_code") == "P"),
            2,
        )

        explicit_budget_matches = [record for record in company_budget_matches if record.get("match_confidence") == "explicit"]
        candidate_budget_matches = [record for record in company_budget_matches if record.get("match_confidence") != "explicit"]

        systems_summary = []
        for system in systems_by_ticker.get(ticker, []):
            system_name = system.system_name
            systems_summary.append(
                {
                    "system_name": system_name,
                    "domain": system.domain,
                    "current_status": system.current_status,
                    "latest_trl_level": max(
                        (
                            int(record.get("trl_level", 0) or 0)
                            for record in company_trl_signals
                            if record.get("system_name") == system_name
                        ),
                        default=None,
                    ),
                    "budget_match_count": sum(1 for record in company_budget_matches if record.get("system_name") == system_name),
                    "upcoming_milestone_count": sum(
                        1
                        for record in company_milestones
                        if record.get("system_name") == system_name and record.get("status") == "planned"
                    ),
                }
            )

        scorecards.append(
            {
                "company_name": company.company_name,
                "ticker": company.ticker,
                "priority": company.priority,
                "primary_domain": company.primary_domain,
                "primary_customer": company.primary_customer,
                "systems": systems_summary,
                "contract_award_count": len(company_awards),
                "contract_award_value_usd": round(
                    sum(float(record.get("obligated_value_usd", 0.0) or 0.0) for record in company_awards),
                    2,
                ),
                "sbir_award_count": len(company_sbir_awards),
                "sbir_award_value_usd": round(
                    sum(float(record.get("award_amount_usd", 0.0) or 0.0) for record in company_sbir_awards),
                    2,
                ),
                "sam_pipeline_signal_count": len(company_pipeline_signals),
                "sam_pipeline_high_priority_count": sum(
                    1 for record in company_pipeline_signals if record.get("priority") == "high"
                ),
                "faa_signal_count": len(company_faa_signals),
                "faa_high_priority_signal_count": sum(
                    1 for record in company_faa_signals if record.get("priority") == "high"
                ),
                "procurement_signal_count": len(company_signals),
                "high_priority_signal_count": sum(1 for record in company_signals if record.get("priority") == "high"),
                "latest_trl_level": latest_trl_level,
                "upcoming_milestone_count": sum(1 for record in company_milestones if record.get("status") == "planned"),
                "test_event_count": len(company_test_events),
                "latest_financial_report_date": latest_financial.get("report_date"),
                "est_runway_months": latest_financial.get("est_runway_months"),
                "going_concern_flag": latest_financial.get("going_concern_flag"),
                "insider_trade_count": len(company_insiders),
                "insider_sale_value_usd": insider_sale_value,
                "insider_purchase_value_usd": insider_purchase_value,
                "budget_match_count": len(company_budget_matches),
                "explicit_budget_exposure_usd": round(
                    sum(float(record.get("amount_usd", 0.0) or 0.0) for record in explicit_budget_matches),
                    2,
                ),
                "candidate_budget_exposure_usd": round(
                    sum(float(record.get("amount_usd", 0.0) or 0.0) for record in candidate_budget_matches),
                    2,
                ),
                "top_budget_matches": company_budget_matches[:5],
            }
        )

    scorecards.sort(
        key=lambda record: (
            {"high": 0, "medium": 1, "low": 2}.get(str(record.get("priority", "")).lower(), 3),
            record.get("ticker", ""),
        )
    )

    summary = {
        "tracked_companies": len(company_rows),
        "companies_with_budget_matches": sum(1 for record in scorecards if record["budget_match_count"] > 0),
        "explicit_budget_exposure_usd": round(sum(record["explicit_budget_exposure_usd"] for record in scorecards), 2),
        "candidate_budget_exposure_usd": round(sum(record["candidate_budget_exposure_usd"] for record in scorecards), 2),
        "total_contract_award_value_usd": round(sum(record["contract_award_value_usd"] for record in scorecards), 2),
        "total_sbir_award_value_usd": round(sum(record["sbir_award_value_usd"] for record in scorecards), 2),
        "total_sam_pipeline_signal_count": sum(record["sam_pipeline_signal_count"] for record in scorecards),
        "total_faa_signal_count": sum(record["faa_signal_count"] for record in scorecards),
    }

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "company_scorecards": scorecards,
        "budget_exposure_matches": budget_matches,
    }


def save_budget_exposure_matches(records: list[dict], *, label: str = "watchlist") -> Path:
    """Save normalized budget exposure matches into processed storage."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = ensure_directory(BUDGET_EXPOSURE_DIR) / f"budget_exposure_{slugify(label)}_{timestamp}.json"
    write_json(out_path, records)
    return out_path


def save_company_scorecards(bundle: dict, *, label: str = "watchlist") -> Path:
    """Save company scorecards into the dashboards folder."""
    out_path = ensure_directory(DASHBOARDS_DIR) / f"company_scorecards_{slugify(label)}.json"
    write_json(
        out_path,
        {
            "generated_at": bundle["generated_at"],
            "summary": bundle["summary"],
            "company_scorecards": bundle["company_scorecards"],
        },
    )
    return out_path
