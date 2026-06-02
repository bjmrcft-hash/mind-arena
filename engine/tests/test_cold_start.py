"""Tests for cold start detection."""

import pytest
from engine.cold_start_detector import ColdStartDetector
from engine.models.schemas import DebateConfig, Message
from datetime import datetime


def _make_msg(content: str, role: str = "B") -> Message:
    """Helper to create a message."""
    return Message(
        session_id="test",
        round_id="test-round",
        role=role,
        round_number=1,
        exchange_number=1,
        content=content,
        message_type="argument",
        timestamp=datetime.utcnow(),
    )


class TestColdStartDetector:
    """Test three-dimension cold start detection."""

    def test_no_messages(self):
        config = DebateConfig()
        detector = ColdStartDetector(config)
        assert detector.check([]) is False

    def test_too_few_messages(self):
        config = DebateConfig()
        detector = ColdStartDetector(config)
        msgs = [_make_msg("短消息")]
        assert detector.check(msgs) is False

    def test_length_drop_detection(self):
        """Consecutive short messages should trigger after enough exchanges."""
        config = DebateConfig(
            message_min_length=50,
            cold_start_threshold=2,
        )
        detector = ColdStartDetector(config)

        # Need at least 4 B/C messages before cold start detection activates
        msgs = [
            _make_msg("短", role="B"),  # Below threshold
            _make_msg("也短", role="C"),  # Below threshold
            _make_msg("还是短", role="B"),  # Below threshold
            _make_msg("依然短", role="C"),  # Below threshold (4 B/C msgs, consecutive)
        ]
        assert detector.check(msgs) is True

    def test_length_recovery(self):
        """A long message should reset the counter."""
        config = DebateConfig(
            message_min_length=20,
            cold_start_threshold=2,
        )
        detector = ColdStartDetector(config)

        msgs = [
            _make_msg("短"),  # Below
            _make_msg("这是一个足够长的消息，超过了最小长度阈值。" * 2),  # Above
            _make_msg("又短了"),  # Below, but counter reset
        ]
        assert detector.check(msgs) is False

    def test_semantic_repetition(self):
        """Similar recent messages should trigger."""
        config = DebateConfig(
            similarity_threshold=0.5,
            message_min_length=5,  # Low to avoid length trigger
        )
        detector = ColdStartDetector(config)

        msgs = [
            _make_msg("人工智能将取代所有程序员工作这是必然趋势"),
            _make_msg("AI技术发展使得编程自动化成为不可逆转的方向"),
            _make_msg("人工智能将取代所有程序员工作这是必然趋势"),
            _make_msg("AI技术发展使得编程自动化成为不可逆转的方向"),
        ]
        # The last two are very similar to the previous two
        assert detector.check(msgs) is True

    def test_keyword_repetition(self):
        """High keyword repetition should trigger."""
        config = DebateConfig(
            message_min_length=5,  # Low to avoid length trigger
        )
        detector = ColdStartDetector(config)

        # 6 messages all using the same keywords
        msgs = [
            _make_msg("人工智能编程自动化取代工作趋势发展"),
            _make_msg("人工智能编程自动化取代工作趋势发展"),
            _make_msg("人工智能编程自动化取代工作趋势发展"),
            _make_msg("人工智能编程自动化取代工作趋势发展"),
            _make_msg("人工智能编程自动化取代工作趋势发展"),
            _make_msg("人工智能编程自动化取代工作趋势发展"),
        ]
        assert detector.check(msgs) is True

    def test_healthy_debate_no_trigger(self):
        """Normal debate with diverse content should not trigger."""
        config = DebateConfig(
            message_min_length=20,
            similarity_threshold=0.85,
        )
        detector = ColdStartDetector(config)

        msgs = [
            _make_msg("我认为人工智能的发展将从根本上改变软件开发的方式，从需求分析到测试部署全流程自动化"),
            _make_msg("然而B的论证忽视了一个关键因素：创造性问题解决能力是AI目前无法复制的人类特质"),
            _make_msg("从经济角度来看，自动化替代人工的成本效益分析需要考虑边际成本递减的规律"),
            _make_msg("C混淆了当前技术限制和根本性不可能之间的区别，历史上多次被认为不可能的技术最终都实现了"),
            _make_msg("B的论证犯了类比谬误，AI与之前的技术革命存在本质差异，因为AI直接替代的是认知劳动"),
            _make_msg("从社会层面来看，大规模技术性失业将带来严重的社会不稳定，这是纯技术分析忽视的维度"),
        ]
        assert detector.check(msgs) is False

    def test_reset(self):
        """Test reset clears internal counters."""
        config = DebateConfig(message_min_length=50, cold_start_threshold=2)
        detector = ColdStartDetector(config)

        msgs = [_make_msg("短"), _make_msg("也短")]
        detector.check(msgs)  # Consecutive low = 2

        detector.reset()
        assert detector._consecutive_low == 0
