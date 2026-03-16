"""Runtime helpers for launching MiroFish simulations safely from Super_Agents."""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[4]
MIROFISH_HOME_ENV = "SUPER_AGENTS_MIROFISH_HOME"
LLM_API_KEY_ENV = "LLM_API_KEY"
LLM_BASE_URL_ENV = "LLM_BASE_URL"
LLM_MODEL_NAME_ENV = "LLM_MODEL_NAME"
LLM_BOOST_API_KEY_ENV = "LLM_BOOST_API_KEY"
LLM_BOOST_BASE_URL_ENV = "LLM_BOOST_BASE_URL"
LLM_BOOST_MODEL_NAME_ENV = "LLM_BOOST_MODEL_NAME"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
PRIMARY_ENV_FILE_CANDIDATES = (Path(".env"), Path("backend/.env"))
EXAMPLE_ENV_FILE_CANDIDATES = (Path(".env.example"), Path("backend/.env.example"))
PLACEHOLDER_VALUES = {
    "your_api_key_here",
    "your-key",
    "your_key_here",
    "your_base_url_here",
    "your_model_name_here",
    "replace_me",
    "changeme",
}
RUNTIME_CANDIDATES = (
    PROJECT_ROOT / "vendor" / "MiroFish",
    PROJECT_ROOT / "vendor" / "mirofish",
    PROJECT_ROOT / "_reviews" / "MiroFish",
)
RUNNER_SCRIPTS = {
    "parallel": Path("backend/scripts/run_parallel_simulation.py"),
    "twitter": Path("backend/scripts/run_twitter_simulation.py"),
    "reddit": Path("backend/scripts/run_reddit_simulation.py"),
}
REQUIRED_MODULES = {
    "openai": "openai",
    "dotenv": "python-dotenv",
    "camel": "camel-ai",
    "oasis": "camel-oasis",
}


def _parse_env_file(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    if not path.exists():
        return entries

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ) and len(value) >= 2:
            value = value[1:-1]
        entries[key] = value
    return entries


