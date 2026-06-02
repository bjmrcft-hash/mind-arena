"""
Topic deviation detector — checks if debate has drifted from original topic.

Uses keyword coverage as a lightweight proxy (no embedding model needed).
"""

from __future__ import annotations

import re

from engine.models.schemas import Message


class DeviationDetector:
    """Detect when debate has drifted off-topic."""

    def __init__(self, deviation_threshold: float = 0.2, min_exchanges: int = 3) -> None:
        self.deviation_threshold = deviation_threshold
        self.min_exchanges = min_exchanges  # Don't trigger before this many exchanges
        self._consecutive_deviations: int = 0
        self._required_consecutive: int = 2  # Need N consecutive deviations to trigger

    def check(self, topic: str, recent_messages: list[Message]) -> bool:
        """
        Check if recent messages have deviated from the topic.

        Only triggers after min_exchanges AND requires consecutive detections.
        """
        # Count B/C messages to determine exchange count
        bc_count = sum(1 for m in recent_messages if m.role in ("B", "C"))
        if bc_count < self.min_exchanges:
            self._consecutive_deviations = 0
            return False

        topic_keywords = self._extract_keywords(topic)
        if not topic_keywords:
            return False

        recent_text = " ".join(m.content for m in recent_messages[-4:])
        recent_keywords = self._extract_keywords(recent_text)

        if not recent_keywords:
            return False

        # Keyword coverage: what fraction of topic keywords appear in recent messages
        coverage = len(topic_keywords & recent_keywords) / len(topic_keywords)

        if coverage < self.deviation_threshold:
            self._consecutive_deviations += 1
        else:
            self._consecutive_deviations = 0

        return self._consecutive_deviations >= self._required_consecutive

    def reset(self) -> None:
        """Reset consecutive counter."""
        self._consecutive_deviations = 0

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        """Extract keywords from Chinese text."""
        words = re.split(r'[，。！？、；：\u201c\u201d\u2018\u2019（）\s\.\!\?\;\:\,\(\)]+', text)
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
            "那", "但", "而", "所以", "因为", "如果", "可以", "这个", "那个",
            "什么", "怎么", "为什么", "还", "又", "再", "更", "最", "非常",
        }
        keywords = set()
        for w in words:
            w = w.strip().lower()
            if len(w) >= 2 and not w.isdigit() and w not in stop_words:
                keywords.add(w)
        return keywords
