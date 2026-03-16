"""Universal CLI for Super_Agents - run any agent skill from any AI tool.

Usage:
    python -m super_agents run --agent biotech --skill fda_tracker --script fetch_drug_approvals --days 30
    python -m super_agents run --agent gaming --skill storefront_monitor --script fetch_storefront_metrics --appid 570
    python -m super_agents list --agent biotech
    python -m super_agents list
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _build_search_configs(
    agents: dict[str, Any],
) -> dict[str, list[tuple[str, str, list[str]]]]:
    """Build search configs for all discovered agents.

    Curated entries (with specific args for richer output) take priority for
    known agents.  Every other discovered agent gets auto-generated entries
    from its first two skills so it appears in ``python -m super_agents search``.
    """
    curated: dict[str, list[tuple[str, str, list[str]]]] = {
        "biotech": [
            ("fda_tracker", "fetch_drug_approvals", ["--days", "30", "--limit", "10"]),
            ("clinicaltrials_scraper", "fetch_trials", ["--status", "RECRUITING", "--limit", "5"]),
            ("sec_filings_parser", "search_edgar", ["--cik", "1682852", "--types", "10-K"]),
        ],
        "gaming": [
            ("storefront_monitor", "fetch_storefront_metrics", ["--appid", "570"]),
        ],
        "aerospace": [
            ("award_tracker", "fetch_awards", ["--days", "30", "--limit", "10"]),
        ],
    }

    configs: dict[str, list[tuple[str, str, list[str]]]] = {}
    for agent_name, agent_info in agents.items():
        if agent_name in curated:
            configs[agent_name] = curated[agent_name]
            continue
        # Auto-discover: pick the first script from the first two available skills.
        entries: list[tuple[str, str, list[str]]] = []
        for skill_name, skill_info in list(agent_info["skills"].items())[:2]:
            script_names = list(skill_info["scripts"].keys())
            if script_names:
                entries.append((skill_name, script_names[0], []))
        if entries:
            configs[agent_name] = entries
    return configs


def _load_common_skill_descriptions(project_root: Path = PROJECT_ROOT) -> dict[str, str]:
    """Load shared skill descriptions from src/super_agents/common/config.yaml.

    Returns a mapping of ``skill_name -> description`` for skills defined in
    the common registry.  Agents that omit these skills from their own
    config.yaml will inherit the shared description automatically.
    """
    config_path = project_root / "src" / "super_agents" / "common" / "config.yaml"
    if not config_path.exists():
        return {}

    descriptions: dict[str, str] = {}
    lines = config_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    in_common_skills = False
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        if stripped == "common_skills:":
            in_common_skills = True
            index += 1
            continue
        if in_common_skills:
            if _indent_width(lines[index]) == 0:
                break
            if _indent_width(lines[index]) == 2 and stripped.startswith("- "):
                entry, index = _parse_skill_entry(lines, index)
                name = entry.get("name", "").strip()
                description = entry.get("description", "").strip()
                if name and description:
                    descriptions[name] = description
                continue
        index += 1
    return descriptions


def _humanize_name(name: str) -> str:
    """Convert a filesystem slug into a readable label."""
    return name.replace("_", " ").replace("-", " ").strip().title()


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_scalar_value(lines: list[str], index: int, key_fragment: str, indent: int) -> tuple[str, int]:
    """Parse a simple YAML scalar or folded block value."""
    _, _, raw_value = key_fragment.partition(":")
    value = raw_value.strip()

    if value not in {">", "|"}:
        return _strip_quotes(value), index + 1

    folded_lines: list[str] = []
    index += 1
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        if _indent_width(line) <= indent:
            break
        folded_lines.append(stripped)
        index += 1
    return " ".join(folded_lines), index


def _parse_skill_entry(lines: list[str], index: int) -> tuple[dict[str, str], int]:
    """Parse one item from the top-level skills list in config.yaml."""
    entry: dict[str, str] = {}
    bullet_line = lines[index]
    bullet_indent = _indent_width(bullet_line)

    first_fragment = bullet_line.strip()[2:]
    if ":" in first_fragment:
        key, _, _ = first_fragment.partition(":")
        value, index = _parse_scalar_value(lines, index, first_fragment, bullet_indent)
        entry[key.strip()] = value
    else:
        index += 1

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue
        line_indent = _indent_width(line)
        if line_indent <= bullet_indent:
            break
        if line_indent == bullet_indent + 2 and ":" in stripped:
            key, _, _ = stripped.partition(":")
            value, index = _parse_scalar_value(lines, index, stripped, line_indent)
            entry[key.strip()] = value
            continue
        index += 1
    return entry, index


def _skill_name_from_config_path(path_value: str) -> str | None:
    if not path_value:
        return None
    path = PurePosixPath(path_value)
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "skills":
        return parts[1]
    return None


def _script_name_from_config_path(path_value: str) -> str | None:
    if not path_value:
        return None
    path = PurePosixPath(path_value)
    parts = path.parts
    if len(parts) >= 4 and parts[0] == "skills" and parts[2] == "scripts" and path.suffix == ".py":
        return path.stem
    return None


def _load_agent_metadata(agent_dir: Path) -> tuple[str, dict[str, str], dict[tuple[str, str], str]]:
    """Read a subset of each agent config without depending on PyYAML."""
    config_path = agent_dir / "config.yaml"
    if not config_path.exists():
        return "", {}, {}

    lines = config_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    agent_description = ""
    skill_descriptions: dict[str, str] = {}
    script_descriptions: dict[tuple[str, str], str] = {}

    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped or stripped.startswith("#"):
            index += 1
            continue

        if stripped == "agent:":
            index += 1
            while index < len(lines):
                line = lines[index]
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("#"):
                    index += 1
                    continue
                if _indent_width(line) == 0:
                    break
                if _indent_width(line) == 2 and line_stripped.startswith("description:"):
                    agent_description, index = _parse_scalar_value(lines, index, line_stripped, 2)
                    continue
                index += 1
            continue

        if stripped == "skills:":
            index += 1
            while index < len(lines):
                line = lines[index]
                line_stripped = line.strip()
                if not line_stripped or line_stripped.startswith("#"):
                    index += 1
                    continue
                if _indent_width(line) == 0:
                    break
                if _indent_width(line) == 2 and line_stripped.startswith("- "):
                    entry, index = _parse_skill_entry(lines, index)
                    description = entry.get("description", "").strip()
                    skill_name = _skill_name_from_config_path(entry.get("path", ""))
                    script_name = _script_name_from_config_path(entry.get("path", ""))
                    if not description:
                        continue
                    if skill_name and script_name:
                        script_descriptions[(skill_name, script_name)] = description
                    elif skill_name:
                        skill_descriptions[skill_name] = description
                    continue
                index += 1
            continue

        index += 1

    return agent_description, skill_descriptions, script_descriptions


def _load_module_ast(script_path: Path) -> ast.Module | None:
    try:
        source = script_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _read_script_description(script_path: Path) -> str:
    """Return the first non-empty docstring line, if available."""
    module = _load_module_ast(script_path)
    if module is None:
        return ""

    docstring = ast.get_docstring(module)
    if not docstring:
        return ""

    for line in docstring.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


class _ArgparseOptionVisitor(ast.NodeVisitor):
    """Collect argparse option flags from parser.add_argument calls."""

    def __init__(self) -> None:
        self.options: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("--"):
                    if arg.value not in self.options:
                        self.options.append(arg.value)
        self.generic_visit(node)


def _read_script_args(script_path: Path) -> list[str]:
    module = _load_module_ast(script_path)
    if module is None:
        return []

    visitor = _ArgparseOptionVisitor()
    visitor.visit(module)
    return visitor.options


def discover_agents(project_root: Path = PROJECT_ROOT) -> dict[str, dict[str, Any]]:
    """Discover runnable agents by scanning .agent_* directories."""
    agents: dict[str, dict[str, Any]] = {}
    common_skill_descriptions = _load_common_skill_descriptions(project_root)

    for agent_dir in sorted(project_root.glob(".agent_*")):
        skills_root = agent_dir / "skills"
        if not skills_root.is_dir():
            continue

        agent_name = agent_dir.name[len(".agent_") :]
        agent_description, skill_descriptions, script_descriptions = _load_agent_metadata(agent_dir)
        skills: dict[str, dict[str, Any]] = {}

        for skill_dir in sorted(skills_root.iterdir()):
            if not skill_dir.is_dir():
                continue

            scripts_dir = skill_dir / "scripts"
            if not scripts_dir.is_dir():
                continue

            scripts: dict[str, dict[str, Any]] = {}
            for script_path in sorted(scripts_dir.glob("*.py")):
                script_name = script_path.stem
                script_description = script_descriptions.get((skill_dir.name, script_name))
                if not script_description:
                    script_description = _read_script_description(script_path) or _humanize_name(script_name)

                scripts[script_name] = {
                    "file": script_path.name,
                    "path": script_path,
                    "args": _read_script_args(script_path),
                    "description": script_description,
                }

            if not scripts:
                continue

            skill_description = (
                skill_descriptions.get(skill_dir.name)
                or common_skill_descriptions.get(skill_dir.name)
            )
            if not skill_description and len(scripts) == 1:
                skill_description = next(iter(scripts.values()))["description"]
            if not skill_description:
                skill_description = _humanize_name(skill_dir.name)

            skills[skill_dir.name] = {
                "description": skill_description,
                "scripts": scripts,
            }

        if not skills:
            continue

        agents[agent_name] = {
            "dir": agent_dir.name,
            "description": agent_description or _humanize_name(agent_name),
            "skills": skills,
        }

    return agents


AGENTS = discover_agents()
SEARCH_CONFIGS = _build_search_configs(AGENTS)


def resolve_script_path(agent: str, skill: str, script_name: str) -> Path:
    """Resolve the full path to a skill script."""
    agent_info = AGENTS[agent]
    skill_info = agent_info["skills"][skill]
    script_info = skill_info["scripts"][script_name]
    return script_info["path"]


def cmd_list(args: argparse.Namespace) -> int:
    """List available agents, skills, and scripts."""
    if args.agent:
        agents_to_show = [args.agent]
    else:
        agents_to_show = list(AGENTS.keys())

    for agent_name in agents_to_show:
        if agent_name not in AGENTS:
            print(f"Unknown agent: {agent_name}", file=sys.stderr)
            print(f"Available agents: {', '.join(AGENTS.keys())}", file=sys.stderr)
            return 1
        agent = AGENTS[agent_name]
        display_name = agent_name.upper().replace("_", " ")
        print(f"\n{'='*60}")
        print(f"  {display_name} - {agent['description']}")
        print(f"{'='*60}")

        for skill_name, skill in sorted(agent["skills"].items()):
            print(f"\n  {skill_name}: {skill['description']}")
            for script_name, script in sorted(skill["scripts"].items()):
                known_args = " ".join(script.get("args", []))
                print(f"    - {script_name:<35} {script['description']}")
                if known_args:
                    print(f"      args: {known_args}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run a specific agent skill script."""
    agent_name = args.agent
    skill_name = args.skill
    script_name = args.script

    if agent_name not in AGENTS:
        print(f"Unknown agent: {agent_name}", file=sys.stderr)
        print(f"Available: {', '.join(AGENTS.keys())}", file=sys.stderr)
        return 1

    agent = AGENTS[agent_name]
    if skill_name not in agent["skills"]:
        print(f"Unknown skill: {skill_name} for agent {agent_name}", file=sys.stderr)
        print(f"Available: {', '.join(agent['skills'].keys())}", file=sys.stderr)
        return 1

    skill = agent["skills"][skill_name]
    if script_name not in skill["scripts"]:
        print(f"Unknown script: {script_name} in {agent_name}/{skill_name}", file=sys.stderr)
        print(f"Available: {', '.join(skill['scripts'].keys())}", file=sys.stderr)
        return 1

    script_path = resolve_script_path(agent_name, skill_name, script_name)
    if not script_path.exists():
        print(f"Script not found: {script_path}", file=sys.stderr)
        return 1

    extra = [a for a in args.extra if a != "--"]
    cmd = [sys.executable, str(script_path)] + extra
    print(f"Running: {' '.join(cmd)}")
    print(f"Agent: {agent_name} | Skill: {skill_name} | Script: {script_name}")
    print("-" * 60)

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    return result.returncode


