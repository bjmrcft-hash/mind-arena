"""Data access layer for debate sessions, rounds, and messages."""

from __future__ import annotations

import json
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)


class DebateRepository:
    """Repository for debate data access."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    # ── Sessions ──

    async def create_session(
        self, session_id: str, topic: str, config_json: str
    ) -> None:
        await self.db.execute(
            "INSERT INTO debate_sessions (id, topic, config, status) VALUES (?, ?, ?, 'idle')",
            (session_id, topic, config_json),
        )
        await self.db.commit()

    async def update_session_status(
        self, session_id: str, status: str
    ) -> None:
        await self.db.execute(
            "UPDATE debate_sessions SET status = ? WHERE id = ?",
            (status, session_id),
        )
        await self.db.commit()

    async def update_session_progress(
        self, session_id: str, current_round: int, current_exchange: int
    ) -> None:
        await self.db.execute(
            "UPDATE debate_sessions SET current_round = ?, current_exchange = ? WHERE id = ?",
            (current_round, current_exchange, session_id),
        )
        await self.db.commit()

    async def complete_session(self, session_id: str) -> None:
        await self.db.execute(
            "UPDATE debate_sessions SET status = 'completed', completed_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), session_id),
        )
        await self.db.commit()

    async def get_session(self, session_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM debate_sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def list_sessions(
        self, limit: int = 20, offset: int = 0
    ) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM debate_sessions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Rounds ──

    async def create_round(
        self, round_id: str, session_id: str, round_number: int, dimension: str | None
    ) -> None:
        await self.db.execute(
            "INSERT INTO debate_rounds (id, session_id, round_number, dimension) VALUES (?, ?, ?, ?)",
            (round_id, session_id, round_number, dimension),
        )
        await self.db.commit()

    async def get_rounds(self, session_id: str) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM debate_rounds WHERE session_id = ? ORDER BY round_number",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Messages ──

    async def create_message(
        self,
        message_id: str,
        session_id: str,
        round_id: str,
        role: str,
        round_number: int,
        exchange_number: int,
        content: str,
        message_type: str,
        audio_url: str | None = None,
        token_count: int | None = None,
    ) -> None:
        await self.db.execute(
            """INSERT INTO messages
            (id, session_id, round_id, role, round_number, exchange_number,
             content, audio_url, message_type, token_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                message_id, session_id, round_id, role,
                round_number, exchange_number, content,
                audio_url, message_type, token_count,
            ),
        )
        await self.db.commit()

    async def get_messages(
        self, session_id: str, limit: int = 200
    ) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp LIMIT ?",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_messages_by_round(
        self, session_id: str, round_number: int
    ) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM messages WHERE session_id = ? AND round_number = ? ORDER BY timestamp",
            (session_id, round_number),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
