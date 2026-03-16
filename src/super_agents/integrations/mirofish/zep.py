"""Helpers for publishing Super_Agents MiroFish bundles into Zep-backed MiroFish projects."""

from __future__ import annotations

import importlib
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .runtime import resolve_runtime_home

PROJECT_ROOT = Path(__file__).resolve().parents[4]
ACTION_LOGS = {
    "twitter": Path("twitter") / "actions.jsonl",
    "reddit": Path("reddit") / "actions.jsonl",
}
OPTIONAL_BUNDLE_FILES = (
    Path("simulation.log"),
    Path("reddit_profiles.json"),
    Path("twitter_profiles.csv"),
    Path("twitter_simulation.db"),
    Path("reddit_simulation.db"),
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        records.append(json.loads(stripped))
    return records


def _meaningful_actions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [record for record in records if "action_type" in record]


def _max_round(records: list[dict[str, Any]]) -> int:
    rounds = [
        int(record.get("round_num", record.get("round", 0)))
        for record in records
        if "round" in record or "round_num" in record
    ]
    return max(rounds, default=0)


def _total_rounds_from_records(records: list[dict[str, Any]]) -> int | None:
    for record in records:
        if record.get("event_type") == "simulation_start" and record.get("total_rounds") is not None:
            return int(record["total_rounds"])
    return None


def _normalize_timestamp(value: str | None) -> str:
    if value:
        return value
    return datetime.now().isoformat()


def _import_backend_symbols(runtime_home: Path) -> dict[str, Any]:
    backend_root = runtime_home / "backend"
    backend_root_str = str(backend_root.resolve())
    if backend_root_str not in sys.path:
        sys.path.insert(0, backend_root_str)

    config_module = importlib.import_module("app.config")
    graph_builder_module = importlib.import_module("app.services.graph_builder")
    project_module = importlib.import_module("app.models.project")
    simulation_manager_module = importlib.import_module("app.services.simulation_manager")
    simulation_runner_module = importlib.import_module("app.services.simulation_runner")
    zep_updater_module = importlib.import_module("app.services.zep_graph_memory_updater")

    return {
        "Config": config_module.Config,
        "GraphBuilderService": graph_builder_module.GraphBuilderService,
        "Project": project_module.Project,
        "ProjectManager": project_module.ProjectManager,
        "ProjectStatus": project_module.ProjectStatus,
        "SimulationManager": simulation_manager_module.SimulationManager,
        "SimulationState": simulation_manager_module.SimulationState,
        "SimulationStatus": simulation_manager_module.SimulationStatus,
        "SimulationRunner": simulation_runner_module.SimulationRunner,
        "SimulationRunState": simulation_runner_module.SimulationRunState,
        "RunnerStatus": simulation_runner_module.RunnerStatus,
        "AgentAction": simulation_runner_module.AgentAction,
        "ZepGraphMemoryUpdater": zep_updater_module.ZepGraphMemoryUpdater,
    }


def summarize_bundle_activity(bundle_dir: str | Path) -> dict[str, Any]:
    """Return a compact summary of bundle actions for each platform."""

    bundle_path = Path(bundle_dir).resolve()
    if not (bundle_path / "simulation_config.json").exists():
        raise FileNotFoundError(f"Missing simulation_config.json in {bundle_path}")

    platform_records = {
        platform: _iter_jsonl(bundle_path / relative_path)
        for platform, relative_path in ACTION_LOGS.items()
    }
    meaningful = {
        platform: _meaningful_actions(records)
        for platform, records in platform_records.items()
    }
    combined_actions = [
        {**record, "platform": record.get("platform") or platform}
        for platform, records in meaningful.items()
        for record in records
    ]
    combined_actions.sort(key=lambda record: (_normalize_timestamp(record.get("timestamp")), record.get("agent_id", 0)))

    total_rounds = next(
        (
            rounds
            for rounds in (_total_rounds_from_records(records) for records in platform_records.values())
            if rounds is not None
        ),
        None,
    )

    return {
        "platforms": sorted(platform for platform, records in meaningful.items() if records),
        "action_counts": {platform: len(records) for platform, records in meaningful.items()},
        "event_counts": {platform: len(records) for platform, records in platform_records.items()},
        "max_round_per_platform": {platform: _max_round(records) for platform, records in meaningful.items()},
        "max_round": max((_max_round(records) for records in meaningful.values()), default=0),
        "total_rounds": total_rounds,
        "recent_actions": combined_actions[-10:],
    }


def build_bundle_import_manifest(
    bundle_dir: str | Path,
    *,
    graph_id: str,
    graph_name: str | None = None,
    project_id: str | None = None,
    project_name: str | None = None,
    simulation_id: str | None = None,
    imported_at: str | None = None,
) -> dict[str, Any]:
    """Build a pure-data manifest for importing a completed bundle into MiroFish."""

    bundle_path = Path(bundle_dir).resolve()
    config = _read_json(bundle_path / "simulation_config.json")
    activity = summarize_bundle_activity(bundle_path)

    imported_at = imported_at or datetime.now().isoformat()
    resolved_project_id = project_id or str(config.get("project_id") or f"proj_{bundle_path.name}")
    resolved_simulation_id = simulation_id or str(config.get("simulation_id") or f"sim_{bundle_path.name}")
    resolved_graph_name = graph_name or f"Super_Agents {resolved_simulation_id}"
    resolved_project_name = project_name or resolved_graph_name
    agent_configs = list(config.get("agent_configs", []))
    entity_types = sorted({str(agent.get("entity_type") or "Participant") for agent in agent_configs})
    total_rounds = activity["total_rounds"]
    if total_rounds is None:
        total_rounds = max(
            activity["max_round"] + 1,
            int(config.get("time_config", {}).get("total_simulation_hours", 0)),
        )

    files = [{"filename": "simulation_config.json"}]
    for relative_path in ACTION_LOGS.values():
        if (bundle_path / relative_path).exists():
            files.append({"filename": relative_path.as_posix()})

    import_summary = (
        f"Imported Super_Agents bundle {resolved_simulation_id} into Zep graph {graph_id}. "
        f"Agents: {len(agent_configs)}. Platforms: {', '.join(activity['platforms']) or 'none'}. "
        f"Recorded actions: {sum(activity['action_counts'].values())}."
    )

    config_copy = json.loads(json.dumps(config))
    config_copy["project_id"] = resolved_project_id
    config_copy["simulation_id"] = resolved_simulation_id
    config_copy["graph_id"] = graph_id

    copy_files = []
    for relative_path in (Path("simulation_config.json"), *OPTIONAL_BUNDLE_FILES, *ACTION_LOGS.values()):
        source_path = bundle_path / relative_path
        if source_path.exists():
            copy_files.append({"source": str(source_path), "target": relative_path.as_posix()})

    return {
        "bundle_dir": str(bundle_path),
        "graph_id": graph_id,
        "graph_name": resolved_graph_name,
        "project": {
            "project_id": resolved_project_id,
            "name": resolved_project_name,
            "status": "graph_completed",
            "created_at": imported_at,
            "updated_at": imported_at,
            "files": files,
            "total_text_length": len(config.get("simulation_requirement", "")),
            "ontology": None,
            "analysis_summary": import_summary,
            "graph_id": graph_id,
            "graph_build_task_id": None,
            "simulation_requirement": config.get("simulation_requirement"),
            "chunk_size": 500,
            "chunk_overlap": 50,
            "error": None,
            "extracted_text": import_summary + "\n\n" + str(config.get("simulation_requirement", "")).strip(),
        },
        "simulation": {
            "simulation_id": resolved_simulation_id,
            "project_id": resolved_project_id,
            "graph_id": graph_id,
            "enable_twitter": activity["action_counts"].get("twitter", 0) > 0,
            "enable_reddit": activity["action_counts"].get("reddit", 0) > 0,
            "status": "completed",
            "entities_count": len(agent_configs),
            "profiles_count": len(agent_configs),
            "entity_types": entity_types,
            "config_generated": True,
            "config_reasoning": "Imported from a completed Super_Agents simulation bundle.",
            "current_round": activity["max_round"],
            "twitter_status": "completed" if activity["action_counts"].get("twitter", 0) > 0 else "not_started",
            "reddit_status": "completed" if activity["action_counts"].get("reddit", 0) > 0 else "not_started",
            "created_at": imported_at,
            "updated_at": imported_at,
            "error": None,
        },
        "run_state": {
            "simulation_id": resolved_simulation_id,
            "runner_status": "completed",
            "current_round": activity["max_round"],
            "total_rounds": total_rounds,
            "simulated_hours": min(activity["max_round"], int(config.get("time_config", {}).get("total_simulation_hours", 0))),
            "total_simulation_hours": int(config.get("time_config", {}).get("total_simulation_hours", 0)),
            "twitter_current_round": activity["max_round_per_platform"].get("twitter", 0),
            "reddit_current_round": activity["max_round_per_platform"].get("reddit", 0),
            "twitter_simulated_hours": activity["max_round_per_platform"].get("twitter", 0),
            "reddit_simulated_hours": activity["max_round_per_platform"].get("reddit", 0),
            "twitter_running": False,
            "reddit_running": False,
            "twitter_completed": activity["action_counts"].get("twitter", 0) > 0,
            "reddit_completed": activity["action_counts"].get("reddit", 0) > 0,
            "twitter_actions_count": activity["action_counts"].get("twitter", 0),
            "reddit_actions_count": activity["action_counts"].get("reddit", 0),
            "started_at": imported_at,
            "updated_at": imported_at,
            "completed_at": imported_at,
            "error": None,
            "process_pid": None,
            "recent_actions": activity["recent_actions"],
        },
        "config": config_copy,
        "copy_files": copy_files,
        "summary": {
            "agent_count": len(agent_configs),
            "action_counts": activity["action_counts"],
            "platforms": activity["platforms"],
            "max_round": activity["max_round"],
            "total_rounds": total_rounds,
        },
    }


def register_bundle_import(
    bundle_dir: str | Path,
    manifest: dict[str, Any],
    *,
    runtime_home: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Write imported bundle metadata into the local MiroFish backend storage."""

    home = resolve_runtime_home(runtime_home)
    symbols = _import_backend_symbols(home)
    bundle_path = Path(bundle_dir).resolve()

    Project = symbols["Project"]
    ProjectManager = symbols["ProjectManager"]
    ProjectStatus = symbols["ProjectStatus"]
    SimulationManager = symbols["SimulationManager"]
    SimulationState = symbols["SimulationState"]
    SimulationStatus = symbols["SimulationStatus"]
    SimulationRunner = symbols["SimulationRunner"]
    SimulationRunState = symbols["SimulationRunState"]
    RunnerStatus = symbols["RunnerStatus"]
    AgentAction = symbols["AgentAction"]

    project_id = manifest["project"]["project_id"]
    simulation_id = manifest["simulation"]["simulation_id"]

    project_dir = Path(ProjectManager._get_project_dir(project_id))
    simulation_dir = Path(SimulationManager.SIMULATION_DATA_DIR) / simulation_id

    if force:
        shutil.rmtree(project_dir, ignore_errors=True)
        shutil.rmtree(simulation_dir, ignore_errors=True)
    else:
        if project_dir.exists():
            raise FileExistsError(f"MiroFish project already exists: {project_id}")
        if simulation_dir.exists():
            raise FileExistsError(f"MiroFish simulation already exists: {simulation_id}")

    ProjectManager._ensure_projects_dir()
    Path(ProjectManager._get_project_files_dir(project_id)).mkdir(parents=True, exist_ok=True)

    project_payload = {key: value for key, value in manifest["project"].items() if key != "extracted_text"}
    project_payload["status"] = ProjectStatus(project_payload["status"])
    project = Project.from_dict(project_payload)
    ProjectManager.save_project(project)
    ProjectManager.save_extracted_text(project_id, manifest["project"]["extracted_text"])

    manager = SimulationManager()
    simulation_dir.mkdir(parents=True, exist_ok=True)
    simulation_payload = dict(manifest["simulation"])
    simulation_payload["status"] = SimulationStatus(simulation_payload["status"])
    state = SimulationState(**simulation_payload)
    manager._save_simulation_state(state)

    config_target = simulation_dir / "simulation_config.json"
    _write_json(config_target, manifest["config"])

    for item in manifest["copy_files"]:
        source = Path(item["source"])
        target = simulation_dir / item["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.name == "simulation_config.json":
            continue
        shutil.copy2(source, target)

    run_state_payload = dict(manifest["run_state"])
    recent_actions_payload = run_state_payload.pop("recent_actions", [])
    run_state_payload["runner_status"] = RunnerStatus(run_state_payload["runner_status"])
    run_state = SimulationRunState(**run_state_payload)
    for action in recent_actions_payload:
        run_state.recent_actions.append(
            AgentAction(
                round_num=int(action.get("round_num", action.get("round", 0))),
                timestamp=_normalize_timestamp(action.get("timestamp")),
                platform=str(action.get("platform") or ""),
                agent_id=int(action.get("agent_id", 0)),
                agent_name=str(action.get("agent_name") or ""),
                action_type=str(action.get("action_type") or ""),
                action_args=dict(action.get("action_args") or {}),
                result=action.get("result"),
                success=bool(action.get("success", True)),
            )
        )
    SimulationRunner._save_run_state(run_state)

    import_record = {
        "imported_at": manifest["project"]["created_at"],
        "graph_id": manifest["graph_id"],
        "graph_name": manifest["graph_name"],
        "project_id": project_id,
        "simulation_id": simulation_id,
        "bundle_dir": str(bundle_path),
        "summary": manifest["summary"],
    }
    _write_json(simulation_dir / "zep_import.json", import_record)
    _write_json(bundle_path / "zep_import.json", import_record)

    return {
        "project_id": project_id,
        "simulation_id": simulation_id,
        "simulation_dir": str(simulation_dir),
        "project_dir": str(project_dir),
        "import_record_path": str(simulation_dir / "zep_import.json"),
        "bundle_import_record_path": str(bundle_path / "zep_import.json"),
    }


def publish_bundle_to_zep(
    bundle_dir: str | Path,
    *,
    runtime_home: str | Path | None = None,
    graph_name: str | None = None,
    project_name: str | None = None,
    force: bool = False,
    poll_seconds: float = 2.0,
    poll_attempts: int = 10,
) -> dict[str, Any]:
    """Create a Zep graph, replay a completed bundle into it, and register it with local MiroFish state."""

    home = resolve_runtime_home(runtime_home)
    symbols = _import_backend_symbols(home)
    Config = symbols["Config"]
    GraphBuilderService = symbols["GraphBuilderService"]
    ZepGraphMemoryUpdater = symbols["ZepGraphMemoryUpdater"]

    config_errors = Config.validate()
    if config_errors:
        raise ValueError("MiroFish runtime is not configured: " + "; ".join(config_errors))

    bundle_path = Path(bundle_dir).resolve()
    config = _read_json(bundle_path / "simulation_config.json")
    activity = summarize_bundle_activity(bundle_path)

    builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
    resolved_graph_name = graph_name or f"Super_Agents {config.get('simulation_id', bundle_path.name)}"
    graph_id = builder.create_graph(name=resolved_graph_name)

    bootstrap_lines = [
        f"Simulation {config.get('simulation_id', bundle_path.name)} imported from Super_Agents.",
        str(config.get("simulation_requirement") or "").strip(),
        "Participants: " + ", ".join(
            str(agent.get("entity_name") or f"Agent {index}")
            for index, agent in enumerate(config.get("agent_configs", []))
        ),
        "Platforms: " + (", ".join(activity["platforms"]) or "none"),
    ]
    builder.client.graph.add(graph_id=graph_id, type="text", data="\n".join(line for line in bootstrap_lines if line))

    updater = ZepGraphMemoryUpdater(graph_id)
    updater.start()
    try:
        for platform, relative_path in ACTION_LOGS.items():
            for record in _iter_jsonl(bundle_path / relative_path):
                updater.add_activity_from_dict(record, platform)
    finally:
        updater.stop()

    graph_data: dict[str, Any] | None = None
    for attempt in range(max(poll_attempts, 1)):
        try:
            graph_data = builder.get_graph_data(graph_id)
        except Exception:
            graph_data = None
        if graph_data and (
            graph_data.get("node_count")
            or graph_data.get("edge_count")
            or graph_data.get("nodes")
            or graph_data.get("edges")
        ):
            break
        if attempt < poll_attempts - 1:
            time.sleep(max(poll_seconds, 0))

    manifest = build_bundle_import_manifest(
        bundle_path,
        graph_id=graph_id,
        graph_name=resolved_graph_name,
        project_name=project_name,
    )
    registration = register_bundle_import(bundle_path, manifest, runtime_home=home, force=force)

    result = {
        "bundle_dir": str(bundle_path),
        "runtime_home": str(home),
        "graph_id": graph_id,
        "graph_name": resolved_graph_name,
        "graph_data": graph_data or {},
        "project_id": registration["project_id"],
        "simulation_id": registration["simulation_id"],
        "simulation_dir": registration["simulation_dir"],
        "project_dir": registration["project_dir"],
        "import_record_path": registration["import_record_path"],
        "bundle_import_record_path": registration["bundle_import_record_path"],
        "process_url": f"http://localhost:3000/process/{registration['project_id']}",
        "simulation_url": f"http://localhost:3000/simulation/{registration['simulation_id']}",
        "summary": manifest["summary"],
    }
    _write_json(bundle_path / "zep_publish_result.json", result)
    result["result_path"] = str(bundle_path / "zep_publish_result.json")
    return result
