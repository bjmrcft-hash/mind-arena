"""WebSocket handler for real-time debate streaming."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from server.services import session_service

logger = logging.getLogger(__name__)

ws_router = APIRouter()


@ws_router.websocket("/ws/debate/{session_id}")
async def debate_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time debate events.

    Client connects to receive live debate updates.
    Client can send control messages: pause, resume, skip_round, stop.
    """
    await websocket.accept()

    # Check session exists
    engine = session_service.get_engine(session_id)
    if not engine:
        await websocket.send_json({
            "type": "error",
            "data": {"error": f"Debate session {session_id} not found"},
        })
        await websocket.close()
        return

    # Subscribe to events
    event_queue = session_service.subscribe_events(session_id)

    try:
        # Send initial state
        if engine.session:
            await websocket.send_json({
                "type": "state_change",
                "state": engine.session.status,
                "data": {
                    "topic": engine.session.topic,
                    "current_round": engine.session.current_round,
                    "config": engine.session.config.model_dump(),
                },
            })

        # Run event listener and message handler concurrently
        await asyncio.gather(
            _event_sender(websocket, event_queue),
            _message_handler(websocket, session_id),
        )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception:
        logger.exception("WebSocket error for session %s", session_id)
    finally:
        session_service.unsubscribe_events(session_id, event_queue)


async def _event_sender(websocket: WebSocket, queue: asyncio.Queue) -> None:
    """Send events from queue to WebSocket client."""
    while True:
        event = await queue.get()
        try:
            await websocket.send_json(event)
        except Exception:
            break


async def _message_handler(websocket: WebSocket, session_id: str) -> None:
    """Handle control messages from WebSocket client."""
    while True:
        try:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "pause":
                await session_service.pause_debate(session_id)
                await websocket.send_json({"type": "state_change", "state": "paused"})

            elif msg_type == "resume":
                await session_service.resume_debate(session_id)
                await websocket.send_json({"type": "state_change", "state": "running"})

            elif msg_type == "skip_round":
                await session_service.skip_round(session_id)
                await websocket.send_json({"type": "state_change", "state": "skipping"})

            elif msg_type == "stop":
                await session_service.stop_debate(session_id)
                await websocket.send_json({"type": "state_change", "state": "stopped"})

            else:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": f"Unknown message type: {msg_type}"},
                })

        except WebSocketDisconnect:
            break
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "error",
                "data": {"error": "Invalid JSON"},
            })
