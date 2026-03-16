"""
Environment variable utilities for Super Agents.

All external secrets MUST be loaded via `require_env()` — never use
`os.getenv("KEY", "")` for required configuration. Silent empty-string
defaults hide misconfiguration until network calls fail at runtime.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def require_env(name: str) -> str:
    """Return the value of an environment variable, raising if absent or empty.

    Args:
        name: The environment variable name.

    Returns:
        The non-empty string value.

    Raises:
        RuntimeError: If the variable is missing or set to an empty string.

    Example::

        api_key = require_env("OPENFDA_API_KEY")
    """
    value = os.getenv(name, "")
    if not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set or is empty. "
            f"Add it to your .env file or export it before running."
        )
    return value


def optional_env(name: str, default: str = "") -> str:
    """Return the value of an optional environment variable.

    Unlike ``require_env``, this does not raise when the variable is absent.
    Use only for genuinely optional configuration (e.g. API keys that
    affect rate limits but are not required for the call to succeed).

    Args:
        name: The environment variable name.
        default: Fallback value if the variable is absent or empty.

    Returns:
        The variable value, or ``default``.
    """
    return os.getenv(name, default) or default


def validate_env_block(required: list[str], context: str = "") -> None:
    """Assert that all environment variables in *required* are present.

    Collects all missing keys and raises a single ``RuntimeError`` listing
    them all, rather than failing on the first missing key.

    Args:
        required: List of environment variable names that must be set.
        context: Optional label for the error message (e.g. "SMTP config").

    Raises:
        RuntimeError: If any required variables are missing.
    """
    missing = [name for name in required if not os.getenv(name, "")]
    if missing:
        block = ", ".join(missing)
        label = f" ({context})" if context else ""
        raise RuntimeError(
            f"Missing required environment variables{label}: {block}. "
            f"Add them to your .env file or export them before running."
        )
