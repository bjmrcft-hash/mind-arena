"""
Context manager — builds LLM context with rolling summary compression.

Strategy: current round full + previous rounds compressed.
Total context target: ~3900 tokens (well below model limits).
"""

from __future__ import annotations

from engine.models.schemas import Message, DebateConfig


class ContextManager:
    """
    Build context strings for LLM calls.

    Context structure:
    ① System Prompt           ~500 tokens
    ② Debate meta-info        ~100 tokens
    ③ Current round full      ~2000 tokens (most important)
    ④ Previous rounds summary ~500 tokens
    ⑤ Output format           ~100 tokens
    ⑥ Reserved output         ~800 tokens
    """

    def __init__(self, config: DebateConfig) -> None:
        self.config = config
        self._round_summaries: dict[int, str] = {}  # round_number → summary

    def add_round_summary(self, round_number: int, summary: str) -> None:
        """Store A's summary for a completed round."""
        self._round_summaries[round_number] = summary

    def build_context(
        self,
        role: str,
        system_prompt: str,
        topic: str,
        current_round: int,
        current_exchange: int,
        dimension: str | None,
        current_messages: list[Message],
        agent_stance: str | None = None,
    ) -> str:
        """
        Build full context for an agent's LLM call.

        Args:
            role: "A", "B", or "C"
            system_prompt: The agent's system prompt (already templated)
            topic: The debate topic
            current_round: Current round number
            current_exchange: Current exchange number within round
            dimension: Current analysis dimension (set by A)
            current_messages: All messages in the current round
            agent_stance: B/C's assigned stance description

        Returns:
            Complete context string for LLM.
        """
        parts = []

        # ① System prompt (passed as system message, not here)
        # ② Meta info
        meta = self._build_meta(topic, current_round, current_exchange, dimension, role, agent_stance)
        parts.append(meta)

        # ③ Previous rounds summaries
        if self._round_summaries:
            parts.append(self._build_previous_summaries())

        # ④ Current round history
        if current_messages:
            parts.append(self._build_current_history(current_messages))

        return "\n\n".join(parts)

    def _build_meta(
        self,
        topic: str,
        current_round: int,
        current_exchange: int,
        dimension: str | None,
        role: str,
        stance: str | None,
    ) -> str:
        lines = [
            f"【辩论信息】",
            f"话题：{topic}",
            f"当前轮次：第 {current_round} 轮 / 共 {self.config.max_rounds} 轮",
            f"当前交锋：第 {current_exchange} 次 / 上限 {self.config.max_exchanges_per_round} 次",
            f"你的角色：{role}",
        ]
        if dimension:
            lines.append(f"本轮分析维度：{dimension}")
        if stance:
            lines.append(f"你的立场：{stance}")
        # Depth guidance based on exchange count
        if current_exchange <= 1:
            lines.append("\n【辩论要求】这是本轮首次交锋，请深入阐述你的核心论据，给出具体数据和案例。")
        elif current_exchange <= 3:
            lines.append("\n【辩论要求】辩论正在深入，请针对对方上一轮的具体论据逐条反驳，追问数据来源，不要回避对方的核心质疑。")
        else:
            lines.append("\n【辩论要求】这是本轮后期交锋，请聚焦双方的核心分歧点，用更精确的数据和案例进行最终交锋，避免重复。")
        return "\n".join(lines)

    def _build_previous_summaries(self) -> str:
        lines = ["【前轮摘要】"]
        for rnd in sorted(self._round_summaries.keys()):
            lines.append(f"第 {rnd} 轮总结：{self._round_summaries[rnd]}")
        return "\n".join(lines)

    def _build_current_history(self, messages: list[Message]) -> str:
        lines = ["【本轮辩论记录】"]
        for msg in messages:
            role_label = {"A": "主持人A", "B": "正方B", "C": "反方C"}[msg.role]
            lines.append(f"[{role_label}] {msg.content}")
        return "\n".join(lines)

    def reset(self) -> None:
        """Clear all stored summaries."""
        self._round_summaries.clear()