def cmd_search(args: argparse.Namespace) -> int:
    """Run a predefined live search across one or all agents."""
    targets = [args.agent] if args.agent else list(AGENTS.keys())

    for agent_name in targets:
        if agent_name not in AGENTS:
            print(f"Skipping unknown agent: {agent_name}", file=sys.stderr)
            continue

        configs = SEARCH_CONFIGS.get(agent_name, [])
        if not configs:
            print(f"No default search configured for {agent_name}, skipping.")
            continue

        print(f"\n{'='*60}")
        print(f"  LIVE SEARCH: {agent_name.upper().replace('_', ' ')}")
        print(f"{'='*60}")

        for skill_name, script_name, extra_args in configs:
            try:
                script_path = resolve_script_path(agent_name, skill_name, script_name)
            except KeyError:
                print(f"  [!] Search config missing {agent_name}/{skill_name}/{script_name}")
                continue

            if not script_path.exists():
                print(f"  [!] Script missing: {script_path}")
                continue

            print(f"\n  > {skill_name}/{script_name} {' '.join(extra_args)}")
            print(f"  {'-'*56}")

            cmd = [sys.executable, str(script_path)] + extra_args
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT),
                capture_output=not args.verbose,
                text=True,
            )

            if result.returncode == 0:
                print("  [OK] Success (exit 0)")
                if not args.verbose and result.stdout:
                    lines = result.stdout.strip().split("\n")
                    for line in lines[:20]:
                        print(f"    {line}")
                    if len(lines) > 20:
                        print(f"    ... ({len(lines) - 20} more lines)")
            else:
                print(f"  [FAIL] Failed (exit {result.returncode})")
                if result.stderr:
                    for line in result.stderr.strip().split("\n")[:10]:
                        print(f"    {line}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    agent_choices = list(AGENTS.keys())

    parser = argparse.ArgumentParser(
        prog="super_agents",
        description="Universal CLI for Super_Agents - run any agent skill from any AI tool.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list command
    list_parser = subparsers.add_parser("list", help="List available agents and skills")
    list_parser.add_argument("--agent", "-a", choices=agent_choices, help="Filter by agent")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a specific skill script")
    run_parser.add_argument("--agent", "-a", required=True, choices=agent_choices)
    run_parser.add_argument("--skill", "-s", required=True, help="Skill name")
    run_parser.add_argument("--script", "-r", required=True, help="Script name (without .py)")
    run_parser.add_argument("extra", nargs=argparse.REMAINDER, help="Extra arguments for script")

    # search command
    search_parser = subparsers.add_parser("search", help="Run live search across agents")
    search_parser.add_argument("--agent", "-a", choices=agent_choices, help="Single agent")
    search_parser.add_argument("--verbose", "-v", action="store_true", help="Show full output")

    # crucix command
    crucix_parser = subparsers.add_parser("crucix", help="Crucix data hub integration")
    crucix_sub = crucix_parser.add_subparsers(dest="crucix_command", required=True)

    crucix_sub.add_parser("status", help="Show Crucix integration status")
    crucix_sub.add_parser("setup", help="Clone and install Crucix")

    sweep_parser = crucix_sub.add_parser("sweep", help="Run a single Crucix sweep and route signals")
    sweep_parser.add_argument("--store", action="store_true", help="Persist signals to SQLite")

    route_parser = crucix_sub.add_parser("route", help="Route latest briefing to agents (dry-run)")
    route_parser.add_argument("--briefing", type=str, help="Path to briefing JSON (default: latest)")

    signals_parser = crucix_sub.add_parser("signals", help="Query stored signals")
    signals_parser.add_argument("--topic", type=str, help="Filter by topic (supports *)")
    signals_parser.add_argument("--source", type=str, help="Filter by source")
    signals_parser.add_argument("--sector", type=str, help="Filter by sector")
    signals_parser.add_argument("--since", type=str, help="ISO timestamp")
    signals_parser.add_argument("--limit", type=int, default=20, help="Max results")

    crucix_sub.add_parser("sources", help="List all Crucix sources and sector mappings")

    # simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run a scenario simulation")
    sim_parser.add_argument("scenario", type=str, help="Path to scenario YAML file")
    sim_parser.add_argument("--output", "-o", type=str, help="Output directory (default: runs/simulations/)")
    sim_parser.add_argument("--signals", type=str, help="Path to briefing JSON to inject as signals")
    sim_parser.add_argument("--from-store", action="store_true", help="Inject signals from SQLite store")
    sim_parser.add_argument("--json-only", action="store_true", help="Only write JSON output (skip Markdown)")
    sim_parser.add_argument("--summary", action="store_true", help="Print summary to console only")

    return parser


def cmd_crucix(args: argparse.Namespace) -> int:
    """Handle crucix subcommands."""
    subcmd = args.crucix_command

    if subcmd == "status":
        return _crucix_status()
    elif subcmd == "setup":
        return _crucix_setup()
    elif subcmd == "sweep":
        return _crucix_sweep(store=args.store)
    elif subcmd == "route":
        return _crucix_route(briefing_path=getattr(args, "briefing", None))
    elif subcmd == "signals":
        return _crucix_signals(args)
    elif subcmd == "sources":
        return _crucix_sources()
    return 1


def _crucix_status() -> int:
    from super_agents.integrations.crucix.runner import get_status
    status = get_status()
    print("\nCrucix Integration Status")
    print("=" * 40)
    for key, value in status.items():
        print(f"  {key}: {value}")
    return 0


def _crucix_setup() -> int:
    from super_agents.integrations.crucix.runner import clone_crucix, install_crucix, setup_crucix_env
    try:
        clone_crucix()
        install_crucix()
        setup_crucix_env()
        print("[OK] Crucix installed and configured")
        return 0
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1


def _crucix_sweep(store: bool = False) -> int:
    from super_agents.integrations.crucix.runner import run_sweep
    from super_agents.integrations.crucix.bridge import parse_briefing
    from super_agents.integrations.crucix.router import SignalRouter
    from super_agents.common.registry import AgentRegistry

    print("Running Crucix sweep...")
    path = run_sweep()
    if not path:
        print("[FAIL] Sweep produced no output", file=sys.stderr)
        return 1

    signals = parse_briefing(path)
    print(f"Parsed {len(signals)} signals from sweep")

    registry = AgentRegistry()
    router = SignalRouter(registry)
    routed = router.route(signals)

    print(f"\nRouted to {len(routed)} agents:")
    for agent, agent_signals in sorted(routed.items()):
        topics = {s.topic for s in agent_signals}
        print(f"  {agent}: {len(agent_signals)} signals ({len(topics)} topics)")

    if store:
        from super_agents.integrations.crucix.store import SignalStore
        with SignalStore() as signal_store:
            saved = signal_store.save(signals)
            print(f"\nStored {saved} signals to {signal_store._db_path}")

    return 0


def _crucix_route(briefing_path: str | None = None) -> int:
    from super_agents.integrations.crucix.bridge import parse_briefing
    from super_agents.integrations.crucix.runner import CRUCIX_RUNS_DIR
    from super_agents.integrations.crucix.router import SignalRouter
    from super_agents.common.registry import AgentRegistry

    path = Path(briefing_path) if briefing_path else CRUCIX_RUNS_DIR / "latest.json"
    if not path.exists():
        print(f"[FAIL] No briefing at {path}", file=sys.stderr)
        print("Run 'python -m super_agents crucix sweep' first.", file=sys.stderr)
        return 1

    signals = parse_briefing(path)
    print(f"Parsed {len(signals)} signals from {path.name}")

    registry = AgentRegistry()
    router = SignalRouter(registry)
    summary = router.summary(signals)

    print(f"\nRouting Summary ({summary['total_signals']} signals → {summary['agents_targeted']} agents):")
    print("-" * 60)
    for agent, info in sorted(summary["per_agent"].items()):
        print(f"\n  {agent.upper()} ({info['signal_count']} signals)")
        for topic in sorted(info["topics"])[:10]:
            print(f"    - {topic}")
        if len(info["topics"]) > 10:
            print(f"    ... and {len(info['topics']) - 10} more topics")

    return 0


def _crucix_signals(args: argparse.Namespace) -> int:
    from super_agents.integrations.crucix.store import SignalStore

    with SignalStore() as store:
        if not args.topic and not args.source and not args.sector and not args.since:
            # Show stats
            stats = store.stats()
            print("\nSignal Store Stats")
            print("=" * 40)
            print(f"  Total signals:  {stats['total_signals']}")
            print(f"  Processed:      {stats['processed']}")
            print(f"  Unprocessed:    {stats['unprocessed']}")
            print(f"  Sources:        {', '.join(stats['unique_sources'])}")
            print(f"\n  Top topics:")
            for topic, count in list(stats["top_topics"].items())[:10]:
                print(f"    {topic}: {count}")
            return 0

        signals = store.query(
            topic=args.topic,
            source=args.source,
            sector=args.sector,
            since=args.since,
            limit=args.limit,
        )
        print(f"\n{len(signals)} signals found:")
        for s in signals:
            print(f"  [{s.confidence}] {s.timestamp.strftime('%Y-%m-%d %H:%M')} | {s.source} | {s.topic}")
            if s.sectors:
                print(f"           sectors: {', '.join(s.sectors)}")
    return 0


def _crucix_sources() -> int:
    from super_agents.integrations.crucix.source_map import CRUCIX_SOURCE_MAP, sources_for_sector
    from super_agents.common.registry import AgentRegistry

    registry = AgentRegistry()

    print("\nCrucix Sources -> Agent Sectors")
    print("=" * 70)
    for source, info in sorted(CRUCIX_SOURCE_MAP.items()):
        sectors = info["sectors"] if info["sectors"] else ("ALL",)
        print(f"\n  {source:<20} [{info['confidence']}]")
        print(f"    {info['description']}")
        print(f"    Sectors: {', '.join(sectors)}")

    print(f"\n{'=' * 70}")
    print("\nAgent <- Sources")
    print("-" * 70)
    for agent_name in registry.agent_names:
        matched = sources_for_sector(agent_name)
        print(f"  {agent_name:<25} <- {len(matched)} sources: {', '.join(matched[:8])}")
        if len(matched) > 8:
            print(f"  {'':25}   ... and {len(matched) - 8} more")

    return 0


def cmd_simulate(args: argparse.Namespace) -> int:
    """Run a scenario simulation."""
    import json as json_mod
    from datetime import datetime as dt

    from super_agents.simulation.scenario import load_scenario
    from super_agents.simulation.engine import SimulationEngine
    from super_agents.simulation.persona import threshold_rule, signal_watcher_rule
    from super_agents.simulation.timeline import write_json, write_markdown, build_summary

    scenario_path = Path(args.scenario)
    if not scenario_path.is_absolute():
        scenario_path = PROJECT_ROOT / scenario_path

    if not scenario_path.exists():
        print(f"[FAIL] Scenario not found: {scenario_path}", file=sys.stderr)
        return 1

    print(f"Loading scenario: {scenario_path.name}")
    scenario = load_scenario(scenario_path)

    print(f"  Name:     {scenario.name}")
    print(f"  Ticks:    {scenario.tick_count} ({scenario.tick} each)")
    print(f"  Personas: {', '.join(scenario.persona_names)}")
    print(f"  Variables: {len(scenario.variables)}")
    print(f"  Hypotheses: {len(scenario.hypotheses)}")
    print()

    engine = SimulationEngine(scenario)

    # Register domain-specific rules based on scenario variables
    from super_agents.simulation.builtin_rules import auto_register
    rule_count = auto_register(engine, scenario)
    print(f"Auto-registered {rule_count} domain rules")

    # Inject signals from briefing file or store
    signal_count = 0
    if args.signals:
        from super_agents.integrations.crucix.bridge import parse_briefing
        sig_path = Path(args.signals)
        if not sig_path.exists():
            print(f"[WARN] Briefing not found: {sig_path}", file=sys.stderr)
        else:
            signals = parse_briefing(sig_path)
            engine.inject_signals(signals)
            signal_count = len(signals)
            print(f"Injected {signal_count} signals from {sig_path.name}")

    if args.from_store:
        from super_agents.integrations.crucix.store import SignalStore
        with SignalStore() as store:
            signals = store.signals_for_replay()
            engine.inject_signals(signals)
            signal_count += len(signals)
            print(f"Injected {len(signals)} signals from store")

    # Run simulation
    print(f"\nRunning simulation ({scenario.tick_count} ticks)...")
    print("-" * 60)
    result = engine.run()

    # Output
    if args.summary:
        summary = build_summary(result)
        print(f"\nSimulation Complete: {summary['scenario']}")
        print(f"  Ticks:       {summary['ticks']}")
        print(f"  Signals:     {summary['signals_injected']}")
        print(f"  Alerts:      {summary['total_alerts']}")
        print(f"  Predictions: {summary['total_predictions']}")
        print(f"  Duration:    {summary['duration_seconds']:.2f}s")

        if summary["variable_changes"]:
            print(f"\n  Variable Changes:")
            for var, change in summary["variable_changes"].items():
                print(f"    {var}: {change['from']} -> {change['to']}")

        if summary["persona_stats"]:
            print(f"\n  Persona Stats:")
            for name, stats in summary["persona_stats"].items():
                print(f"    {name}: avg_conf={stats['avg_confidence']:.1%}, "
                      f"alerts={stats['total_alerts']}, preds={stats['total_predictions']}")

        if summary["top_alerts"]:
            print(f"\n  Top Alerts:")
            for alert in summary["top_alerts"]:
                print(f"    Tick {alert['tick']} [{alert['persona']}]: {alert['alert']}")

        if summary["top_predictions"]:
            print(f"\n  Top Predictions:")
            for pred in summary["top_predictions"]:
                text = pred.get("text", "")
                print(f"    Tick {pred['tick']} [{pred['persona']}]: {text}")
        return 0

    # Write files
    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "runs" / "simulations"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{scenario.name}_{timestamp}"

    json_path = write_json(result, output_dir / f"{base_name}.json")
    print(f"\nJSON output: {json_path}")

    if not args.json_only:
        md_path = write_markdown(result, output_dir / f"{base_name}.md")
        print(f"Markdown output: {md_path}")

    # Always print summary to console
    summary = build_summary(result)
    print(f"\n{'=' * 60}")
    print(f"  Simulation Complete: {summary['scenario']}")
    print(f"  {summary['ticks']} ticks | {summary['total_alerts']} alerts | "
          f"{summary['total_predictions']} predictions | {summary['duration_seconds']:.2f}s")
    print(f"{'=' * 60}")

    return 0


def _auto_register_rules(engine: "SimulationEngine", scenario: "Scenario") -> None:
    """Register sensible default rules based on scenario variables.

    This gives the rule-based engine something to work with even without
    custom per-scenario rule files. Looks for common variable patterns
    and creates threshold/watcher rules.
    """
    from super_agents.simulation.persona import threshold_rule, signal_watcher_rule

    # Map variable name patterns to rules
    rule_patterns: dict[str, list[tuple[str, float, str, str, str]]] = {
        # (variable, threshold, direction, prediction, alert)
        "oil_price": [
            ("oil_price_wti", 120.0, "above",
             "WTI above $120 - demand destruction likely",
             "CRITICAL: Oil price crisis territory"),
            ("oil_price_brent", 125.0, "above",
             "Brent above $125 - emergency reserves likely",
             "CRITICAL: Brent crisis level"),
        ],
        "vix": [
            ("vix", 35.0, "above",
             "VIX above 35 - elevated fear, portfolio hedging accelerates",
             "HIGH: VIX approaching crisis threshold"),
            ("vix", 40.0, "above",
             "VIX above 40 - crisis territory, margin calls likely",
             "CRITICAL: VIX in crisis zone"),
        ],
        "cape_route": [
            ("cape_route_utilization_pct", 75.0, "above",
             "Cape route utilization above 75% - congestion building",
             "HIGH: Cape route approaching capacity"),
        ],
        "teu_spot_rate": [
            ("teu_spot_rate_eu_asia", 5000, "above",
             "TEU rates above $5000 - shipping cost crisis",
             "HIGH: Container rates at crisis levels"),
        ],
    }

    variables = scenario.variables

    for persona_name in engine.persona_names:
        for pattern_key, rules in rule_patterns.items():
            for var_name, threshold, direction, pred_text, alert_text in rules:
                if var_name in variables:
                    try:
                        rule = threshold_rule(
                            variable=var_name,
                            threshold=threshold,
                            direction=direction,
                            prediction_text=pred_text,
                            alert_text=alert_text,
                        )
                        engine.register_rules(persona_name, [(f"{var_name}_{direction}_{threshold}", rule)])
                    except ValueError:
                        pass  # persona not found - skip

        # Add signal watchers for common topics
        for topic, pred in [
            ("maritime", "Maritime disruption detected - supply chain impact likely"),
            ("conflict", "Armed conflict signal - escalation risk elevated"),
            ("energy", "Energy market signal - price volatility expected"),
            ("sanctions", "Sanctions activity - compliance and trade flow impact"),
        ]:
            try:
                rule = signal_watcher_rule(topic, pred)
                engine.register_rules(persona_name, [(f"watch_{topic}", rule)])
            except ValueError:
                pass


def main() -> int:
    """Entry point."""
    parser = build_parser()
    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "run": cmd_run,
        "search": cmd_search,
        "crucix": cmd_crucix,
        "simulate": cmd_simulate,
    }
    return commands[args.command](args)
