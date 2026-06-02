"""
Agent B — Pro Debater (正方论证者).

Each response: 【回应对方】30-40% + 【发表己见】60-70%.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from engine.agents.base_agent import BaseAgent
from engine.llm.llm_service import LLMService
from engine.models.schemas import DebateConfig


class DebaterB(BaseAgent):
    """Agent B — Pro-side debater."""

    role = "B"

    def __init__(self, llm: LLMService, model: str, temperature: float = 0.8) -> None:
        super().__init__(llm, model, temperature)
        self.load_prompt("debater_b.md")

    def _render_prompt(self, config: DebateConfig) -> str:
        return self._system_prompt_template.format(
            min_length=config.message_min_length,
            max_length=config.message_max_length,
        )

    async def generate_response(
        self,
        context: str,
        config: DebateConfig,
    ) -> tuple[str, int]:
        system = self._render_prompt(config)
        content, tokens = await self.llm.chat(
            model=self.model,
            user_message=context,
            system=system,
            temperature=self.temperature,
            max_tokens=2000,
        )
        return self._truncate_to_range(content, config), tokens

    async def generate_response_stream(
        self,
        context: str,
        config: DebateConfig,
    ) -> AsyncGenerator[str, int]:
        system = self._render_prompt(config)
        async for chunk in self.llm.chat_stream(
            model=self.model,
            user_message=context,
            system=system,
            temperature=self.temperature,
            max_tokens=1200,
        ):
            yield chunk
