"""Tests for shared dashboard data helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from dashboards import dashboard_data
from super_agents import cli

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_dashboard_discovery_matches_cli_registry():
    discovered = {
        agent["name"] for agent in dashboard_data.discover_runnable_agents(PROJECT_ROOT)
    }
    assert discovered == set(cli.AGENTS)


def test_dashboard_artifact_loaders_support_custom_paths():
    test_root = PROJECT_ROOT / ".pytest-dashboard-data-artifacts"
    shutil.rmtree(test_root, ignore_errors=True)
    dashboards_dir = test_root / "dashboards"
    dashboards_dir.mkdir(parents=True)

    try:
        status_payload = {
            "agent_name": "biotech",
            "task_name": "fetch_drug_approvals",
            "status": "running",
            "progress": {"completed": 1, "total": 2},
        }
        latest_payload = {
            "agent_name": "biotech",
            "task_name": "fetch_drug_approvals",
            "status": "completed",
            "completed_at": "2026-03-15T07:00:42",
            "outputs": {"records_written": 3, "files_written": 1},
            "findings": [{"severity": "info", "summary": "One update"}],
        }
        findings_payload = [
            {
                "finding_time": "2026-03-15T07:00:42",
                "finding_type": "approval_granted",
                "summary": "Approval confirmed",
                "action_required": False,
            }
        ]

        (dashboards_dir / "biotech_current_status.json").write_text(
            json.dumps(status_payload),
            encoding="utf-8",
        )
        (dashboards_dir / "biotech_run_latest.json").write_text(
            json.dumps(latest_payload),
            encoding="utf-8",
        )
        (dashboards_dir / "biotech_findings_latest.json").write_text(
            json.dumps(findings_payload),
            encoding="utf-8",
        )

        run_dir = dashboards_dir / "runs" / "biotech" / "20260315_070000"
        run_dir.mkdir(parents=True)
        (run_dir / "summary.json").write_text(json.dumps(latest_payload), encoding="utf-8")
        (run_dir / "summary.md").write_text("# Run Summary", encoding="utf-8")

        assert dashboard_data.load_agent_status("biotech", dashboards_dir)["status"] == "running"
        assert (
            dashboard_data.load_agent_latest_run("biotech", dashboards_dir)["status"] == "completed"
        )
        assert (
            dashboard_data.load_agent_findings("biotech", dashboards_dir)[0]["summary"]
            == "Approval confirmed"
        )

        findings = dashboard_data.load_all_findings(["biotech"], dashboards_dir=dashboards_dir)
        assert findings[0]["_agent"] == "biotech"

        runs = dashboard_data.load_all_runs(dashboards_dir / "runs")
        assert runs[0]["_md_path"] == run_dir / "summary.md"
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


def test_load_calendar_events_filters_non_mapping_items():
    test_root = PROJECT_ROOT / ".pytest-dashboard-data-calendars"
    shutil.rmtree(test_root, ignore_errors=True)
    dashboards_dir = test_root / "dashboards"
    dashboards_dir.mkdir(parents=True)

    try:
        (dashboards_dir / "biotech_catalyst_calendar.json").write_text(
            json.dumps(
                [
                    {"date": "2026-03-20", "ticker": "ABCD"},
                    "not-a-dict",
                    {"date": "2026-03-18", "ticker": "WXYZ"},
                ]
            ),
            encoding="utf-8",
        )

        events = dashboard_data.load_calendar_events("*catalyst_calendar*.json", dashboards_dir)

        assert [event["ticker"] for event in events] == ["WXYZ", "ABCD"]
    finally:
        shutil.rmtree(test_root, ignore_errors=True)


def test_simulation_bundle_helpers_support_custom_paths():
    test_root = PROJECT_ROOT / ".pytest-dashboard-data-simulations"
    shutil.rmtree(test_root, ignore_errors=True)
    processed_dir = test_root / "data" / "processed" / "mirofish_simulations"
    bundle_dir = processed_dir / "sim_cross_sector_signal_cascade"
    (bundle_dir / "twitter").mkdir(parents=True)
    (bundle_dir / "reddit").mkdir(parents=True)

    try:
        (bundle_dir / "simulation_config.json").write_text(
            json.dumps(
                {
                    "simulation_id": "sim_cross_sector_signal_cascade",
                    "project_id": "proj_cross_sector_signal_cascade",
                    "graph_id": "graph_cross_sector_signal_cascade",
                    "simulation_requirement": "Model a simple cascade.",
                    "agent_configs": [
                        {"entity_name": "Aero Cascade Scout", "entity_type": "AerospaceAgent"},
                        {"entity_name": "Renewable Cost Watcher", "entity_type": "EnergyAgent"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (bundle_dir / "twitter" / "actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"event_type": "simulation_start", "platform": "twitter", "total_rounds": 6}),
                    json.dumps(
                        {
                            "round": 0,
                            "agent_id": 0,
                            "agent_name": "Aero Cascade Scout",
                            "action_type": "CREATE_POST",
                            "timestamp": "2026-03-15T20:00:00",
                        }
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (bundle_dir / "reddit" / "actions.jsonl").write_text(
            json.dumps(
                {
                    "round": 1,
                    "agent_id": 1,
                    "agent_name": "Renewable Cost Watcher",
                    "action_type": "CREATE_COMMENT",
                    "timestamp": "2026-03-15T20:05:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (bundle_dir / "zep_publish_result.json").write_text(
            json.dumps(
                {
                    "graph_id": "mirofish_test_graph",
                    "process_url": "http://127.0.0.1:3000/process/proj_cross_sector_signal_cascade",
                    "simulation_url": "http://127.0.0.1:3000/simulation/sim_cross_sector_signal_cascade",
                    "graph_data": {"node_count": 12, "edge_count": 14},
                    "summary": {"agent_count": 2},
                }
            ),
            encoding="utf-8",
        )
        (bundle_dir / "zep_import.json").write_text(
            json.dumps(
                {
                    "imported_at": "2026-03-15T20:25:35",
                    "graph_id": "mirofish_test_graph",
                    "project_id": "proj_cross_sector_signal_cascade",
                    "simulation_id": "sim_cross_sector_signal_cascade",
                }
            ),
            encoding="utf-8",
        )

        bundle = dashboard_data.load_simulation_bundle(bundle_dir)
        assert bundle["published"] is True
        assert bundle["graph_id"] == "mirofish_test_graph"
        assert bundle["action_counts"] == {"twitter": 1, "reddit": 1}
        assert bundle["node_count"] == 12
        assert bundle["process_url"].endswith("/process/proj_cross_sector_signal_cascade")
        assert (
            dashboard_data.build_mirofish_embed_url(bundle["process_url"])
            == "http://127.0.0.1:3000/process/proj_cross_sector_signal_cascade?embed=1&lang=en"
        )

        bundles = dashboard_data.discover_simulation_bundles(processed_dir)
        assert [item["simulation_id"] for item in bundles] == ["sim_cross_sector_signal_cascade"]

        command = dashboard_data.build_mirofish_publish_command(bundle_dir)
        assert command[-3:] == [str(bundle_dir.resolve()), "--json", "--force"]
    finally:
        shutil.rmtree(test_root, ignore_errors=True)
