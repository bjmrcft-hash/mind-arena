"""
Base agent — abstract class for all debate agents.

Handles LLM calls, streaming, prompt loading, and token counting.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from pathlib import Path

from engine.llm.llm_service import LLMService
from engine.models.schemas import DebateConfig, Message

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BaseAgent(ABC):
    """Abstract base for debate agents."""

    role: str  # "A", "B", or "C"

    def __init__(self, llm: LLMService, model: str, temperature: float = 0.7) -> None:
        self.llm = llm
        self.model = model
        self.temperature = temperature
        self._system_prompt_template: str = ""

    def load_prompt(self, filename: str) -> None:
        """Load system prompt from prompts/ directory."""
        path = PROMPTS_DIR / filename
        if path.exists():
            self._system_prompt_template = path.read_text(encoding="utf-8").strip()
        else:
            logger.warning("Prompt file not found: %s", path)

    def _render_prompt(self, config: DebateConfig) -> str:
        """Render prompt template with config values."""
        return self._system_prompt_template.format(
            max_rounds=config.max_rounds,
            max_exchanges=config.max_exchanges_per_round,
            min_length=config.message_min_length,
            max_length=config.message_max_length,
        )

    @abstractmethod
    async def generate_response(
        self,
        context: str,
        config: DebateConfig,
    ) -> tuple[str, int]:
        """
        Generate a complete response (non-streaming).

        Returns:
            (content, token_count)
        """
        ...

    @abstractmethod
    async def generate_response_stream(
        self,
        context: str,
        config: DebateConfig,
    ) -> AsyncGenerator[str, int]:
        """
        Generate a streaming response.

        Yields text chunks. Final token count accessible after iteration.
        """
        ...

    def _truncate_to_range(self, text: str, config: DebateConfig) -> str:
        """Ensure output stays within configured length bounds."""
        if len(text) > config.message_max_length:
            # Try to cut at sentence boundary
            cut = text[:config.message_max_length]
            last_period = max(cut.rfind("。"), cut.rfind("！"), cut.rfind("？"))
            if last_period > config.message_min_length:
                return cut[:last_period + 1]
            return cut + "..."
        return text
