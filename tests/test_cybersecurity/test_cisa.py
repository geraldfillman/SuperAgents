from __future__ import annotations

from datetime import date

import httpx

from super_agents.cybersecurity.calendar import build_patch_calendar
from super_agents.cybersecurity.cisa import (
    build_findings,
    fetch_kev_catalog,
    normalize_kev_catalog,
    select_recent_records,
)
from super_agents.cybersecurity.watchlist import AssetRecord


def test_fetch_kev_catalog_accepts_injected_client():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(200, json={"vulnerabilities": []})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = fetch_kev_catalog(client=client)

    assert payload == {"vulnerabilities": []}


def test_normalize_kev_catalog_marks_watchlist_and_severity():
    payload = {
        "vulnerabilities": [
            {
                "cveID": "CVE-2025-0282",
                "vendorProject": "Ivanti",
                "product": "Connect Secure",
                "vulnerabilityName": "Command Injection",
                "shortDescription": "Example vulnerability",
                "requiredAction": "Apply vendor update",
                "dateAdded": "2026-03-14",
                "dueDate": "2026-03-20",
                "knownRansomwareCampaignUse": "Known",
                "notes": "",
            }
        ]
    }
    assets = [AssetRecord(vendor="Ivanti", product="Connect Secure", priority="critical")]

    records = normalize_kev_catalog(payload, assets=assets)

    assert len(records) == 1
    assert records[0]["watchlist_match"] is True
    assert records[0]["severity"] == "critical"
    assert records[0]["cve_id"] == "CVE-2025-0282"


def test_select_recent_records_filters_by_date_window():
    records = [
        {"cve_id": "CVE-1", "date_added": "2026-03-14"},
        {"cve_id": "CVE-2", "date_added": "2026-02-01"},
    ]

    recent = select_recent_records(records, days=14, reference_date=date(2026, 3, 15))

    assert [record["cve_id"] for record in recent] == ["CVE-1"]


def test_build_findings_and_patch_calendar_use_normalized_records():
    records = [
        {
            "cve_id": "CVE-2025-0282",
            "asset": "Ivanti Connect Secure",
            "vendor": "Ivanti",
            "product": "Connect Secure",
            "required_action": "Apply vendor update",
            "date_added": "2026-03-14",
            "due_date": "2026-03-20",
            "severity": "critical",
            "source_url": "https://example.test/kev",
            "source_confidence": "primary",
            "watchlist_match": True,
            "summary": "Tracked KEV item",
            "finding_type": "known_exploited_vulnerability",
            "finding_time": "2026-03-14",
        }
    ]

    findings = build_findings(records, limit=5)
    events = build_patch_calendar(records, window_days=10, reference_date=date(2026, 3, 15))

    assert findings[0]["cve_id"] == "CVE-2025-0282"
    assert findings[0]["watchlist_match"] is True
    assert events[0]["event_type"] == "patch_due"
    assert events[0]["date"] == "2026-03-20"
