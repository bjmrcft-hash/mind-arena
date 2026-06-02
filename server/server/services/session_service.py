"""Session service — manages debate lifecycle with engine integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from engine.debate_engine import DebateEngine, DebateEvent
from engine.models.schemas import DebateConfig, MODE_PRESETS

from server.db.database import get_db
from server.db.repository import DebateRepository

logger = logging.getLogger(__name__)

# Active debate engines keyed by session_id
_active_engines: dict[str, DebateEngine] = {}
# Event queues for WebSocket consumers
_event_queues: dict[str, list[asyncio.Queue]] = {}


async def create_debate(
    topic: str,
    mode: str = "standard",
    models: dict[str, str] | None = None,
    tts_enabled: bool = False,
) -> dict:
    """Create a new debate session."""
    config = DebateConfig(mode=mode)
    if models:
        config.models = models

    # Apply mode presets
    if mode in MODE_PRESETS:
        preset = MODE_PRESETS[mode]
        config.max_rounds = preset["max_rounds"]
        config.max_exchanges_per_round = preset["max_exchanges_per_round"]

    engine = DebateEngine(config=config, tts_enabled=tts_enabled)
    session = engine.start(topic)

    # Store engine
    _active_engines[session.id] = engine

    # Persist to DB
    db = await get_db()
    try:
        repo = DebateRepository(db)
        await repo.create_session(
            session.id, topic, config.model_dump_json()
        )
        await repo.update_session_status(session.id, "running")
    finally:
        await db.close()

    return {
        "id": session.id,
        "topic": topic,
        "status": "running",
        "config": config.model_dump(),
    }


async def run_debate(session_id: str) -> None:
    """Run a debate engine and broadcast events."""
    engine = _active_engines.get(session_id)
    if not engine:
        logger.error("No engine found for session %s", session_id)
        return

    db = await get_db()
    repo = DebateRepository(db)

    try:
        async for event in engine.run():
            # Broadcast to WebSocket consumers
            await _broadcast_event(session_id, event)

            # Persist messages (skip non-message events like health_check, model_fallback)
            if event.event_type == "message_complete" and event.content:
                round_id = engine.rounds[-1].id if engine.rounds else "pre"
                await repo.create_message(
                    message_id=f"{session_id}_{len(engine.messages)}",
                    session_id=session_id,
                    round_id=round_id,
                    role=event.role or "A",
                    round_number=event.round_number or 0,
                    exchange_number=event.exchange_number or 0,
                    content=event.content,
                    message_type=event.message_type or event.event_type,
                    audio_url=event.audio_path,
                )

            # Update progress
            if engine.session:
                await repo.update_session_progress(
                    session_id,
                    engine.session.current_round,
                    engine.session.current_exchange,
                )

        # Mark completed
        if engine.session and engine.session.status == "completed":
            await repo.complete_session(session_id)

    except Exception:
        logger.exception("Debate %s failed", session_id)
        if engine.session:
            engine.session.status = "error"
        await repo.update_session_status(session_id, "error")
        await _broadcast_event(session_id, DebateEvent(
            event_type="error", data={"error": "Internal engine error"}
        ))
    finally:
        await db.close()


def get_engine(session_id: str) -> DebateEngine | None:
    """Get active engine for a session."""
    return _active_engines.get(session_id)


async def pause_debate(session_id: str) -> bool:
    engine = _active_engines.get(session_id)
    if engine:
        engine.pause()
        db = await get_db()
        try:
            await DebateRepository(db).update_session_status(session_id, "paused")
        finally:
            await db.close()
        return True
    return False


async def resume_debate(session_id: str) -> bool:
    engine = _active_engines.get(session_id)
    if engine:
        engine.resume()
        db = await get_db()
        try:
            await DebateRepository(db).update_session_status(session_id, "running")
        finally:
            await db.close()
        return True
    return False


async def stop_debate(session_id: str) -> bool:
    engine = _active_engines.get(session_id)
    if engine:
        engine.stop()
        db = await get_db()
        try:
            await DebateRepository(db).update_session_status(session_id, "stopped")
        finally:
            await db.close()
        return True
    return False


async def skip_round(session_id: str) -> bool:
    engine = _active_engines.get(session_id)
    if engine:
        engine.skip_round()
        return True
    return False


# ── Event broadcasting ──

def subscribe_events(session_id: str) -> asyncio.Queue:
    """Subscribe to debate events. Returns a queue."""
    q: asyncio.Queue = asyncio.Queue()
    _event_queues.setdefault(session_id, []).append(q)
    return q


def unsubscribe_events(session_id: str, q: asyncio.Queue) -> None:
    """Unsubscribe from debate events."""
    queues = _event_queues.get(session_id, [])
    if q in queues:
        queues.remove(q)


async def _broadcast_event(session_id: str, event: DebateEvent) -> None:
    """Broadcast an event to all subscribers."""
    data = {
        "type": event.event_type,
        "message_type": event.message_type or event.event_type,
        "role": event.role,
        "content": event.content,
        "round_number": event.round_number,
        "exchange_number": event.exchange_number,
        "dimension": event.dimension,
        "audio_url": event.audio_path,
        "state": event.state,
        "data": event.data,
        "model": event.model,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
    }
    queues = _event_queues.get(session_id, [])
    for q in queues:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            pass
