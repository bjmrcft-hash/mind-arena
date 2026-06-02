"""
Debate engine — orchestrates the full debate lifecycle.

Ties together: FSM, agents, round controller, context manager,
cold start detector, deviation detector, LLM service, TTS service.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

from engine.agents.moderator_a import ModeratorA
from engine.agents.debater_b import DebaterB
from engine.agents.debater_c import DebaterC
from engine.cold_start_detector import ColdStartDetector
from engine.context_manager import ContextManager
from engine.deviation_detector import DeviationDetector
from engine.llm.llm_service import LLMService
from engine.llm.model_router import ModelRouter
from engine.model_health import check_all_models, check_model_health, get_fallback_model, HealthCheckResult

# Provider configs: name → (base_url, env_key_name)
PROVIDER_CONFIGS: dict[str, tuple[str, str]] = {
    "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "LLM_API_KEY"),
    "nvidia": ("https://integrate.api.nvidia.com/v1", "NVIDIA_API_KEY"),
    "modelscope": ("https://api-inference.modelscope.cn/v1", "MODELSCOPE_API_KEY"),
    "moonshot": ("https://api.moonshot.cn/v1", "MOONSHOT_API_KEY"),
    "xiaomi": ("https://token-plan-cn.xiaomimimo.com/v1", "XIAOMI_CODING_API_KEY"),
}

# Model → provider mapping
MODEL_PROVIDER_MAP: dict[str, str] = {
    "qwen-turbo": "qwen",
    "qwen-plus": "qwen",
    "qwen3.5-plus-2026-04-20": "qwen",
    "deepseek-ai/deepseek-v4-flash": "nvidia",
    "deepseek-ai/deepseek-v4-pro": "nvidia",
    "kimi-k2.6": "moonshot",
    "moonshotai/kimi-k2.6": "moonshot",
    "ZhipuAI/GLM-5": "modelscope",
    "MiniMax/MiniMax-M1-80k": "modelscope",
    "mimo-v2.5-pro": "xiaomi",
    "mimo-v2.5": "xiaomi",
}
from engine.models.schemas import (
    DebateConfig, DebateRound, DebateSession, Message,
    MODE_PRESETS,
)
from engine.round_controller import RoundController
from engine.state_machine import (
    DebateStateMachine, A_DONE, A_SUMMARIZED, A_VERDICT,
    BC_OPENED, COLD_START, COMPLETED, ERROR_EVENT,
    EXCHANGE_LIMIT, ROUND_EXHAUST, ROUND_REMAIN, START,
    USER_PAUSE, USER_RESUME, USER_SKIP, USER_STOP,
)
from engine.tts.tts_service import TTSService

logger = logging.getLogger(__name__)


class DebateEvent:
    """Event emitted during debate for UI consumption."""

    def __init__(
        self,
        event_type: str,
        role: str | None = None,
        content: str | None = None,
        round_number: int | None = None,
        exchange_number: int | None = None,
        dimension: str | None = None,
        audio_path: str | None = None,
        state: str | None = None,
        data: dict | None = None,
        message_type: str | None = None,
        model: str | None = None,
    ) -> None:
        self.event_type = event_type
        self.role = role
        self.content = content
        self.round_number = round_number
        self.exchange_number = exchange_number
        self.dimension = dimension
        self.audio_path = audio_path
        self.state = state
        self.data = data or {}
        self.message_type = message_type or event_type
        self.model = model
        self.timestamp = datetime.utcnow()


class DebateEngine:
    """
    Main debate engine.

    Usage:
        config = DebateConfig(mode="quick")
        engine = DebateEngine(config)
        engine.start("AI会取代程序员吗？")
        async for event in engine.run():
            print(f"[{event.event_type}] {event.role}: {event.content[:50]}...")
    """

    def __init__(
        self,
        config: DebateConfig | None = None,
        llm_service: LLMService | None = None,
        tts_dir: str | Path = "./audio",
        tts_enabled: bool = True,
    ) -> None:
        # Apply mode presets
        if config and config.mode in MODE_PRESETS:
            preset = MODE_PRESETS[config.mode]
            config.max_rounds = preset["max_rounds"]
            config.max_exchanges_per_round = preset["max_exchanges_per_round"]

        self.config = config or DebateConfig()

        # Services
        self.llm = llm_service or LLMService()

        # Register all available providers
        # 1. From env vars
        for name, (base_url, env_key) in PROVIDER_CONFIGS.items():
            api_key = os.environ.get(env_key, "")
            if api_key:
                self.llm.register_provider(name, base_url, api_key)
                logger.info("Registered provider: %s (env)", name)

        # 2. From OpenClaw auth-profiles.json (fallback if env not set)
        self._load_openclaw_auth()

        self.tts = TTSService(audio_dir=tts_dir, enabled=tts_enabled)

        # Model routing
        router = ModelRouter(self.config.models)
        assignments = router.resolve()

        # Agents
        a = assignments["A"]
        b = assignments["B"]
        c = assignments["C"]
        self.agent_a = ModeratorA(self.llm, a.model, a.temperature)
        self.agent_b = DebaterB(self.llm, b.model, b.temperature)
        self.agent_c = DebaterC(self.llm, c.model, c.temperature)

        # Sub-systems
        self.fsm = DebateStateMachine()
        self.round_ctrl = RoundController(self.config)
        self.context_mgr = ContextManager(self.config)
        self.cold_detector = ColdStartDetector(self.config)
        self.deviation_detector = DeviationDetector()

        # State
        self.session: DebateSession | None = None
        self._rounds: list[DebateRound] = []
        self._messages: list[Message] = []
        self._current_round_messages: list[Message] = []
        self._stall_count: int = 0
        self._model_health: HealthCheckResult | None = None
        self._active_models: dict[str, str] = {}  # role → model_id (may differ from config if fallback)

    def _load_openclaw_auth(self) -> None:
        """Load API keys from OpenClaw auth-profiles.json for providers missing from env."""
        import json
        auth_path = Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"
        if not auth_path.exists():
            return
        try:
            with open(auth_path, encoding="utf-8") as f:
                auth = json.load(f)
            profiles = auth.get("profiles", {})
            # Map provider name → auth profile id
            PROVIDER_AUTH_MAP = {
                "qwen": "qwen:default",
                "nvidia": "nvidia:default",
                "modelscope": "qwen:default",  # modelscope shares qwen key in some setups
                "moonshot": "moonshot:default",
                "xiaomi": "xiaomi:default",
            }
            for provider, profile_id in PROVIDER_AUTH_MAP.items():
                if provider in self.llm._providers:
                    continue  # already registered from env
                profile = profiles.get(profile_id, {})
                key = profile.get("key", "") or profile.get("apiKey", "")
                if key and provider in PROVIDER_CONFIGS:
                    base_url = PROVIDER_CONFIGS[provider][0]
                    self.llm.register_provider(provider, base_url, key)
                    logger.info("Registered provider: %s (auth-profiles)", provider)
        except Exception as e:
            logger.warning("Failed to load OpenClaw auth: %s", e)

    async def preflight_check(self) -> HealthCheckResult:
        """Check all models before debate starts. Returns health check result."""
        model_ids = {
            "A": self.agent_a.model,
            "B": self.agent_b.model,
            "C": self.agent_c.model,
        }

        # Check each model with its provider's client
        from engine.model_health import ModelStatus
        result = HealthCheckResult()

        for role, model_id in model_ids.items():
            provider = MODEL_PROVIDER_MAP.get(model_id, "qwen")
            client = self.llm._get_client(provider)
            # Create a temporary LLMService with the provider's client
            tmp_llm = LLMService()
            tmp_llm._default_client = client
            status = await check_model_health(tmp_llm, model_id, timeout=60)
            result.models[role] = status
            if not status.available:
                result.all_ok = False

        # Apply fallback for failed models
        for role, status in result.models.items():
            if status.available:
                self._active_models[role] = status.model_id
            else:
                # Find fallback
                fallback = get_fallback_model(
                    status.model_id,
                    {r: s.model_id for r, s in result.models.items() if s.available},
                )
                if fallback:
                    logger.warning("Model %s unavailable, falling back to %s", status.model_id, fallback)
                    self._active_models[role] = fallback
                    if role == "A":
                        self.agent_a.model = fallback
                    elif role == "B":
                        self.agent_b.model = fallback
                    elif role == "C":
                        self.agent_c.model = fallback
                else:
                    logger.error("No fallback available for model %s", status.model_id)
                    self._active_models[role] = status.model_id

        # Bind model→provider so LLMService auto-resolves the right client
        for role, model_id in self._active_models.items():
            provider = MODEL_PROVIDER_MAP.get(model_id, "modelscope")
            if provider in self.llm._providers:
                self.llm.set_model_provider(model_id, provider)
                logger.info("Bound %s → %s (role %s)", model_id, provider, role)

        self._model_health = result
        return result

    def _handle_model_failure(self, role: str, failed_model: str) -> str:
        """Handle a model failure during debate. Returns new model to use."""
        other_models = {r: m for r, m in self._active_models.items() if r != role}
        fallback = get_fallback_model(failed_model, other_models)
        if fallback:
            logger.warning("Runtime model failure for %s (%s), switching to %s", role, failed_model, fallback)
            self._active_models[role] = fallback
            if role == "A":
                self.agent_a.model = fallback
            elif role == "B":
                self.agent_b.model = fallback
            elif role == "C":
                self.agent_c.model = fallback
            return fallback
        logger.error("No fallback available for %s (%s)", role, failed_model)
        return failed_model

    async def _call_with_fallback(self, role: str, coro_factory) -> tuple[str, int]:
        """Call an LLM method with automatic fallback on failure.

        Args:
            role: "A", "B", or "C"
            coro_factory: callable that returns a coroutine (e.g. lambda: agent.generate_response(...))
        """
        try:
            return await coro_factory()
        except Exception as e:
            logger.warning("LLM call failed for role %s: %s", role, e)
            model = self._active_models.get(role, "unknown")
            new_model = self._handle_model_failure(role, model)
            if new_model != model:
                # Update agent's provider reference
                provider = MODEL_PROVIDER_MAP.get(new_model)
                if role == "A":
                    self.agent_a.model = new_model
                elif role == "B":
                    self.agent_b.model = new_model
                elif role == "C":
                    self.agent_c.model = new_model
                logger.info("Retrying role %s with fallback model %s (provider=%s)", role, new_model, provider)
                return await coro_factory()
            raise

    def start(self, topic: str) -> DebateSession:
        """
        Initialize a new debate session.

        Args:
            topic: The debate topic.

        Returns:
            The created DebateSession.
        """
        self.session = DebateSession(topic=topic, config=self.config)
        self.fsm.transition(START)
        self.session.status = "running"
        return self.session

    async def run(self) -> AsyncGenerator[DebateEvent, None]:
        """
        Run the full debate, yielding events for each step.

        This is the main generator that drives the debate lifecycle.
        """
        if not self.session:
            raise RuntimeError("Call start(topic) before run()")

        topic = self.session.topic
        config = self.config

        try:
            # ── Phase 0: Model Health Check ──
            yield DebateEvent(event_type="state_change", state="health_check")
            health = await self.preflight_check()
            for role, status in health.models.items():
                if not status.available:
                    yield DebateEvent(
                        event_type="model_fallback",
                        data={
                            "role": role,
                            "original": status.model_id,
                            "fallback": self._active_models.get(role, status.model_id),
                            "error": status.error,
                        },
                    )

            # ── Phase 1: Topic Introduction (A) ──
            yield DebateEvent(event_type="state_change", state="topic_intro")

            intro_content, intro_tokens = await self._call_with_fallback(
                "A", lambda: self.agent_a.generate_topic_intro(topic, config)
            )
            intro_msg = self._add_message("A", intro_content, "topic_intro", 0, 0)

            yield DebateEvent(
                event_type="message_complete", role="A", content=intro_content,
                round_number=0, audio_path=await self._tts(intro_content, "A"),
                message_type="topic_intro", model=self._active_models.get("A"),
            )

            self.fsm.transition(A_DONE)

            # ── Phase 2: Opening statements (B, C) ──
            yield DebateEvent(event_type="state_change", state="opening")

            # B opening
            b_ctx = self.context_mgr.build_context(
                "B", "", topic, 0, 0, None, [], agent_stance="正方"
            )
            b_opening, b_tokens = await self._call_with_fallback(
                "B", lambda: self.agent_b.generate_response(b_ctx, config)
            )
            self._add_message("B", b_opening, "opening", 0, 0)
            yield DebateEvent(
                event_type="message_complete", role="B", content=b_opening,
                round_number=0, audio_path=await self._tts(b_opening, "B"),
                message_type="opening", model=self._active_models.get("B"),
            )

            # C opening
            c_ctx = self.context_mgr.build_context(
                "C", "", topic, 0, 0, None,
                self._current_round_messages, agent_stance="反方"
            )
            c_opening, c_tokens = await self._call_with_fallback(
                "C", lambda: self.agent_c.generate_response(c_ctx, config)
            )
            self._add_message("C", c_opening, "opening", 0, 0)
            yield DebateEvent(
                event_type="message_complete", role="C", content=c_opening,
                round_number=0, audio_path=await self._tts(c_opening, "C"),
                message_type="opening", model=self._active_models.get("C"),
            )

            self.fsm.transition(BC_OPENED)

            # ── Phase 3: Debate rounds ──
            while self.round_ctrl.has_more_rounds():
                rnd = self.round_ctrl.start_round()
                self._current_round_messages = []
                self.cold_detector.reset()

                # A: Level up (set dimension)
                yield DebateEvent(
                    event_type="round_change", round_number=rnd,
                    state="level_up",
                )

                dimension_content, _ = await self._call_with_fallback(
                    "A", lambda: self.agent_a.generate_level_up(topic, rnd, config)
                )
                dimension = self._extract_dimension(dimension_content)
                self._add_message("A", dimension_content, "level_up", rnd, 0)

                yield DebateEvent(
                    event_type="message_complete", role="A", content=dimension_content,
                    round_number=rnd, dimension=dimension,
                    audio_path=await self._tts(dimension_content, "A"),
                    message_type="level_up", model=self._active_models.get("A"),
                )

                # Create round record
                debate_round = DebateRound(
                    session_id=self.session.id,
                    round_number=rnd,
                    dimension=dimension,
                )
                self._rounds.append(debate_round)

                # B/C exchanges
                last_b_content = ""
                last_c_content = ""

                for exchange in range(1, config.max_exchanges_per_round + 1):
                    self.round_ctrl.record_exchange()

                    # B speaks
                    b_ctx = self.context_mgr.build_context(
                        "B", "", topic, rnd, exchange, dimension,
                        self._current_round_messages, agent_stance="正方"
                    )
                    b_content, _ = await self._call_with_fallback(
                        "B", lambda: self.agent_b.generate_response(b_ctx, config)
                    )
                    self._add_message("B", b_content, "argument", rnd, exchange)
                    last_b_content = b_content

                    yield DebateEvent(
                        event_type="message_complete", role="B", content=b_content,
                        round_number=rnd, exchange_number=exchange,
                        audio_path=await self._tts(b_content, "B"),
                        message_type="argument", model=self._active_models.get("B"),
                    )

                    # C responds
                    c_ctx = self.context_mgr.build_context(
                        "C", "", topic, rnd, exchange, dimension,
                        self._current_round_messages, agent_stance="反方"
                    )
                    c_content, _ = await self._call_with_fallback(
                        "C", lambda: self.agent_c.generate_response(c_ctx, config)
                    )
                    self._add_message("C", c_content, "rebuttal", rnd, exchange)
                    last_c_content = c_content

                    yield DebateEvent(
                        event_type="message_complete", role="C", content=c_content,
                        round_number=rnd, exchange_number=exchange,
                        audio_path=await self._tts(c_content, "C"),
                        message_type="rebuttal", model=self._active_models.get("C"),
                    )

                    yield DebateEvent(
                        event_type="exchange_update",
                        round_number=rnd, exchange_number=exchange,
                    )

                    # Hard stop: exchange limit reached
                    if self.round_ctrl.should_end_round():
                        break

                    # Soft intervention: moderator judges whether to continue
                    if self.cold_detector.check(self._current_round_messages):
                        logger.info("Cold start detected at round %d exchange %d", rnd, exchange)
                        self._stall_count += 1
                        break

                    if self.deviation_detector.check(topic, self._current_round_messages):
                        logger.info("Topic deviation detected at round %d exchange %d", rnd, exchange)
                        break

                # A: Summarize round
                # First transition from EXCHANGING to SUMMARIZING
                self.fsm.transition(EXCHANGE_LIMIT)

                round_text = self._format_round_messages(rnd)
                summary_content, _ = await self._call_with_fallback(
                    "A", lambda: self.agent_a.generate_summary(topic, rnd, round_text, config)
                )
                self.context_mgr.add_round_summary(rnd, summary_content)
                self._add_message("A", summary_content, "summary", rnd, 0)

                yield DebateEvent(
                    event_type="message_complete", role="A", content=summary_content,
                    round_number=rnd,
                    audio_path=await self._tts(summary_content, "A"),
                    message_type="summary", model=self._active_models.get("A"),
                )

                self.fsm.transition(A_SUMMARIZED)

                # Check if more rounds
                if self.round_ctrl.has_more_rounds():
                    self.fsm.transition(ROUND_REMAIN)
                else:
                    self.fsm.transition(ROUND_EXHAUST)

            # ── Phase 4: Final verdict (A) ──
            yield DebateEvent(event_type="state_change", state="final")

            all_summaries = self._format_all_summaries()
            verdict_content, _ = await self._call_with_fallback(
                "A", lambda: self.agent_a.generate_verdict(topic, all_summaries, config)
            )
            self._add_message("A", verdict_content, "verdict", self.round_ctrl.current_round, 0)

            yield DebateEvent(
                event_type="message_complete", role="A", content=verdict_content,
                round_number=self.round_ctrl.current_round,
                audio_path=await self._tts(verdict_content, "A"),
                message_type="verdict", model=self._active_models.get("A"),
            )

            self.fsm.transition(A_VERDICT)

            # ── Done ──
            self.session.status = "completed"
            self.session.completed_at = datetime.utcnow()
            yield DebateEvent(event_type="debate_completed")

        except Exception as e:
            logger.exception("Debate error")
            self.fsm.transition(ERROR_EVENT)
            if self.session:
                self.session.status = "error"
            yield DebateEvent(event_type="error", data={"error": str(e)})

    def pause(self) -> None:
        """Pause the debate."""
        self.fsm.transition(USER_PAUSE)
        if self.session:
            self.session.status = "paused"

    def resume(self) -> None:
        """Resume the debate."""
        self.fsm.transition(USER_RESUME)
        if self.session:
            self.session.status = "running"

    def stop(self) -> None:
        """Stop the debate."""
        self.fsm.transition(USER_STOP)
        if self.session:
            self.session.status = "stopped"

    def skip_round(self) -> None:
        """Signal to skip current round."""
        self.fsm.transition(USER_SKIP)

    # ── Internal helpers ──

    def _add_message(
        self, role: str, content: str, msg_type: str,
        round_number: int, exchange: int,
    ) -> Message:
        """Add a message to the debate record."""
        round_id = self._rounds[-1].id if self._rounds else "pre-round"
        model = self._active_models.get(role)
        msg = Message(
            session_id=self.session.id if self.session else "",
            round_id=round_id,
            role=role,
            round_number=round_number,
            exchange_number=exchange,
            content=content,
            message_type=msg_type,
            model=model,
        )
        self._messages.append(msg)
        self._current_round_messages.append(msg)
        return msg

    async def _tts(self, text: str, role: str) -> str | None:
        """Generate TTS audio for a message."""
        try:
            return await self.tts.synthesize(text, role)
        except Exception:
            logger.warning("TTS failed for role %s", role, exc_info=True)
            return None

    def _format_round_messages(self, round_number: int) -> str:
        """Format current round messages for A's summary."""
        lines = []
        for msg in self._current_round_messages:
            if msg.round_number == round_number and msg.role != "A":
                label = "正方B" if msg.role == "B" else "反方C"
                lines.append(f"[{label}] {msg.content}")
        return "\n\n".join(lines)

    def _format_all_summaries(self) -> str:
        """Format all round summaries for final verdict."""
        return "\n\n".join(
            f"第 {r.round_number} 轮（{r.dimension}）：{self.context_mgr._round_summaries.get(r.round_number, '无')}"
            for r in self._rounds
        )

    @staticmethod
    def _extract_dimension(content: str) -> str | None:
        """Try to extract dimension name from A's level-up content."""
        # Look for patterns like "维度：XXX" or "从XXX角度"
        import re
        patterns = [
            r'维度[：:]\s*(.{2,20})',
            r'从(.{2,15})角度',
            r'从(.{2,15})层面',
            r'转向(.{2,15})',
        ]
        for p in patterns:
            m = re.search(p, content)
            if m:
                return m.group(1).strip()
        # Fallback: first sentence, truncated
        first_line = content.split("\n")[0][:30]
        return first_line if first_line else None

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    @property
    def rounds(self) -> list[DebateRound]:
        return list(self._rounds)
