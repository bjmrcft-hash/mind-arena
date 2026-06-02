"""
Formal Finite State Machine for MindArena debate engine.

States: IDLE, TOPIC_INTRO, OPENING, EXCHANGING, SUMMARIZING,
        LEVEL_UP, FINAL, COMPLETED, PAUSED, STOPPED, ERROR

Inspired by XState formalism — every transition is explicit and validated.
"""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# ── States ──────────────────────────────────────────────────────────

IDLE = "idle"
TOPIC_INTRO = "topic_intro"
OPENING = "opening"
EXCHANGING = "exchanging"
SUMMARIZING = "summarizing"
LEVEL_UP = "level_up"
FINAL = "final"
COMPLETED = "completed"
PAUSED = "paused"
STOPPED = "stopped"
ERROR = "error"

ALL_STATES = {
    IDLE, TOPIC_INTRO, OPENING, EXCHANGING, SUMMARIZING,
    LEVEL_UP, FINAL, COMPLETED, PAUSED, STOPPED, ERROR,
}

# ── Events ──────────────────────────────────────────────────────────

START = "start"
A_DONE = "a_done"
BC_OPENED = "bc_opened"
EXCHANGE_LIMIT = "exchange_limit"
COLD_START = "cold_start"
USER_SKIP = "user_skip"
A_SUMMARIZED = "a_summarized"
ROUND_REMAIN = "round_remain"
ROUND_EXHAUST = "round_exhaust"
A_VERDICT = "a_verdict"
USER_PAUSE = "user_pause"
USER_RESUME = "user_resume"
USER_STOP = "user_stop"
ERROR_EVENT = "error"

ALL_EVENTS = {
    START, A_DONE, BC_OPENED, EXCHANGE_LIMIT, COLD_START,
    USER_SKIP, A_SUMMARIZED, ROUND_REMAIN, ROUND_EXHAUST,
    A_VERDICT, USER_PAUSE, USER_RESUME, USER_STOP, ERROR_EVENT,
}

# ── Transition table ────────────────────────────────────────────────
# (current_state, event) -> (target_state, description)
# None target means "return to state before pause"

TRANSITIONS: dict[tuple[str, str], tuple[str | None, str]] = {
    (IDLE, START):              (TOPIC_INTRO, "Create session, A decompose topic"),
    (TOPIC_INTRO, A_DONE):      (OPENING, "Broadcast A intro, assign B/C stances"),
    (OPENING, BC_OPENED):       (EXCHANGING, "B/C each complete 1 opening statement"),
    (EXCHANGING, EXCHANGE_LIMIT): (SUMMARIZING, "Exchange count reached limit"),
    (EXCHANGING, COLD_START):   (SUMMARIZING, "Cold start detection triggered"),
    (EXCHANGING, USER_SKIP):    (SUMMARIZING, "User skipped round"),
    (SUMMARIZING, A_SUMMARIZED): (LEVEL_UP, "A completed round summary"),
    (LEVEL_UP, ROUND_REMAIN):   (EXCHANGING, "More rounds remaining"),
    (LEVEL_UP, ROUND_EXHAUST):  (FINAL, "All rounds completed"),
    (FINAL, A_VERDICT):         (COMPLETED, "A completed final summary"),
    # Pause/resume from any active state
    (IDLE, USER_PAUSE):         (PAUSED, "Paused"),
    (TOPIC_INTRO, USER_PAUSE):  (PAUSED, "Paused"),
    (OPENING, USER_PAUSE):      (PAUSED, "Paused"),
    (EXCHANGING, USER_PAUSE):   (PAUSED, "Paused"),
    (SUMMARIZING, USER_PAUSE):  (PAUSED, "Paused"),
    (LEVEL_UP, USER_PAUSE):     (PAUSED, "Paused"),
    (FINAL, USER_PAUSE):        (PAUSED, "Paused"),
    (PAUSED, USER_RESUME):      (None, "Resumed to previous state"),
    # Stop from any active state
    (IDLE, USER_STOP):          (STOPPED, "Stopped"),
    (TOPIC_INTRO, USER_STOP):   (STOPPED, "Stopped"),
    (OPENING, USER_STOP):       (STOPPED, "Stopped"),
    (EXCHANGING, USER_STOP):    (STOPPED, "Stopped"),
    (SUMMARIZING, USER_STOP):   (STOPPED, "Stopped"),
    (LEVEL_UP, USER_STOP):      (STOPPED, "Stopped"),
    (FINAL, USER_STOP):         (STOPPED, "Stopped"),
    (PAUSED, USER_STOP):        (STOPPED, "Stopped"),
    # Error from any non-terminal state
    (IDLE, ERROR_EVENT):        (ERROR, "Error occurred"),
    (TOPIC_INTRO, ERROR_EVENT): (ERROR, "Error occurred"),
    (OPENING, ERROR_EVENT):     (ERROR, "Error occurred"),
    (EXCHANGING, ERROR_EVENT):  (ERROR, "Error occurred"),
    (SUMMARIZING, ERROR_EVENT): (ERROR, "Error occurred"),
    (LEVEL_UP, ERROR_EVENT):    (ERROR, "Error occurred"),
    (FINAL, ERROR_EVENT):       (ERROR, "Error occurred"),
    (PAUSED, ERROR_EVENT):      (ERROR, "Error occurred"),
}