def _is_placeholder_value(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    if not normalized:
        return False
    return (
        normalized in PLACEHOLDER_VALUES
        or normalized.startswith("your_")
        or normalized.startswith("<your")
    )


def _is_valid_url(value: str | None) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _resolve_runtime_env_files(runtime_home: Path) -> tuple[Path | None, Path | None]:
    active_env_file = next(
        (runtime_home / relative for relative in PRIMARY_ENV_FILE_CANDIDATES if (runtime_home / relative).exists()),
        None,
    )
    example_env_file = next(
        (runtime_home / relative for relative in EXAMPLE_ENV_FILE_CANDIDATES if (runtime_home / relative).exists()),
        None,
    )
    return active_env_file, example_env_file


def _runtime_config_summary(
    runtime_home: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    runtime_env = env if env is not None else os.environ
    active_env_file, example_env_file = _resolve_runtime_env_files(runtime_home)
    file_values = _parse_env_file(active_env_file) if active_env_file else {}

    def effective_value(key: str) -> tuple[str | None, str | None]:
        if runtime_env.get(key):
            return runtime_env.get(key), "environment"
        if key in file_values and file_values.get(key):
            return file_values.get(key), str(active_env_file)
        return None, None

    primary_api_key, primary_api_key_source = effective_value(LLM_API_KEY_ENV)
    openai_api_key, openai_api_key_source = effective_value(OPENAI_API_KEY_ENV)
    effective_api_key = primary_api_key or openai_api_key
    effective_api_key_source = primary_api_key_source or openai_api_key_source
    effective_base_url, effective_base_url_source = effective_value(LLM_BASE_URL_ENV)
    effective_model, effective_model_source = effective_value(LLM_MODEL_NAME_ENV)
    boost_api_key, boost_api_key_source = effective_value(LLM_BOOST_API_KEY_ENV)
    boost_base_url, boost_base_url_source = effective_value(LLM_BOOST_BASE_URL_ENV)
    boost_model, boost_model_source = effective_value(LLM_BOOST_MODEL_NAME_ENV)

    errors: list[str] = []
    warnings: list[str] = []

    if example_env_file and not active_env_file and not primary_api_key and not openai_api_key:
        warnings.append(
            f"Found {example_env_file}, but MiroFish only loads .env or backend/.env at runtime."
        )

    if not effective_api_key:
        errors.append(
            f"Missing {LLM_API_KEY_ENV}. Set it in the environment, {runtime_home / '.env'}, or backend/.env."
        )
    elif _is_placeholder_value(effective_api_key):
        errors.append(f"{LLM_API_KEY_ENV} is still a placeholder in {effective_api_key_source}.")

    if effective_base_url and _is_placeholder_value(effective_base_url):
        errors.append(f"{LLM_BASE_URL_ENV} is still a placeholder in {effective_base_url_source}.")
    elif effective_base_url and not _is_valid_url(effective_base_url):
        errors.append(f"{LLM_BASE_URL_ENV} is not a valid http(s) URL in {effective_base_url_source}.")

    if effective_model and _is_placeholder_value(effective_model):
        errors.append(f"{LLM_MODEL_NAME_ENV} is still a placeholder in {effective_model_source}.")

    boost_enabled = bool(boost_api_key)
    if boost_enabled:
        if _is_placeholder_value(boost_api_key):
            errors.append(f"{LLM_BOOST_API_KEY_ENV} is still a placeholder in {boost_api_key_source}.")
        if boost_base_url and _is_placeholder_value(boost_base_url):
            errors.append(
                f"{LLM_BOOST_BASE_URL_ENV} is still a placeholder in {boost_base_url_source}."
            )
        elif boost_base_url and not _is_valid_url(boost_base_url):
            errors.append(
                f"{LLM_BOOST_BASE_URL_ENV} is not a valid http(s) URL in {boost_base_url_source}."
            )
        if boost_model and _is_placeholder_value(boost_model):
            errors.append(
                f"{LLM_BOOST_MODEL_NAME_ENV} is still a placeholder in {boost_model_source}."
            )
    elif boost_base_url or boost_model:
        warnings.append(
            "Boost model settings are present without LLM_BOOST_API_KEY; Reddit will fall back to the primary model."
        )

    if not active_env_file and not effective_api_key:
        warnings.append("Create a runtime .env file by copying .env.example to .env before repeat runs.")

    return {
        "config_ready": not errors,
        "config_errors": errors,
        "config_warnings": warnings,
        "active_env_file": str(active_env_file) if active_env_file else None,
        "example_env_file": str(example_env_file) if example_env_file else None,
        "api_key_source": effective_api_key_source,
        "effective_base_url": effective_base_url or None,
        "effective_model": effective_model or None,
        "boost_enabled": boost_enabled,
    }


def _build_runtime_env(
    *,
    base_env: Mapping[str, str] | None = None,
    env_overrides: Mapping[str, str] | None = None,
    openai_defaults: bool = False,
) -> dict[str, str]:
    runtime_env = dict(base_env or os.environ)

    if openai_defaults:
        runtime_env.setdefault(LLM_BASE_URL_ENV, DEFAULT_OPENAI_BASE_URL)
        runtime_env.setdefault(LLM_MODEL_NAME_ENV, DEFAULT_OPENAI_MODEL)
        if runtime_env.get(LLM_API_KEY_ENV):
            runtime_env.setdefault(LLM_BOOST_API_KEY_ENV, runtime_env[LLM_API_KEY_ENV])
        if runtime_env.get(LLM_BASE_URL_ENV):
            runtime_env.setdefault(LLM_BOOST_BASE_URL_ENV, runtime_env[LLM_BASE_URL_ENV])
        if runtime_env.get(LLM_MODEL_NAME_ENV):
            runtime_env.setdefault(LLM_BOOST_MODEL_NAME_ENV, runtime_env[LLM_MODEL_NAME_ENV])

    if env_overrides:
        for key, value in env_overrides.items():
            runtime_env[key] = value

    return runtime_env


def _normalize_runtime_home(path: Path) -> Path:
    if (path / "backend" / "scripts").is_dir():
        return path
    if path.name == "backend" and (path / "scripts").is_dir():
        return path.parent
    raise FileNotFoundError(
        f"{path} does not look like a MiroFish checkout. Expected a repo root with backend/scripts."
    )


def resolve_runtime_home(runtime_home: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the local MiroFish checkout used as the runtime."""

    candidates: list[Path] = []
    if runtime_home:
        candidates.append(Path(runtime_home))

    env_value = os.environ.get(MIROFISH_HOME_ENV)
    if env_value:
        candidates.append(Path(env_value))

    candidates.extend(RUNTIME_CANDIDATES)

    for candidate in candidates:
        if candidate and candidate.exists():
            return _normalize_runtime_home(candidate.resolve())

    checked = ", ".join(str(candidate) for candidate in candidates if candidate)
    raise FileNotFoundError(
        "Could not locate a MiroFish runtime checkout. "
        f"Set {MIROFISH_HOME_ENV} or pass --runtime-path. Checked: {checked}"
    )


def get_runner_script(runtime_home: Path, platform: str) -> Path:
    try:
        relative = RUNNER_SCRIPTS[platform]
    except KeyError as exc:
        raise ValueError(f"Unsupported platform: {platform}") from exc
    script = runtime_home / relative
    if not script.exists():
        raise FileNotFoundError(f"Missing runner script: {script}")
    return script


def check_runtime(
    runtime_home: str | os.PathLike[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return a validation summary for a local MiroFish runtime checkout."""

    home = resolve_runtime_home(runtime_home)
    files = {platform: str(get_runner_script(home, platform)) for platform in RUNNER_SCRIPTS}
    modules = {
        module_name: {
            "importable": importlib.util.find_spec(module_name) is not None,
            "package": package_name,
        }
        for module_name, package_name in REQUIRED_MODULES.items()
    }
    missing_modules = [info["package"] for info in modules.values() if not info["importable"]]
    config_summary = _runtime_config_summary(home, env=env)
    dependencies_ready = not missing_modules
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    compatibility_warnings: list[str] = []
    if sys.version_info >= (3, 12):
        compatibility_warnings.append(
            f"Python {python_version} detected. The tested MiroFish runtime stack "
            "(camel-ai 0.2.78 / camel-oasis 0.2.5) currently needs Python 3.11."
        )
    config_warnings = compatibility_warnings + config_summary["config_warnings"]
    return {
        "runtime_home": str(home),
        "python_executable": sys.executable,
        "python_version": python_version,
        "runner_scripts": files,
        "dependencies": modules,
        "ready": dependencies_ready,
        "config_ready": config_summary["config_ready"],
        "runnable": dependencies_ready and config_summary["config_ready"],
        "missing_packages": missing_modules,
        "config_errors": config_summary["config_errors"],
        "config_warnings": config_warnings,
        "active_env_file": config_summary["active_env_file"],
        "example_env_file": config_summary["example_env_file"],
        "api_key_source": config_summary["api_key_source"],
        "effective_base_url": config_summary["effective_base_url"],
        "effective_model": config_summary["effective_model"],
        "boost_enabled": config_summary["boost_enabled"],
    }


def build_run_command(
    bundle_dir: Path | str,
    *,
    runtime_home: str | os.PathLike[str] | None = None,
    platform: str = "parallel",
    max_rounds: int | None = None,
    no_wait: bool = False,
) -> list[str]:
    """Build the subprocess command used to launch the MiroFish runtime."""

    home = resolve_runtime_home(runtime_home)
    script = get_runner_script(home, platform)
    bundle_path = Path(bundle_dir).resolve()
    config_path = bundle_path / "simulation_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing simulation_config.json in {bundle_path}")

    command = [sys.executable, str(script), "--config", str(config_path)]
    if max_rounds is not None:
        command.extend(["--max-rounds", str(max_rounds)])
    if no_wait:
        command.append("--no-wait")
    return command


def launch_simulation(
    bundle_dir: Path | str,
    *,
    runtime_home: str | os.PathLike[str] | None = None,
    platform: str = "parallel",
    max_rounds: int | None = None,
    no_wait: bool = False,
    background: bool = False,
    openai_defaults: bool = False,
    env_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Launch a MiroFish simulation for a prepared bundle."""

    home = resolve_runtime_home(runtime_home)
    runtime_env = _build_runtime_env(
        env_overrides=env_overrides,
        openai_defaults=openai_defaults,
    )
    command = build_run_command(
        bundle_dir,
        runtime_home=home,
        platform=platform,
        max_rounds=max_rounds,
        no_wait=no_wait,
    )
    bundle_path = Path(bundle_dir).resolve()
    runtime_info = check_runtime(home, env=runtime_env)
    if not runtime_info["ready"]:
        missing = ", ".join(runtime_info["missing_packages"])
        raise RuntimeError(f"MiroFish runtime dependencies are missing from this Python env: {missing}")
    if not runtime_info["config_ready"]:
        errors = " ".join(runtime_info["config_errors"])
        raise RuntimeError(f"MiroFish runtime configuration is incomplete: {errors}")

    if background:
        log_path = bundle_path / "mirofish_runtime.log"
        log_handle = log_path.open("a", encoding="utf-8")
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(
            command,
            cwd=runtime_info["runtime_home"],
            env=runtime_env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        log_handle.close()
        return {
            "mode": "background",
            "pid": process.pid,
            "command": command,
            "log_path": str(log_path),
            "runtime_home": runtime_info["runtime_home"],
        }

    completed = subprocess.run(
        command,
        cwd=runtime_info["runtime_home"],
        env=runtime_env,
        check=False,
    )
    return {
        "mode": "foreground",
        "returncode": completed.returncode,
        "command": command,
        "runtime_home": runtime_info["runtime_home"],
    }
