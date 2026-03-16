from __future__ import annotations

import shutil
from pathlib import Path

from super_agents.cybersecurity.watchlist import find_asset, load_asset_watchlist, load_org_watchlist


def _workspace_temp_dir(label: str) -> Path:
    root = Path("tests") / ".tmp_cybersecurity" / label
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_load_asset_watchlist_from_custom_path():
    csv_path = _workspace_temp_dir("asset_watchlist") / "assets.csv"
    csv_path.write_text(
        "vendor,product,cve_id,priority,notes\n"
        "Ivanti,Connect Secure,,critical,Edge appliance\n"
        ",,CVE-2025-0282,high,Specific CVE\n",
        encoding="utf-8",
    )

    assets = load_asset_watchlist(csv_path)

    assert len(assets) == 2
    assert assets[0].vendor == "Ivanti"
    assert assets[1].cve_id == "CVE-2025-0282"


def test_find_asset_matches_by_cve_id():
    csv_path = _workspace_temp_dir("find_asset") / "assets.csv"
    csv_path.write_text(
        "vendor,product,cve_id,priority,notes\n"
        ",,CVE-2025-0282,critical,Specific CVE\n",
        encoding="utf-8",
    )

    assets = load_asset_watchlist(csv_path)
    match = find_asset(cve_id="CVE-2025-0282", assets=assets)

    assert match is not None
    assert match.priority == "critical"


def test_load_org_watchlist_from_custom_path():
    csv_path = _workspace_temp_dir("org_watchlist") / "orgs.csv"
    csv_path.write_text(
        "company_name,ticker,cik,primary_focus,priority,notes\n"
        "CrowdStrike,CRWD,1535527,endpoint security,high,Representative vendor\n",
        encoding="utf-8",
    )

    orgs = load_org_watchlist(csv_path)

    assert len(orgs) == 1
    assert orgs[0].company_name == "CrowdStrike"
    assert orgs[0].ticker == "CRWD"