class InvalidTransitionError(Exception):
    """Raised when an event is not valid in the current state."""
    def __init__(self, state: str, event: str):
        self.state = state
        self.event = event
        super().__init__(f"Invalid transition: cannot handle '{event}' in state '{state}'")


class DebateStateMachine:
    """
    Formal FSM for debate lifecycle.

    Usage:
        fsm = DebateStateMachine()
        fsm.transition("start")          # idle → topic_intro
        fsm.transition("a_done")         # topic_intro → opening
        ...
        fsm.transition("user_pause")     # exchanging → paused
        fsm.transition("user_resume")    # paused → exchanging (previous state)
    """

    def __init__(self) -> None:
        self._state: str = IDLE
        self._pre_pause_state: str | None = None
        self._history: list[tuple[str, str, str]] = []  # (from, event, to)
        self._callbacks: list[Callable[[str, str, str], None]] = []

    @property
    def state(self) -> str:
        return self._state

    @property
    def history(self) -> list[tuple[str, str, str]]:
        return list(self._history)

    def on_transition(self, callback: Callable[[str, str, str], None]) -> None:
        """Register a callback for state transitions."""
        self._callbacks.append(callback)

    def transition(self, event: str) -> str:
        """
        Process an event and transition to the next state.

        Args:
            event: The event to process.

        Returns:
            The new state after transition.

        Raises:
            InvalidTransitionError: If the event is not valid in the current state.
            ValueError: If the event is unknown.
        """
        if event not in ALL_EVENTS:
            raise ValueError(f"Unknown event: '{event}'. Valid events: {ALL_EVENTS}")

        key = (self._state, event)
        if key not in TRANSITIONS:
            raise InvalidTransitionError(self._state, event)

        target, description = TRANSITIONS[key]

        # Handle resume → restore pre-pause state
        if target is None:
            if self._pre_pause_state is None:
                raise InvalidTransitionError(self._state, event)
            target = self._pre_pause_state
            self._pre_pause_state = None

        old_state = self._state

        # Save state before pausing
        if event == USER_PAUSE:
            self._pre_pause_state = self._state

        self._state = target
        self._history.append((old_state, event, target))

        logger.info("FSM: %s --[%s]--> %s (%s)", old_state, event, target, description)

        for cb in self._callbacks:
            try:
                cb(old_state, event, target)
            except Exception:
                logger.exception("Callback error during transition")

        return target

    def can_transition(self, event: str) -> bool:
        """Check if an event is valid in the current state without executing it."""
        return (self._state, event) in TRANSITIONS

    def reset(self) -> None:
        """Reset FSM to initial state."""
        self._state = IDLE
        self._pre_pause_state = None
        self._history.clear()

    def is_terminal(self) -> bool:
        """Check if the FSM is in a terminal state."""
        return self._state in (COMPLETED, STOPPED, ERROR)

    def is_active(self) -> bool:
        """Check if the debate is actively running (not paused/stopped/completed)."""
        return self._state in (TOPIC_INTRO, OPENING, EXCHANGING, SUMMARIZING, LEVEL_UP, FINAL)
