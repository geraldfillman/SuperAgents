"""Tests for the optional MiroFish runtime integration."""

from __future__ import annotations

import json
import shutil
import uuid
from contextlib import contextmanager
from pathlib import Path

from super_agents.integrations.mirofish.bundle import (
    MiroFishBundleSpec,
    create_bundle_from_spec,
    read_bundle,
)
from super_agents.integrations.mirofish.zep import (
    build_bundle_import_manifest,
    summarize_bundle_activity,
)
from super_agents.integrations.mirofish.runtime import (
    LLM_API_KEY_ENV,
    build_run_command,
    check_runtime,
)
from super_agents.integrations.mirofish.status import read_runtime_status, send_close_command


@contextmanager
def _workspace_temp_dir(prefix: str):
    root = Path.cwd() / f".tmp_{prefix}_{uuid.uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_create_bundle_from_spec_writes_expected_files():
    with _workspace_temp_dir("mirofish_bundle") as root:
        spec = MiroFishBundleSpec.from_mapping(
            {
                "simulation_id": "sim_test_bundle",
                "project_id": "proj_test_bundle",
                "graph_id": "graph_test_bundle",
                "simulation_requirement": "Model a short product launch discussion.",
                "agent_profiles": [
                    {
                        "name": "Alice Analyst",
                        "username": "alice_analyst",
                        "bio": "Covers product launches for institutional investors.",
                        "persona": "Asks skeptical questions and posts detailed threads.",
                        "interested_topics": ["earnings", "launches"],
                        "stance": "observer",
                    },
                    {
                        "name": "Bob Builder",
                        "bio": "Follows developer feedback and community adoption.",
                        "persona": "Amplifies high-signal community sentiment.",
                        "gender": "male",
                        "age": 28,
                    },
                ],
                "event_config": {
                    "initial_posts": [
                        {"poster_agent_id": 0, "content": "Launch day sentiment is mixed so far."}
                    ]
                },
            }
        )

        bundle_dir = create_bundle_from_spec(spec, root / "bundle")

        summary = read_bundle(bundle_dir)
        assert summary["simulation_id"] == "sim_test_bundle"
        assert summary["agent_count"] == 2
        assert summary["has_twitter_profiles"] is True
        assert summary["has_reddit_profiles"] is True

        config = json.loads((bundle_dir / "simulation_config.json").read_text(encoding="utf-8"))
        assert config["graph_id"] == "graph_test_bundle"
        assert config["agent_configs"][0]["entity_name"] == "Alice Analyst"
        assert config["event_config"]["initial_posts"][0]["poster_agent_id"] == 0

        reddit_profiles = json.loads((bundle_dir / "reddit_profiles.json").read_text(encoding="utf-8"))
        assert reddit_profiles[1]["user_id"] == 1
        assert reddit_profiles[1]["gender"] == "male"

        twitter_csv = (bundle_dir / "twitter_profiles.csv").read_text(encoding="utf-8").splitlines()
        assert twitter_csv[0] == "user_id,name,username,user_char,description"
        assert "Alice Analyst" in twitter_csv[1]


def test_runtime_helpers_accept_explicit_runtime_checkout():
    with _workspace_temp_dir("mirofish_runtime") as root:
        runtime_home = root / "MiroFish"
        scripts_dir = runtime_home / "backend" / "scripts"
        scripts_dir.mkdir(parents=True)
        for script_name in (
            "run_parallel_simulation.py",
            "run_twitter_simulation.py",
            "run_reddit_simulation.py",
        ):
            (scripts_dir / script_name).write_text("print('stub runtime')\n", encoding="utf-8")

        bundle_dir = root / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "simulation_config.json").write_text("{}", encoding="utf-8")

        runtime_info = check_runtime(runtime_home)
        assert Path(runtime_info["runtime_home"]) == runtime_home.resolve()
        assert runtime_info["runner_scripts"]["parallel"].endswith("run_parallel_simulation.py")
        assert runtime_info["config_ready"] is False
        assert runtime_info["runnable"] is False
        assert runtime_info["config_errors"]

        twitter_command = build_run_command(bundle_dir, runtime_home=runtime_home, platform="twitter")
        assert "--twitter-only" not in twitter_command
        assert twitter_command[-2:] == ["--config", str((bundle_dir / "simulation_config.json").resolve())]


