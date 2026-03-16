"""LLM model configuration loader.

Each agent's config.yaml can specify model preferences:

    llm:
      default_model: "claude-sonnet-4-20250514"
      extraction_model: "gpt-4o-mini"
      scoring_model: "claude-sonnet-4-20250514"
      fallback_model: "gemini-2.0-flash"
      max_tokens: 4096
      temperature: 0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LLMConfig:
    """Immutable LLM configuration for an agent."""

    default_model: str = "claude-sonnet-4-20250514"
    extraction_model: str = "gpt-4o-mini"
    scoring_model: str = "claude-sonnet-4-20250514"
    fallback_model: str = "gemini-2.0-flash"
    max_tokens: int = 4096
    temperature: float = 0.0


def load_llm_config(config_path: Path | str) -> LLMConfig:
    """Load LLM config from an agent's config.yaml.

    Args:
        config_path: Path to the agent's config.yaml file.

    Returns:
        LLMConfig with the agent's model preferences.
    """
    path = Path(config_path)
    if not path.exists():
        return LLMConfig()

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    llm_section = data.get("llm", {})
    return LLMConfig(
        default_model=llm_section.get("default_model", LLMConfig.default_model),
        extraction_model=llm_section.get("extraction_model", LLMConfig.extraction_model),
        scoring_model=llm_section.get("scoring_model", LLMConfig.scoring_model),
        fallback_model=llm_section.get("fallback_model", LLMConfig.fallback_model),
        max_tokens=llm_section.get("max_tokens", LLMConfig.max_tokens),
        temperature=llm_section.get("temperature", LLMConfig.temperature),
    )
