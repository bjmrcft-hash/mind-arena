"""
Round controller — manages round and exchange counting.

Tracks which round we're in, how many exchanges have occurred,
and signals when limits are reached.
"""

from __future__ import annotations

from engine.models.schemas import DebateConfig


class RoundController:
    """
    Manages debate rounds and exchange counts.

    Usage:
        ctrl = RoundController(config)
        ctrl.start_round()           # Begin round 1
        ctrl.record_exchange()       # B or C spoke
        ctrl.complete_round()        # A summarized
        should_end = ctrl.should_end_round()  # Check limit
    """

    def __init__(self, config: DebateConfig) -> None:
        self.config = config
        self.current_round: int = 0
        self.current_exchange: int = 0
        self._total_exchanges: int = 0

    def start_round(self) -> int:
        """Begin a new round. Returns the round number."""
        self.current_round += 1
        self.current_exchange = 0
        return self.current_round

    def record_exchange(self) -> int:
        """Record one exchange (B or C spoke). Returns exchange count."""
        self.current_exchange += 1
        self._total_exchanges += 1
        return self.current_exchange

    def should_end_round(self) -> bool:
        """Check if exchange count has reached the round limit."""
        return self.current_exchange >= self.config.max_exchanges_per_round

    def has_more_rounds(self) -> bool:
        """Check if more rounds are available."""
        return self.current_round < self.config.max_rounds

    def is_final_round(self) -> bool:
        """Check if this is the last round."""
        return self.current_round >= self.config.max_rounds

    def complete_round(self) -> None:
        """Mark current round as completed (for tracking)."""
        # Round completion is tracked by round number increment on next start_round()

    @property
    def total_exchanges(self) -> int:
        return self._total_exchanges

    def reset(self) -> None:
        """Reset all counters."""
        self.current_round = 0
        self.current_exchange = 0
        self._total_exchanges = 0
