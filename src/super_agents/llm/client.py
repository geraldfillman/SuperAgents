"""Model-agnostic LLM client wrapping LiteLLM.

Supports:
- Swapping models via config (Claude, GPT-4, Gemini, Llama, etc.)
- Automatic fallback when primary model fails
- Langfuse tracing via callbacks
- Per-task model selection (extraction vs scoring vs summarization)
"""

from __future__ import annotations

import logging
from typing import Any

import litellm

from .config import LLMConfig

logger = logging.getLogger(__name__)

# Optional Langfuse callback — enabled when LANGFUSE_SECRET_KEY is set
try:
    from langfuse.callback import CallbackHandler as LangfuseHandler

    _langfuse_available = True
except ImportError:
    _langfuse_available = False


def _get_callbacks() -> list[Any]:
    """Build callback list (Langfuse if configured)."""
    if _langfuse_available:
        try:
            return [LangfuseHandler()]
        except Exception:
            pass
    return []


def completion(
    prompt: str,
    *,
    model: str | None = None,
    task_type: str = "default",
    config: LLMConfig | None = None,
    system: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Synchronous LLM completion with automatic fallback.

    Args:
        prompt: The user prompt.
        model: Override model name. If None, selected from config by task_type.
        task_type: One of 'default', 'extraction', 'scoring'. Selects model from config.
        config: LLMConfig instance. Uses defaults if None.
        system: Optional system message.
        max_tokens: Override max tokens.
        temperature: Override temperature.

    Returns:
        The model's response text.
    """
    cfg = config or LLMConfig()
    selected_model = model or _select_model(cfg, task_type)
    fallback_model = cfg.fallback_model

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": selected_model,
        "messages": messages,
        "max_tokens": max_tokens or cfg.max_tokens,
        "temperature": temperature if temperature is not None else cfg.temperature,
    }

    callbacks = _get_callbacks()
    if callbacks:
        kwargs["callbacks"] = callbacks

    try:
        response = litellm.completion(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as exc:
        if fallback_model and fallback_model != selected_model:
            logger.warning(
                "Primary model %s failed (%s), falling back to %s",
                selected_model,
                exc,
                fallback_model,
            )
            kwargs["model"] = fallback_model
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content or ""
        raise


async def acompletion(
    prompt: str,
    *,
    model: str | None = None,
    task_type: str = "default",
    config: LLMConfig | None = None,
    system: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Async LLM completion with automatic fallback."""
    cfg = config or LLMConfig()
    selected_model = model or _select_model(cfg, task_type)
    fallback_model = cfg.fallback_model

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": selected_model,
        "messages": messages,
        "max_tokens": max_tokens or cfg.max_tokens,
        "temperature": temperature if temperature is not None else cfg.temperature,
    }

    callbacks = _get_callbacks()
    if callbacks:
        kwargs["callbacks"] = callbacks

    try:
        response = await litellm.acompletion(**kwargs)
        return response.choices[0].message.content or ""
    except Exception as exc:
        if fallback_model and fallback_model != selected_model:
            logger.warning(
                "Primary model %s failed (%s), falling back to %s",
                selected_model,
                exc,
                fallback_model,
            )
            kwargs["model"] = fallback_model
            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content or ""
        raise


def _select_model(config: LLMConfig, task_type: str) -> str:
    """Select model based on task type."""
    model_map = {
        "default": config.default_model,
        "extraction": config.extraction_model,
        "scoring": config.scoring_model,
    }
    return model_map.get(task_type, config.default_model)
