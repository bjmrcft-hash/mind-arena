"""Tests for the debate state machine."""

import pytest
from engine.state_machine import (
    DebateStateMachine, InvalidTransitionError,
    IDLE, TOPIC_INTRO, OPENING, EXCHANGING, SUMMARIZING,
    LEVEL_UP, FINAL, COMPLETED, PAUSED, STOPPED, ERROR,
    START, A_DONE, BC_OPENED, EXCHANGE_LIMIT, COLD_START,
    USER_SKIP, A_SUMMARIZED, ROUND_REMAIN, ROUND_EXHAUST,
    A_VERDICT, USER_PAUSE, USER_RESUME, USER_STOP, ERROR_EVENT,
)


class TestStateMachine:
    """Test all valid and invalid transitions."""

    def test_initial_state(self):
        fsm = DebateStateMachine()
        assert fsm.state == IDLE

    def test_full_happy_path(self):
        """Test the complete happy path: IDLE → ... → COMPLETED."""
        fsm = DebateStateMachine()

        assert fsm.transition(START) == TOPIC_INTRO
        assert fsm.transition(A_DONE) == OPENING
        assert fsm.transition(BC_OPENED) == EXCHANGING
        assert fsm.transition(EXCHANGE_LIMIT) == SUMMARIZING
        assert fsm.transition(A_SUMMARIZED) == LEVEL_UP
        assert fsm.transition(ROUND_EXHAUST) == FINAL
        assert fsm.transition(A_VERDICT) == COMPLETED

        assert fsm.is_terminal()
        assert not fsm.is_active()

    def test_cold_start_trigger(self):
        """Test cold start triggers transition to SUMMARIZING."""
        fsm = DebateStateMachine()
        fsm.transition(START)
        fsm.transition(A_DONE)
        fsm.transition(BC_OPENED)

        assert fsm.transition(COLD_START) == SUMMARIZING

    def test_user_skip(self):
        """Test user can skip current round."""
        fsm = DebateStateMachine()
        fsm.transition(START)
        fsm.transition(A_DONE)
        fsm.transition(BC_OPENED)

        assert fsm.transition(USER_SKIP) == SUMMARIZING

    def test_pause_resume_cycle(self):
        """Test pause from various states and resume."""
        for state_event_pairs in [
            [(START, TOPIC_INTRO)],
            [(START, TOPIC_INTRO), (A_DONE, OPENING)],
            [(START, TOPIC_INTRO), (A_DONE, OPENING), (BC_OPENED, EXCHANGING)],
        ]:
            fsm = DebateStateMachine()
            last_state = IDLE
            for event, expected in state_event_pairs:
                last_state = fsm.transition(event)
                assert fsm.state == expected

            # Pause
            assert fsm.transition(USER_PAUSE) == PAUSED
            assert fsm.state == PAUSED

            # Resume should go back
            assert fsm.transition(USER_RESUME) == last_state
            assert fsm.state == last_state

    def test_stop_from_active_states(self):
        """Test stop works from all active states."""
        active_states_events = [
            (START, TOPIC_INTRO),
            (A_DONE, OPENING),
            (BC_OPENED, EXCHANGING),
        ]

        for stop_after_events, stop_from_state in [
            ([], IDLE),
            ([(START, TOPIC_INTRO)], TOPIC_INTRO),
            ([(START, TOPIC_INTRO), (A_DONE, OPENING)], OPENING),
            ([(START, TOPIC_INTRO), (A_DONE, OPENING), (BC_OPENED, EXCHANGING)], EXCHANGING),
        ]:
            fsm = DebateStateMachine()
            for event, _ in stop_after_events:
                fsm.transition(event)

            assert fsm.transition(USER_STOP) == STOPPED
            assert fsm.is_terminal()

    def test_stop_from_paused(self):
        """Test stop from paused state."""
        fsm = DebateStateMachine()
        fsm.transition(START)
        fsm.transition(USER_PAUSE)
        assert fsm.state == PAUSED

        assert fsm.transition(USER_STOP) == STOPPED
        assert fsm.is_terminal()

    def test_error_from_active_states(self):
        """Test error can be raised from any active state."""
        fsm = DebateStateMachine()
        fsm.transition(START)
        assert fsm.transition(ERROR_EVENT) == ERROR
        assert fsm.is_terminal()

    def test_invalid_transition_raises(self):
        """Test that invalid transitions raise errors."""
        fsm = DebateStateMachine()

        # Can't do A_DONE in IDLE
        with pytest.raises(InvalidTransitionError):
            fsm.transition(A_DONE)

        # Can't do BC_OPENED in IDLE
        with pytest.raises(InvalidTransitionError):
            fsm.transition(BC_OPENED)

    def test_cannot_transition_after_terminal(self):
        """Test that no transitions work from terminal states."""
        for terminal_event in [USER_STOP, ERROR_EVENT]:
            fsm = DebateStateMachine()
            fsm.transition(START)
            if terminal_event == USER_STOP:
                fsm.transition(USER_STOP)
            else:
                fsm.transition(ERROR_EVENT)

            assert fsm.is_terminal()
            with pytest.raises(InvalidTransitionError):
                fsm.transition(START)

    def test_can_transition_check(self):
        """Test can_transition without executing."""
        fsm = DebateStateMachine()
        assert fsm.can_transition(START) is True
        assert fsm.can_transition(A_DONE) is False

    def test_transition_history(self):
        """Test that transition history is recorded."""
        fsm = DebateStateMachine()
        fsm.transition(START)
        fsm.transition(A_DONE)

        history = fsm.history
        assert len(history) == 2
        assert history[0] == (IDLE, START, TOPIC_INTRO)
        assert history[1] == (TOPIC_INTRO, A_DONE, OPENING)

    def test_reset(self):
        """Test reset clears state and history."""
        fsm = DebateStateMachine()
        fsm.transition(START)
        fsm.transition(A_DONE)

        fsm.reset()
        assert fsm.state == IDLE
        assert fsm.history == []

    def test_callback_called(self):
        """Test transition callbacks are invoked."""
        fsm = DebateStateMachine()
        calls = []
        fsm.on_transition(lambda old, evt, new: calls.append((old, evt, new)))

        fsm.transition(START)
        assert len(calls) == 1
        assert calls[0] == (IDLE, START, TOPIC_INTRO)

    def test_unknown_event_raises(self):
        """Test that unknown events raise ValueError."""
        fsm = DebateStateMachine()
        with pytest.raises(ValueError, match="Unknown event"):
            fsm.transition("totally_invalid_event")
