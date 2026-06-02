"""Tests for debate engine initialization and configuration."""

import pytest
from engine.debate_engine import DebateEngine
from engine.models.schemas import DebateConfig, DebateSession, MODE_PRESETS


class TestDebateConfig:
    """Test configuration and mode presets."""

    def test_default_config(self):
        config = DebateConfig()
        assert config.max_rounds == 5
        assert config.max_exchanges_per_round == 10
        assert config.mode == "standard"

    def test_quick_mode_preset(self):
        config = DebateConfig(mode="quick")
        preset = MODE_PRESETS["quick"]
        assert preset["max_rounds"] == 2
        assert preset["max_exchanges_per_round"] == 5

    def test_deep_mode_preset(self):
        preset = MODE_PRESETS["deep"]
        assert preset["max_rounds"] == 8
        assert preset["max_exchanges_per_round"] == 15

    def test_mode_presets_complete(self):
        """All three modes must be defined."""
        assert set(MODE_PRESETS.keys()) == {"quick", "standard", "deep"}


class TestDebateEngine:
    """Test engine initialization."""

    def test_engine_init_default(self):
        engine = DebateEngine()
        assert engine.config is not None
        assert engine.fsm.state == "idle"

    def test_engine_init_with_mode(self):
        config = DebateConfig(mode="quick")
        engine = DebateEngine(config=config)
        assert engine.config.max_rounds == 2
        assert engine.config.max_exchanges_per_round == 5

    def test_engine_start(self):
        engine = DebateEngine()
        session = engine.start("测试话题")
        assert isinstance(session, DebateSession)
        assert session.topic == "测试话题"
        assert session.status == "running"
        assert engine.fsm.state == "topic_intro"

    def test_engine_model_routing(self):
        """Verify agents are assigned different models."""
        engine = DebateEngine()
        assert engine.agent_a.model is not None
        assert engine.agent_b.model is not None
        assert engine.agent_c.model is not None

    def test_session_has_id(self):
        session = DebateSession(topic="test")
        assert session.id is not None
        assert len(session.id) > 0
