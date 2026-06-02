"""
Model health checker — verify model availability before and during debate.

Provides:
- Pre-debate health check for all configured models
- Runtime fallback when a model fails
- Model status tracking
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field

from engine.llm.llm_service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class ModelStatus:
    """Status of a single model."""
    model_id: str
    provider: str  # "qwen", "nvidia", "modelscope", etc.
    available: bool = False
    latency_ms: float = 0
    error: str | None = None
    last_checked: float = 0


@dataclass
class HealthCheckResult:
    """Result of a full health check."""
    models: dict[str, ModelStatus] = field(default_factory=dict)
    all_ok: bool = True
    fallback_chain: list[str] = field(default_factory=list)


# Known fallback chains: primary → backup1 → backup2
FALLBACK_CHAINS: dict[str, list[str]] = {
    "modelscope": ["MiniMax/MiniMax-M1-80k", "ZhipuAI/GLM-5"],
    "nvidia": ["MiniMax/MiniMax-M1-80k", "ZhipuAI/GLM-5"],
    "qwen": ["MiniMax/MiniMax-M1-80k", "ZhipuAI/GLM-5"],
    "xiaomi": ["MiniMax/MiniMax-M1-80k", "ZhipuAI/GLM-5"],
}

# Provider → model name mapping for fallback
PROVIDER_MODELS: dict[str, str] = {
    "modelscope": "MiniMax/MiniMax-M1-80k",
    "nvidia": "deepseek-ai/deepseek-v4-flash",
    "qwen": "qwen-turbo",
}


def _detect_provider(model_id: str) -> str:
    """Detect provider from model name or env."""
    model_lower = model_id.lower()
    if "qwen" in model_lower:
        return "qwen"
    if "deepseek" in model_lower:
        return "nvidia"
    if "kimi-k2" in model_lower:
        return "moonshot"
    if "kimi" in model_lower or "glm" in model_lower:
        return "modelscope"
    if "minimax" in model_lower:
        return "modelscope"
    if "mimo" in model_lower:
        return "xiaomi"
    return "unknown"


async def check_model_health(
    llm: LLMService,
    model_id: str,
    timeout: float = 30.0,
    provider: str | None = None,
) -> ModelStatus:
    """Test a single model with a minimal request."""
    detected = provider or _detect_provider(model_id)
    status = ModelStatus(model_id=model_id, provider=detected)

    # moonshot requires temperature=1
    temp = 1 if detected == "moonshot" else 0

    try:
        import time
        start = time.monotonic()
        content, _ = await asyncio.wait_for(
            llm.chat(
                model=model_id,
                user_message="回复OK",
                system="你是一个测试助手，只需回复OK。",
                temperature=temp,
                max_tokens=10,
                provider=detected,
            ),
            timeout=timeout,
        )
        elapsed = (time.monotonic() - start) * 1000
        status.available = True
        status.latency_ms = elapsed
        logger.info("Model %s health OK (%.0fms)", model_id, elapsed)
    except asyncio.TimeoutError:
        status.error = f"Timeout after {timeout}s"
        logger.warning("Model %s health TIMEOUT", model_id)
    except Exception as e:
        status.error = str(e)[:200]
        logger.warning("Model %s health FAIL: %s", model_id, status.error)

    return status


async def check_all_models(
    model_ids: dict[str, str],
    llm: LLMService | None = None,
) -> HealthCheckResult:
    """
    Check health of all configured models.

    Args:
        model_ids: {"A": "model_name", "B": "model_name", "C": "model_name"}
        llm: LLM service instance (creates default if None)
    """
    if llm is None:
        llm = LLMService()

    result = HealthCheckResult()

    # Check all models in parallel
    tasks = []
    for role, model_id in model_ids.items():
        provider = _detect_provider(model_id)
        tasks.append(check_model_health(llm, model_id, provider=provider))

    statuses = await asyncio.gather(*tasks, return_exceptions=True)

    for (role, model_id), status in zip(model_ids.items(), statuses):
        if isinstance(status, Exception):
            status = ModelStatus(
                model_id=model_id,
                provider=_detect_provider(model_id),
                error=str(status)[:200],
            )
        result.models[role] = status
        if not status.available:
            result.all_ok = False

    # Build fallback chain based on available models
    available_providers = [
        s.provider for s in result.models.values() if s.available
    ]
    if available_providers:
        # Use the fastest available provider as primary fallback
        available_providers.sort(
            key=lambda p: next(
                s.latency_ms for s in result.models.values()
                if s.provider == p and s.available
            )
        )
        result.fallback_chain = available_providers

    return result


def get_fallback_model(
    failed_model: str,
    available_models: dict[str, str],
) -> str | None:
    """
    Find a fallback model when the primary fails.

    Strategy: look at other roles' models that are known to work,
    or use the fallback chain.
    """
    failed_provider = _detect_provider(failed_model)

    # First: try other roles' models that are different from the failed one
    for role, model in available_models.items():
        if model != failed_model:
            return model

    # Second: use fallback chain
    chain = FALLBACK_CHAINS.get(failed_provider, ["qwen", "nvidia"])
    for provider in chain:
        if provider in PROVIDER_MODELS:
            return PROVIDER_MODELS[provider]

    return None
