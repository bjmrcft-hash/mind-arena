"""
Heterogeneous model routing — maps agents to different model types.

Core design: three agents use different models to maximize cognitive diversity.
A = reasoning, B = creative, C = balanced.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ModelAssignment:
    """Model assignment for one agent."""
    agent: str
    model: str
    model_type: str  # "reasoning", "creative", "balanced"
    temperature: float


# Default model presets — can be overridden via env or config
DEFAULT_MODELS = {
    "reasoning": ["deepseek-r1", "gpt-4o", "glm-5"],
    "creative": ["kimi-k2", "claude-sonnet-4-20250514", "deepseek-v4"],
    "balanced": ["qwen3.5-plus", "gemini-2.5-flash", "mimo-v2.5-pro"],
}

AGENT_ROLES = {
    "A": {"type": "reasoning", "temp": 0.5, "desc": "主持人/协调者"},
    "B": {"type": "creative",  "temp": 0.8, "desc": "正方论证者"},
    "C": {"type": "balanced",  "temp": 0.7, "desc": "反方批判者"},
}


class ModelRouter:
    """
    Route agents to models based on role requirements.

    Priority: env vars > explicit config > defaults.
    """

    def __init__(self, model_overrides: dict[str, str] | None = None) -> None:
        self._overrides = model_overrides or {}

    def resolve(self) -> dict[str, ModelAssignment]:
        """
        Resolve model assignments for all agents.

        Returns:
            Dict mapping agent role ("A"/"B"/"C") → ModelAssignment.
        """
        assignments = {}

        for agent, role_info in AGENT_ROLES.items():
            model_type = role_info["type"]

            # Priority: env var > explicit config > first in defaults
            model = (
                os.environ.get(f"MODEL_{agent}")
                or self._overrides.get(agent)
                or DEFAULT_MODELS[model_type][0]
            )

            assignments[agent] = ModelAssignment(
                agent=agent,
                model=model,
                model_type=model_type,
                temperature=role_info["temp"],
            )

        return assignments

    @staticmethod
    def get_model_type(model_name: str) -> str:
        """Infer model type from name (heuristic)."""
        name_lower = model_name.lower()
        if any(k in name_lower for k in ("r1", "o1", "o3", "gpt-4o", "glm-5")):
            return "reasoning"
        if any(k in name_lower for k in ("kimi", "claude-sonnet", "deepseek-v4")):
            return "creative"
        return "balanced"

    @staticmethod
    def check_heterogeneity(assignments: dict[str, ModelAssignment]) -> dict:
        """
        Check if model assignments are heterogeneous.

        Returns:
            Dict with 'unique_count', 'is_heterogeneous', 'warnings'.
        """
        models = [a.model for a in assignments.values()]
        unique = set(models)
        warnings = []

        if len(unique) < len(assignments):
            dupes = [m for m in models if models.count(m) > 1]
            warnings.append(
                f"同模型警告: {set(dupes)} 被多个代理使用。"
                f"建议通过提示词差异化确保输出异构性。"
            )

        return {
            "unique_count": len(unique),
            "is_heterogeneous": len(unique) == len(assignments),
            "warnings": warnings,
        }
