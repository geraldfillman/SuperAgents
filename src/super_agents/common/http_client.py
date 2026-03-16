"""Shared HTTP client with retry, rate-limit awareness, and consistent headers.

Every skill script that makes external API calls should use this module
instead of rolling its own httpx/requests setup. This gives us:

- Exponential backoff with jitter on transient failures
- Automatic rate-limit detection (429 / Retry-After)
- Consistent User-Agent across all agents
- One place to add request logging or metrics later
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

from .env import optional_env

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_USER_AGENT = optional_env(
    "SUPER_AGENTS_USER_AGENT",
    "SuperAgents/0.1 research@example.com",
)

DEFAULT_TIMEOUT = float(optional_env("SUPER_AGENTS_HTTP_TIMEOUT", "30"))
DEFAULT_MAX_RETRIES = int(optional_env("SUPER_AGENTS_HTTP_MAX_RETRIES", "3"))
DEFAULT_BACKOFF_BASE = 1.0  # seconds


# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------

_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


def _backoff_delay(attempt: int, base: float = DEFAULT_BACKOFF_BASE) -> float:
    """Exponential backoff with jitter: base * 2^attempt + random(0..base)."""
    import random

    return base * (2 ** attempt) + random.uniform(0, base)


def _parse_retry_after(response: httpx.Response) -> float | None:
    """Extract Retry-After header value in seconds, if present."""
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return float(header)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Core request functions
# ---------------------------------------------------------------------------

def resilient_get(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    user_agent: str = DEFAULT_USER_AGENT,
    follow_redirects: bool = True,
) -> httpx.Response:
    """Perform a GET request with automatic retry on transient failures.

    Args:
        url: The URL to fetch.
        params: Optional query parameters.
        headers: Additional headers (merged with defaults).
        timeout: Request timeout in seconds.
        max_retries: Maximum number of retry attempts.
        user_agent: User-Agent string.
        follow_redirects: Whether to follow HTTP redirects.

    Returns:
        The httpx.Response object.

    Raises:
        httpx.HTTPStatusError: On non-retryable 4xx/5xx after exhausting retries.
        httpx.RequestError: On connection failures after exhausting retries.
    """
    merged_headers = {"User-Agent": user_agent, "Accept": "application/json"}
    if headers:
        merged_headers.update(headers)

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = httpx.get(
                url,
                params=params,
                headers=merged_headers,
                timeout=timeout,
                follow_redirects=follow_redirects,
            )

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response

            # Retryable status — back off
            retry_after = _parse_retry_after(response)
            delay = retry_after if retry_after is not None else _backoff_delay(attempt)

            if attempt < max_retries:
                logger.warning(
                    "HTTP %d from %s — retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    url,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(delay)
                continue

            # Final attempt — raise
            response.raise_for_status()
            return response  # pragma: no cover — raise_for_status would fire

        except httpx.RequestError as exc:
            last_error = exc
            if attempt < max_retries:
                delay = _backoff_delay(attempt)
                logger.warning(
                    "Connection error for %s — retrying in %.1fs (attempt %d/%d): %s",
                    url,
                    delay,
                    attempt + 1,
                    max_retries,
                    exc,
                )
                time.sleep(delay)
                continue
            raise

    # Should not reach here, but satisfy type checker
    if last_error:
        raise last_error
    raise RuntimeError(f"Exhausted retries for {url}")  # pragma: no cover


def resilient_post(
    url: str,
    *,
    json: Any | None = None,
    data: Any | None = None,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    user_agent: str = DEFAULT_USER_AGENT,
) -> httpx.Response:
    """Perform a POST request with automatic retry on transient failures.

    Same retry semantics as resilient_get.
    """
    merged_headers = {"User-Agent": user_agent}
    if json is not None:
        merged_headers["Content-Type"] = "application/json"
        merged_headers["Accept"] = "application/json"
    if headers:
        merged_headers.update(headers)

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = httpx.post(
                url,
                json=json,
                data=data,
                params=params,
                headers=merged_headers,
                timeout=timeout,
            )

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                response.raise_for_status()
                return response

            retry_after = _parse_retry_after(response)
            delay = retry_after if retry_after is not None else _backoff_delay(attempt)

            if attempt < max_retries:
                logger.warning(
                    "HTTP %d from %s — retrying in %.1fs (attempt %d/%d)",
                    response.status_code,
                    url,
                    delay,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(delay)
                continue

            response.raise_for_status()
            return response  # pragma: no cover

        except httpx.RequestError as exc:
            last_error = exc
            if attempt < max_retries:
                delay = _backoff_delay(attempt)
                logger.warning(
                    "Connection error for %s — retrying in %.1fs (attempt %d/%d): %s",
                    url,
                    delay,
                    attempt + 1,
                    max_retries,
                    exc,
                )
                time.sleep(delay)
                continue
            raise

    if last_error:
        raise last_error
    raise RuntimeError(f"Exhausted retries for {url}")  # pragma: no cover


def head_check(url: str, *, timeout: float = 10) -> tuple[bool, int | str]:
    """Quick HEAD check for URL validity.

    Returns:
        Tuple of (is_reachable, status_code_or_error_string).
    """
    try:
        response = httpx.head(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        return response.status_code < 400, response.status_code
    except httpx.RequestError as exc:
        return False, str(exc)
