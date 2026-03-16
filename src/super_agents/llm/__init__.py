"""Model-agnostic LLM abstraction layer using LiteLLM."""

from __future__ import annotations

from typing import Any

from .config import load_llm_config


def completion(*args: Any, **kwargs: Any):
    """Lazily import the LiteLLM-backed sync client."""
    from .client import completion as _completion

    return _completion(*args, **kwargs)


async def acompletion(*args: Any, **kwargs: Any):
    """Lazily import the LiteLLM-backed async client."""
    from .client import acompletion as _acompletion

    return await _acompletion(*args, **kwargs)


__all__ = ["completion", "acompletion", "load_llm_config"]
