"""
Agent A — Moderator / Host.

Responsibilities:
- TOPIC_INTRO: Decompose topic, assign B/C stances
- LEVEL_UP: Set new analytical dimension each round
- SUMMARIZING: Summarize round results
- FINAL: Final verdict summary
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from engine.agents.base_agent import BaseAgent
from engine.llm.llm_service import LLMService
from engine.models.schemas import DebateConfig


class ModeratorA(BaseAgent):
    """Agent A — Moderator and debate host."""

    role = "A"

    def __init__(self, llm: LLMService, model: str, temperature: float = 0.5) -> None:
        super().__init__(llm, model, temperature)
        self.load_prompt("moderator.md")

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
        full_text = ""
        async for chunk in self.llm.chat_stream(
            model=self.model,
            user_message=context,
            system=system,
            temperature=self.temperature,
            max_tokens=1500,
        ):
            full_text += chunk
            yield chunk

    async def generate_topic_intro(self, topic: str, config: DebateConfig) -> tuple[str, int]:
        """Generate the opening topic decomposition."""
        context = (
            f"请对以下辩论话题进行开场介绍。\n\n"
            f"话题：{topic}\n\n"
            f"你的任务（仅限开场，不要涉及任何轮次内容）：\n"
            f"1. 介绍这个话题的背景和讨论价值（2-3句话）\n"
            f"2. 将话题拆解为两个对立的分析视角\n"
            f"3. 明确分配立场：B 持视角 1（正方），C 持视角 2（反方）\n"
            f"4. 宣布辩论规则：共 {config.max_rounds} 轮，每轮交锋上限 {config.max_exchanges_per_round} 次\n"
            f"5. 强调双方必须针对对方的具体论据和数据进行逐条反驳\n\n"
            f"⚠️ 严格禁止：不要设定任何分析维度，不要提及第几轮具体内容，不要预判辩论方向。"
            f"开场只做话题介绍和规则宣布，维度设定将在每轮开始时单独进行。"
        )
        return await self.generate_response(context, config)

    async def generate_level_up(
        self, topic: str, round_number: int, config: DebateConfig
    ) -> tuple[str, int]:
        """Generate the dimension upgrade for a new round."""
        if round_number == 1:
            # 第1轮：承接开场，设定第一个维度
            context = (
                f"辩论话题：{topic}\n\n"
                f"双方已完成开场陈述。现在由你设定第一个分析维度，引导辩论进入深入交锋。\n\n"
                f"你的任务：\n"
                f"1. 明确本轮的分析视角（例如：技术层面、经济层面、伦理层面、实践层面等）\n"
                f"2. 提出本轮的**核心争议焦点**（一个具体的争论问题）\n"
                f"3. 给出2-3个**引导性问题**，要求B/C必须回答\n\n"
                f"⚠️ 严格禁止：不要重复开场介绍，不要宣布\"进入第1轮\"，不要代替B/C发言，不要给出自己的观点。"
            )
        else:
            # 第2轮及以后：总结上轮，引出新维度
            context = (
                f"辩论话题：{topic}\n"
                f"现在进入第 {round_number} 轮（共 {config.max_rounds} 轮）。\n\n"
                f"你的任务：为本轮设定一个新的分析维度。\n\n"
                f"要求：\n"
                f"1. 明确本轮的分析视角（例如：技术层面、经济层面、伦理层面、实践层面等）\n"
                f"2. 提出本轮的**核心争议焦点**（一个具体的争论问题）\n"
                f"3. 给出2-3个**引导性问题**，要求B/C必须回答\n"
                f"4. 简要指出上一轮中**未被充分论证**的薄弱环节\n\n"
                f"⚠️ 严格禁止：不要重复开场介绍，不要代替B/C发言，不要给出自己的观点。"
            )
        return await self.generate_response(context, config)

    async def generate_summary(
        self, topic: str, round_number: int, round_messages: str, config: DebateConfig
    ) -> tuple[str, int]:
        """Generate round summary."""
        context = (
            f"辩论话题：{topic}\n"
            f"第 {round_number} 轮辩论记录：\n\n{round_messages}\n\n"
            f"请对本轮辩论进行精确总结。"
        )
        return await self.generate_response(context, config)

    async def generate_verdict(
        self, topic: str, all_summaries: str, config: DebateConfig
    ) -> tuple[str, int]:
        """Generate final verdict."""
        context = (
            f"辩论话题：{topic}\n\n"
            f"各轮总结：\n{all_summaries}\n\n"
            f"请进行终场总结。概括辩论精华、立场演变、核心矛盾和未解之题。"
            f"注意：不对任何一方做价值判断或胜负裁决。"
        )
        return await self.generate_response(context, config)
