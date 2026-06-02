"""
Three-dimension cold start detection.

Detects when debate is stalling and A should intervene:
1. Semantic repetition — recent messages too similar to previous ones
2. Length drop — consecutive messages below minimum length
3. Keyword repetition — high keyword overlap in recent messages
"""

from __future__ import annotations

import re
from collections import Counter

from engine.models.schemas import Message, DebateConfig


class ColdStartDetector:
    """Three-dimension cold start detector."""

    def __init__(self, config: DebateConfig) -> None:
        self.similarity_threshold = config.similarity_threshold
        self.consecutive_limit = config.cold_start_threshold
        self.min_length = config.message_min_length
        self._consecutive_low = 0

    def check(self, recent_messages: list[Message]) -> bool:
        """
        Check if debate is cold-starting.

        Only triggers after enough messages to avoid premature interruption.
        """
        # Need at least 4 B/C messages before checking (2 full exchanges)
        bc_count = sum(1 for m in recent_messages if m.role in ("B", "C"))
        if bc_count < 4:
            return False

        # Dimension 1: Semantic repetition (need 4+ messages)
        if len(recent_messages) >= 4:
            if self._check_semantic_repetition(recent_messages[-2:], recent_messages[-4:-2]):
                return True

        # Dimension 2: Length drop (check all recent messages to track consecutive)
        if self._check_length_drop(recent_messages):
            return True

        # Dimension 3: Keyword repetition (need 6+ messages)
        if len(recent_messages) >= 6:
            if self._check_keyword_repetition(recent_messages[-6:]):
                return True

        return False

    def _check_semantic_repetition(
        self, recent: list[Message], previous: list[Message]
    ) -> bool:
        """Check if recent messages are too similar to previous ones."""
        recent_text = " ".join(m.content for m in recent)
        prev_text = " ".join(m.content for m in previous)

        # Use keyword overlap as lightweight similarity proxy
        recent_kw = self._extract_keywords(recent_text)
        prev_kw = self._extract_keywords(prev_text)

        if not prev_kw:
            return False

        overlap = len(recent_kw & prev_kw)
        total = len(recent_kw | prev_kw)
        similarity = overlap / total if total > 0 else 0

        return similarity > self.similarity_threshold

    def _check_length_drop(self, messages: list[Message]) -> bool:
        """Check if consecutive messages are below minimum length."""
        self._consecutive_low = 0
        for msg in messages:
            if len(msg.content) < self.min_length:
                self._consecutive_low += 1
            else:
                self._consecutive_low = 0
        return self._consecutive_low >= self.consecutive_limit

    def _check_keyword_repetition(self, messages: list[Message]) -> bool:
        """Check if keyword repetition rate is too high across recent messages."""
        all_keywords: list[str] = []
        for msg in messages:
            all_keywords.extend(self._extract_keywords(msg.content))

        if not all_keywords:
            return False

        counter = Counter(all_keywords)
        total = len(all_keywords)
        repeated_count = sum(count for count in counter.values() if count >= 3)

        return (repeated_count / total) > 0.7 if total > 0 else False

    @staticmethod
    def _extract_keywords(text: str, top_n: int = 20) -> set[str]:
        """
        Extract keywords from Chinese text.
        Simple approach: split by punctuation/whitespace, filter short/common words.
        """
        # Split on punctuation and whitespace
        words = re.split(r'[，。！？、；：\u201c\u201d\u2018\u2019（）\s\.\!\?\;\:\,\(\)]+', text)
        # Filter: length >= 2, not purely numeric, not common stop words
        stop_words = {
            "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
            "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你",
            "会", "着", "没有", "看", "好", "自己", "这", "他", "她", "它",
            "那", "但", "而", "所以", "因为", "如果", "可以", "这个", "那个",
            "什么", "怎么", "为什么", "还", "又", "再", "更", "最", "非常",
            "已经", "可能", "应该", "需要", "能够", "以及", "或者", "但是",
            "然而", "因此", "所以", "虽然", "不过", "只是", "而是", "这样",
            "那样", "这些", "那些", "一些", "每个", "任何", "所有",
        }
        keywords = set()
        for w in words:
            w = w.strip().lower()
            if len(w) >= 2 and not w.isdigit() and w not in stop_words:
                keywords.add(w)
        return keywords

    def reset(self) -> None:
        """Reset internal counters."""
        self._consecutive_low = 0
