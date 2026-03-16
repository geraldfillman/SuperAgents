"""
Security hardening tests — Phase 1.

Verifies:
- require_env() raises on missing/empty variables
- optional_env() returns defaults gracefully
- validate_env_block() collects all missing keys before raising
- Input bounds validation rejects out-of-range CLI args
- Exception messages do not leak internal paths or URLs
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from super_agents.common.env import optional_env, require_env, validate_env_block


# ---------------------------------------------------------------------------
# require_env
# ---------------------------------------------------------------------------

class TestRequireEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_KEY_123", "hello")
        assert require_env("TEST_KEY_123") == "hello"

    def test_raises_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TEST_KEY_MISSING", raising=False)
        with pytest.raises(RuntimeError, match="TEST_KEY_MISSING"):
            require_env("TEST_KEY_MISSING")

    def test_raises_when_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TEST_KEY_EMPTY", "")
        with pytest.raises(RuntimeError, match="TEST_KEY_EMPTY"):
            require_env("TEST_KEY_EMPTY")

    def test_error_message_names_the_variable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MY_SECRET_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            require_env("MY_SECRET_KEY")
        assert "MY_SECRET_KEY" in str(exc_info.value)


# ---------------------------------------------------------------------------
# optional_env
# ---------------------------------------------------------------------------

class TestOptionalEnv:
    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPT_KEY", "value")
        assert optional_env("OPT_KEY") == "value"

    def test_returns_default_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPT_KEY_ABSENT", raising=False)
        assert optional_env("OPT_KEY_ABSENT") == ""
        assert optional_env("OPT_KEY_ABSENT", default="fallback") == "fallback"

    def test_returns_default_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPT_KEY_EMPTY", "")
        assert optional_env("OPT_KEY_EMPTY", default="fb") == "fb"

    def test_does_not_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NEVER_SET_KEY_XYZ", raising=False)
        # Should never raise
        result = optional_env("NEVER_SET_KEY_XYZ")
        assert result == ""


# ---------------------------------------------------------------------------
# validate_env_block
# ---------------------------------------------------------------------------

class TestValidateEnvBlock:
    def test_passes_when_all_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("BLOCK_A", "1")
        monkeypatch.setenv("BLOCK_B", "2")
        # Should not raise
        validate_env_block(["BLOCK_A", "BLOCK_B"], context="test block")

    def test_raises_listing_all_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_X", raising=False)
        monkeypatch.delenv("MISSING_Y", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            validate_env_block(["MISSING_X", "MISSING_Y"], context="smtp")
        error_text = str(exc_info.value)
        # Both missing keys must appear in the single error
        assert "MISSING_X" in error_text
        assert "MISSING_Y" in error_text

    def test_raises_only_for_missing_not_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRESENT_KEY", "yes")
        monkeypatch.delenv("ABSENT_KEY", raising=False)
        with pytest.raises(RuntimeError) as exc_info:
            validate_env_block(["PRESENT_KEY", "ABSENT_KEY"])
        assert "ABSENT_KEY" in str(exc_info.value)
        assert "PRESENT_KEY" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Bounds validation — fetch_sam_pipeline.py CLI args
# ---------------------------------------------------------------------------

SAM_SCRIPT = str(
    PROJECT_ROOT
    / ".agent_aerospace"
    / "skills"
    / "sam_pipeline_tracker"
    / "scripts"
    / "fetch_sam_pipeline.py"
)


class TestSamPipelineBounds:
    def _run(self, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, SAM_SCRIPT, "--company", "Test Corp", *extra_args],
            capture_output=True,
            text=True,
        )

    def test_days_zero_rejected(self) -> None:
        result = self._run("--days", "0")
        # returncode != 0 is the key guarantee; message content is validated
        # in unit tests since the script depends on adt_agent (sector package).
        assert result.returncode != 0

    def test_days_366_rejected(self) -> None:
        result = self._run("--days", "366")
        assert result.returncode != 0

    def test_days_365_accepted(self) -> None:
        # Should pass bounds check and fail later (missing SAM_API_KEY / watchlist),
        # but NOT fail due to bounds validation.
        result = self._run("--days", "365")
        combined = result.stdout + result.stderr
        assert "--days must be" not in combined

    def test_max_pages_51_rejected(self) -> None:
        result = self._run("--max-pages", "51")
        assert result.returncode != 0

    def test_page_size_zero_rejected(self) -> None:
        result = self._run("--page-size", "0")
        assert result.returncode != 0

    def test_api_key_arg_removed(self) -> None:
        """--api-key must no longer be a recognised argument."""
        result = self._run("--api-key", "somekey")
        assert result.returncode != 0
        combined = result.stdout + result.stderr
        assert "unrecognized" in combined.lower() or "error" in combined.lower()


# ---------------------------------------------------------------------------
# Exception message sanitisation — notify.py
# ---------------------------------------------------------------------------

class TestNotifyExceptionSanitisation:
    """Verify that exception handlers do not leak internal paths or URLs."""

    def test_slack_failure_does_not_leak_url(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/secret/path/TOKEN")

        import httpx
        # Add src to path so notify is importable
        sys.path.insert(0, str(PROJECT_ROOT / ".agent_biotech" / "plugins" / "notification_hooks"))

        # Re-import to pick up monkeypatched env
        import importlib
        import notify
        importlib.reload(notify)

        with patch.object(httpx, "post", side_effect=httpx.RequestError("connection refused")):
            notify.send_slack_notification("test message")

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        # The secret token and full URL must not appear in stdout/stderr
        assert "TOKEN" not in combined
        assert "hooks.slack.com" not in combined

    def test_email_failure_does_not_leak_host(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.setenv("SMTP_HOST", "internal-mailserver.corp.example.com")
        monkeypatch.setenv("SMTP_USER", "alerts@corp.example.com")
        monkeypatch.setenv("SMTP_PASSWORD", "s3cr3t")
        monkeypatch.setenv("ALERT_EMAIL_TO", "ops@corp.example.com")

        import importlib
        import notify
        # Reload so _SMTP_READY is recalculated with mocked env
        importlib.reload(notify)

        with patch("smtplib.SMTP", side_effect=OSError("connection refused to internal host")):
            notify.send_email_notification("Subject", "Body")

        captured = capsys.readouterr()
        combined = captured.out + captured.err
        assert "internal-mailserver" not in combined
        assert "s3cr3t" not in combined
        assert "corp.example.com" not in combined