def test_runtime_helpers_flag_env_example_and_accept_env_overrides():
    with _workspace_temp_dir("mirofish_runtime_env") as root:
        runtime_home = root / "MiroFish"
        scripts_dir = runtime_home / "backend" / "scripts"
        scripts_dir.mkdir(parents=True)
        for script_name in (
            "run_parallel_simulation.py",
            "run_twitter_simulation.py",
            "run_reddit_simulation.py",
        ):
            (scripts_dir / script_name).write_text("print('stub runtime')\n", encoding="utf-8")

        (runtime_home / ".env.example").write_text(
            "\n".join(
                [
                    "LLM_API_KEY=your_api_key_here",
                    "LLM_BASE_URL=https://api.openai.com/v1",
                    "LLM_MODEL_NAME=gpt-4o-mini",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        placeholder_info = check_runtime(runtime_home)
        assert placeholder_info["config_ready"] is False
        assert placeholder_info["example_env_file"].endswith(".env.example")
        assert any(".env.example" in warning for warning in placeholder_info["config_warnings"])

        configured_info = check_runtime(runtime_home, env={LLM_API_KEY_ENV: "test-key"})
        assert configured_info["config_ready"] is True
        assert configured_info["config_errors"] == []
        assert configured_info["api_key_source"] == "environment"


def test_status_helpers_report_bundle_and_write_close_command():
    with _workspace_temp_dir("mirofish_status") as root:
        bundle_dir = root / "bundle"
        bundle_dir.mkdir()
        (bundle_dir / "simulation_config.json").write_text(
            json.dumps({"simulation_id": "sim_status", "agent_configs": [{"agent_id": 0}]}),
            encoding="utf-8",
        )
        (bundle_dir / "run_state.json").write_text(
            json.dumps({"runner_status": "running", "current_round": 3}),
            encoding="utf-8",
        )
        (bundle_dir / "env_status.json").write_text(
            json.dumps({"status": "alive"}),
            encoding="utf-8",
        )

        status = read_runtime_status(bundle_dir)
        assert status["simulation_id"] == "sim_status"
        assert status["run_state"]["runner_status"] == "running"
        assert status["env_status"]["status"] == "alive"

        close_result = send_close_command(bundle_dir, timeout=12.5)
        command = json.loads(Path(close_result["command_path"]).read_text(encoding="utf-8"))
        assert command["command_type"] == "close_env"
        assert command["requested_timeout"] == 12.5


def test_summarize_bundle_activity_counts_meaningful_actions():
    with _workspace_temp_dir("mirofish_zep_summary") as root:
        bundle_dir = root / "bundle"
        (bundle_dir / "twitter").mkdir(parents=True)
        (bundle_dir / "reddit").mkdir(parents=True)
        (bundle_dir / "simulation_config.json").write_text(
            json.dumps(
                {
                    "simulation_id": "sim_summary",
                    "project_id": "proj_summary",
                    "graph_id": "graph_summary",
                    "simulation_requirement": "Track a simple cascade.",
                    "time_config": {"total_simulation_hours": 6, "minutes_per_round": 60},
                    "agent_configs": [{"entity_name": "Agent A", "entity_type": "Analyst"}],
                }
            ),
            encoding="utf-8",
        )
        (bundle_dir / "twitter" / "actions.jsonl").write_text(
            "\n".join(
                [
                    json.dumps({"event_type": "simulation_start", "platform": "twitter", "total_rounds": 6}),
                    json.dumps({"round": 0, "agent_id": 0, "agent_name": "Agent A", "action_type": "CREATE_POST", "timestamp": "2026-03-15T12:00:00"}),
                    json.dumps({"round": 1, "agent_id": 0, "agent_name": "Agent A", "action_type": "QUOTE_POST", "timestamp": "2026-03-15T13:00:00"}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (bundle_dir / "reddit" / "actions.jsonl").write_text(
            json.dumps({"round": 1, "agent_id": 0, "agent_name": "Agent A", "action_type": "CREATE_COMMENT", "timestamp": "2026-03-15T13:05:00"})
            + "\n",
            encoding="utf-8",
        )

        summary = summarize_bundle_activity(bundle_dir)
        assert summary["action_counts"] == {"twitter": 2, "reddit": 1}
        assert summary["event_counts"]["twitter"] == 3
        assert summary["platforms"] == ["reddit", "twitter"]
        assert summary["max_round"] == 1
        assert summary["total_rounds"] == 6
        assert summary["recent_actions"][-1]["action_type"] == "CREATE_COMMENT"


def test_build_bundle_import_manifest_preserves_ids_and_updates_graph():
    with _workspace_temp_dir("mirofish_zep_manifest") as root:
        bundle_dir = root / "bundle"
        (bundle_dir / "twitter").mkdir(parents=True)
        (bundle_dir / "reddit").mkdir(parents=True)
        (bundle_dir / "simulation_config.json").write_text(
            json.dumps(
                {
                    "simulation_id": "sim_manifest",
                    "project_id": "proj_manifest",
                    "graph_id": "graph_old",
                    "simulation_requirement": "Model a propagated signal.",
                    "time_config": {"total_simulation_hours": 4, "minutes_per_round": 60},
                    "agent_configs": [
                        {"entity_name": "Agent A", "entity_type": "SectorAgent"},
                        {"entity_name": "Agent B", "entity_type": "SectorAgent"},
                    ],
                }
            ),
            encoding="utf-8",
        )
        (bundle_dir / "twitter" / "actions.jsonl").write_text(
            json.dumps({"round": 2, "agent_id": 0, "agent_name": "Agent A", "action_type": "CREATE_POST", "timestamp": "2026-03-15T12:00:00"})
            + "\n",
            encoding="utf-8",
        )

        manifest = build_bundle_import_manifest(
            bundle_dir,
            graph_id="graph_new",
            graph_name="Imported Cascade",
            imported_at="2026-03-15T21:00:00",
        )

        assert manifest["graph_id"] == "graph_new"
        assert manifest["graph_name"] == "Imported Cascade"
        assert manifest["project"]["project_id"] == "proj_manifest"
        assert manifest["simulation"]["simulation_id"] == "sim_manifest"
        assert manifest["config"]["graph_id"] == "graph_new"
        assert manifest["simulation"]["status"] == "completed"
        assert manifest["run_state"]["runner_status"] == "completed"
        assert manifest["summary"]["agent_count"] == 2
        assert manifest["summary"]["action_counts"]["twitter"] == 1
