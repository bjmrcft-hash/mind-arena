"""
Unified LLM service — wraps OpenAI Python SDK for any compatible provider.

Supports streaming and non-streaming, automatic retries, and token counting.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError

logger = logging.getLogger(__name__)


class LLMService:
    """
    Async LLM wrapper supporting any OpenAI-compatible API.

    Supports multiple providers with automatic model→provider resolution.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        max_retries: int = 3,
        timeout: float = 120.0,
    ) -> None:
        self._default_client = AsyncOpenAI(
            base_url=base_url or os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
            api_key=api_key or os.environ.get("LLM_API_KEY", "sk-placeholder"),
            timeout=timeout,
            max_retries=0,
        )
        self._timeout = timeout
        self.max_retries = max_retries
        # Multi-provider client cache: name → AsyncOpenAI
        self._providers: dict[str, AsyncOpenAI] = {}
        # Model → provider mapping (set by engine after preflight)
        self._model_to_provider: dict[str, str] = {}

    def register_provider(self, name: str, base_url: str, api_key: str) -> None:
        """Register a named provider with its own base_url and api_key."""
        self._providers[name] = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=self._timeout,
            max_retries=0,
        )

    def set_model_provider(self, model: str, provider: str) -> None:
        """Bind a model to a specific provider. Called by engine after preflight."""
        self._model_to_provider[model] = provider

    def _get_client(self, provider: str | None = None, model: str | None = None) -> AsyncOpenAI:
        """Get client for a provider, auto-resolving from model name if needed."""
        # Explicit provider takes priority
        if provider and provider in self._providers:
            return self._providers[provider]
        # Auto-resolve from model→provider mapping
        if model and model in self._model_to_provider:
            p = self._model_to_provider[model]
            if p in self._providers:
                return self._providers[p]
        return self._default_client

    async def chat(
        self,
        model: str,
        user_message: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str | None = None,
    ) -> tuple[str, int]:
        messages = self._build_messages(system, user_message)
        client = self._get_client(provider, model)

        for attempt in range(self.max_retries):
            try:
                resp = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                content = resp.choices[0].message.content or ""
                tokens = resp.usage.total_tokens if resp.usage else self._approx_tokens(content)
                return content, tokens
            except (RateLimitError, APIConnectionError) as e:
                wait = 2 ** attempt
                logger.warning("LLM retry %d/%d after %ds: %s", attempt + 1, self.max_retries, wait, e)
                await asyncio.sleep(wait)
            except APIStatusError as e:
                logger.error("LLM API error (status %d): %s", e.status_code, e.message)
                raise

        raise RuntimeError(f"LLM call failed after {self.max_retries} retries")

    async def chat_stream(
        self,
        model: str,
        user_message: str,
        *,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        provider: str | None = None,
    ) -> AsyncGenerator[str, int]:
        messages = self._build_messages(system, user_message)
        total_tokens = 0
        client = self._get_client(provider, model)

        for attempt in range(self.max_retries):
            try:
                stream = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True,
                    stream_options={"include_usage": True},
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        total_tokens += self._approx_tokens(text)
                        yield text
                    if chunk.usage and chunk.usage.total_tokens:
                        total_tokens = chunk.usage.total_tokens

                return
            except (RateLimitError, APIConnectionError) as e:
                wait = 2 ** attempt
                logger.warning("LLM stream retry %d/%d after %ds: %s", attempt + 1, self.max_retries, wait, e)
                await asyncio.sleep(wait)
            except APIStatusError as e:
                logger.error("LLM API error (status %d): %s", e.status_code, e.message)
                raise

        raise RuntimeError(f"LLM streaming failed after {self.max_retries} retries")

    @staticmethod
    def _build_messages(system: str | None, user: str) -> list[dict[str, str]]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        return messages

    @staticmethod
    def _approx_tokens(text: str) -> int:
        cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other = len(text) - cn_chars
        return int(cn_chars * 1.5 + other * 0.25)

    async def close(self) -> None:
        await self._default_client.close()
