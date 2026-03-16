"""
ClinicalTrials fetcher with WHO ICTRP and AACT fallbacks.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aact_fallback import search_aact_trials
from super_agents.biotech.io_utils import write_json
from super_agents.biotech.paths import RAW_CLINICALTRIALS_DIR, ensure_biotech_directory

RAW_DIR = RAW_CLINICALTRIALS_DIR
API_BASE = "https://clinicaltrials.gov/api/v2/studies"
WHO_ADVANCED_URL = "https://trialsearch.who.int/AdvSearch.aspx"
WHO_UNAVAILABLE_MARKER = RAW_DIR / "who_ictrp_unavailable.json"
USER_AGENT = os.getenv("CLINICALTRIALS_USER_AGENT", os.getenv("SEC_EDGAR_USER_AGENT", "BiotechTracker research@example.com"))
REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/json",
}
WHO_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Origin": "https://trialsearch.who.int",
    "Referer": WHO_ADVANCED_URL,
    "Sec-Ch-Ua": '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
}


def _safe_label(value: str) -> str:
    """Create a filesystem-safe label for cached raw responses."""
    return "".join(char if char.isalnum() else "_" for char in value)[:30] or "search"

def _load_cached_response(search_label: str) -> dict | None:
    """Load the latest cached raw response for a given search label."""
    safe_label = _safe_label(search_label)
    cached_files = sorted(RAW_DIR.glob(f"trials_{safe_label}_*.json"), key=lambda path: path.stat().st_mtime)
    if not cached_files:
        return None
    return json.loads(cached_files[-1].read_text(encoding="utf-8"))


def _request_json(url: str, params: dict, search_label: str) -> dict | None:
    """
    Fetch JSON from ClinicalTrials.gov.

    If the live service is blocked or unavailable, fall back to the latest
    cached response for the same search label when available.
    """
    try:
        response = httpx.get(
            url,
            params=params,
            headers=REQUEST_HEADERS,
            timeout=30,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        cached = _load_cached_response(search_label)
        if cached is not None:
            print(
                f"ClinicalTrials.gov returned HTTP {exc.response.status_code} for '{search_label}'. "
                "Using latest cached response."
            )
            return cached

        if exc.response.status_code == 403:
            print(
                f"ClinicalTrials.gov returned HTTP 403 for '{search_label}'. "
                "No cached response is available; trying fallback sources."
            )
            return None
        raise
    except httpx.RequestError as exc:
        cached = _load_cached_response(search_label)
        if cached is not None:
            print(
                f"ClinicalTrials.gov request failed for '{search_label}' ({exc}). "
                "Using latest cached response."
            )
            return cached

        print(f"ClinicalTrials.gov request failed for '{search_label}' ({exc}). Trying fallback sources.")
        return None


def search_trials(
    sponsor: str | None = None,
    nct_id: str | None = None,
    condition: str | None = None,
    intervention: str | None = None,
    phase: str | None = None,
    status: str | None = None,
    page_size: int = 50,
) -> list[dict]:
    """Search ClinicalTrials.gov with fallback sources when needed."""
    ensure_biotech_directory(RAW_DIR)

    params = {
        "format": "json",
        "pageSize": page_size,
    }

    search_label = nct_id or sponsor or condition or intervention or "search"

    if nct_id:
        url = f"{API_BASE}/{nct_id}"
        data = _request_json(url, {"format": "json"}, search_label)
    else:
        if sponsor:
            params["query.spons"] = sponsor
        if condition:
            params["query.cond"] = condition
        if intervention:
            params["query.intr"] = intervention
        if phase:
            params["filter.advanced"] = f"AREA[Phase]{phase}"
        if status:
            params["filter.overallStatus"] = status

        data = _request_json(API_BASE, params, search_label)

    if data is not None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = _safe_label(search_label)
        raw_path = RAW_DIR / f"trials_{safe_label}_{timestamp}.json"
        _write_json(raw_path, data)

        if nct_id:
            studies = [data] if "protocolSection" in data else []
        else:
            studies = data.get("studies", [])

        transformed = _transform_trials(studies)
        if transformed:
            return transformed

        print(f"ClinicalTrials.gov returned 0 trials for '{search_label}'. Trying fallback sources.")

    return _search_fallback_sources(
        sponsor=sponsor,
        nct_id=nct_id,
        condition=condition,
        intervention=intervention,
        phase=phase,
        status=status,
        page_size=page_size,
        search_label=search_label,
    )


def _search_fallback_sources(
    sponsor: str | None,
    nct_id: str | None,
    condition: str | None,
    intervention: str | None,
    phase: str | None,
    status: str | None,
    page_size: int,
    search_label: str,
) -> list[dict]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = _safe_label(search_label)

    who_trials = _search_who_ictrp(
        sponsor=sponsor,
        nct_id=nct_id,
        condition=condition,
        intervention=intervention,
        page_size=page_size,
    )
    if who_trials:
        who_path = RAW_DIR / f"who_ictrp_{safe_label}_{timestamp}.json"
        _write_json(who_path, {"source": "WHO ICTRP", "results": who_trials})
        print(f"WHO ICTRP fallback returned {len(who_trials)} trials for '{search_label}'.")
        return who_trials

    aact_trials = search_aact_trials(
        sponsor=sponsor,
        nct_id=nct_id,
        condition=condition,
        intervention=intervention,
        phase=phase,
        status=status,
        page_size=page_size,
    )
    if aact_trials:
        aact_path = RAW_DIR / f"aact_{safe_label}_{timestamp}.json"
        _write_json(aact_path, {"source": "AACT", "results": aact_trials})
        print(f"AACT fallback returned {len(aact_trials)} trials for '{search_label}'.")
    else:
        print(f"No fallback trials were found for '{search_label}'.")
    return aact_trials


def _search_who_ictrp(
    sponsor: str | None,
    nct_id: str | None,
    condition: str | None,
    intervention: str | None,
    page_size: int,
) -> list[dict]:
    if _who_unavailable_today():
        return []

    if nct_id:
        return []

    if not sponsor and not condition and not intervention:
        return []

    try:
        with httpx.Client(headers=WHO_REQUEST_HEADERS, follow_redirects=True, timeout=30) as client:
            response = client.get(WHO_ADVANCED_URL)
            response.raise_for_status()

            fields = _extract_who_form_fields(response.text)
            if sponsor:
                fields["ctl00$ContentPlaceHolder1$txtPrimarySponsor"] = sponsor
            if condition:
                fields["ctl00$ContentPlaceHolder1$txtCondition"] = condition
            if intervention:
                fields["ctl00$ContentPlaceHolder1$txtIntervention"] = intervention
            fields["ctl00$ContentPlaceHolder1$btnSearch"] = "Search"

            result = client.post(WHO_ADVANCED_URL, data=fields)
            if result.status_code == 403:
                _mark_who_unavailable(
                    reason="HTTP 403 from WHO ICTRP advanced search",
                    status_code=result.status_code,
                )
                return []

            result.raise_for_status()
            if "NoAccess.aspx" in str(result.url):
                _mark_who_unavailable(reason="WHO ICTRP redirected the advanced search request to NoAccess.aspx")
                return []

            trials = _parse_who_result_page(result.text, sponsor=sponsor or "", condition=condition or "")
            return trials[:page_size]
    except httpx.HTTPError as exc:
        print(f"WHO ICTRP fallback request failed: {exc}")
    except Exception as exc:
        print(f"WHO ICTRP fallback failed: {exc}")
    return []


def _extract_who_form_fields(html: str) -> dict[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.find("form")
    if form is None:
        raise RuntimeError("WHO ICTRP advanced search form was not found.")

    fields: dict[str, str] = {}
    for element in form.find_all(["input", "select", "textarea"]):
        name = element.get("name")
        if not name:
            continue

        tag = element.name
        if tag == "input":
            input_type = (element.get("type") or "text").lower()
            if input_type in {"checkbox", "radio"}:
                if element.has_attr("checked"):
                    fields[name] = element.get("value", "on")
            elif input_type not in {"submit", "button", "image", "file"}:
                fields[name] = element.get("value", "")
        elif tag == "select":
            selected = element.find("option", selected=True) or element.find("option")
            fields[name] = selected.get("value", "") if selected else ""
        elif tag == "textarea":
            fields[name] = element.text or ""

    return fields


def _parse_who_result_page(html: str, sponsor: str, condition: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    if "No results were found." in soup.get_text(" ", strip=True):
        return []

    trials: list[dict] = []
    seen_ids: set[str] = set()
    for link in soup.select('a[href*="Trial2.aspx?TrialID="]'):
        row = link.find_parent("tr")
        if row is None:
            continue

        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        main_id = cells[1].get_text(" ", strip=True)
        title = link.get_text(" ", strip=True)
        if not main_id or main_id in seen_ids:
            continue

        seen_ids.add(main_id)
        results_available = len(cells) > 4 and cells[4].get_text(" ", strip=True).lower() == "yes"
        trials.append(
            {
                "nct_id": main_id,
                "title": title,
                "phase": "",
                "status": cells[0].get_text(" ", strip=True),
                "sponsor": sponsor,
                "indication": condition,
                "primary_endpoint": "",
                "estimated_primary_completion": "",
                "estimated_study_completion": "",
                "results_posted": results_available,
                "source_url": urljoin(WHO_ADVANCED_URL, link.get("href", "")),
                "source_type": "WHO ICTRP",
                "source_confidence": "secondary",
            }
        )

    return trials


def _who_unavailable_today() -> bool:
    if not WHO_UNAVAILABLE_MARKER.exists():
        return False

    try:
        payload = json.loads(WHO_UNAVAILABLE_MARKER.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False

    return payload.get("date") == date.today().isoformat()


def _mark_who_unavailable(reason: str, status_code: int | None = None) -> None:
    payload = {
        "date": date.today().isoformat(),
        "status_code": status_code,
        "reason": reason,
        "marked_at": datetime.now().isoformat(),
    }
    _write_json(WHO_UNAVAILABLE_MARKER, payload)
    print(f"WHO ICTRP fallback is unavailable from this environment: {reason}")


def _transform_trials(studies: list[dict]) -> list[dict]:
    """Transform ClinicalTrials.gov studies into clinical_trials format."""
    trials = []
    for study in studies:
        protocol = study.get("protocolSection", {})
        id_module = protocol.get("identificationModule", {})
        status_module = protocol.get("statusModule", {})
        design_module = protocol.get("designModule", {})
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        conditions_module = protocol.get("conditionsModule", {})
        outcomes_module = protocol.get("outcomesModule", {})
        results_section = study.get("resultsSection")

        primary_outcomes = outcomes_module.get("primaryOutcomes", [])
        primary_endpoint = primary_outcomes[0].get("measure", "") if primary_outcomes else ""

        primary_completion = status_module.get("primaryCompletionDateStruct", {}).get("date", "")
        study_completion = status_module.get("completionDateStruct", {}).get("date", "")

        trial = {
            "nct_id": id_module.get("nctId", ""),
            "title": id_module.get("briefTitle", ""),
            "phase": ",".join(design_module.get("phases", [])),
            "status": status_module.get("overallStatus", ""),
            "sponsor": sponsor_module.get("leadSponsor", {}).get("name", ""),
            "indication": ", ".join(conditions_module.get("conditions", [])),
            "primary_endpoint": primary_endpoint,
            "estimated_primary_completion": primary_completion,
            "estimated_study_completion": study_completion,
            "results_posted": results_section is not None,
            "source_url": f"https://clinicaltrials.gov/study/{id_module.get('nctId', '')}",
            "source_type": "ClinicalTrials.gov",
            "source_confidence": "primary",
        }
        trials.append(trial)

    return trials


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch clinical trials with fallback sources")
    parser.add_argument("--sponsor", type=str, help="Lead sponsor name")
    parser.add_argument("--nct", type=str, help="NCT ID for direct lookup")
    parser.add_argument("--condition", type=str, help="Condition/disease")
    parser.add_argument("--phase", type=str, help="Phase filter (e.g., PHASE3)")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    results = search_trials(
        sponsor=args.sponsor,
        nct_id=args.nct,
        condition=args.condition,
        phase=args.phase,
        page_size=args.limit,
    )
    print(f"Found {len(results)} trials")
    for trial in results[:5]:
        print(f"  {trial['nct_id']} | {trial['phase']} | {trial['status']} | {trial['title'][:60]}")
