"""Tests for LLM config loading."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
from super_agents.llm.config import load_llm_config


def test_load_llm_config_defaults_when_file_missing():
    config = load_llm_config(Path("missing.yaml"))

    assert config.default_model == "claude-sonnet-4-20250514"
    assert config.max_tokens == 4096
    assert config.temperature == 0.0


def test_load_llm_config_reads_yaml_values(monkeypatch: pytest.MonkeyPatch):
    config_path = Path("synthetic_llm_config.yaml")
    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:
        if self == config_path:
            return True
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)

    mocked_file = mock.mock_open(
        read_data="\n".join(
            [
                "llm:",
                '  default_model: "gpt-4o-mini"',
                '  extraction_model: "gpt-4.1-mini"',
                "  max_tokens: 2048",
                "  temperature: 0.2",
            ]
        )
    )

    with mock.patch("builtins.open", mocked_file):
        config = load_llm_config(config_path)

        assert config.default_model == "gpt-4o-mini"
        assert config.extraction_model == "gpt-4.1-mini"
        assert config.max_tokens == 2048
        assert config.temperature == 0.2
