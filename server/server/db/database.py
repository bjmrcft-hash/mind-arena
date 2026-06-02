"""SQLite database initialization and connection management."""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

from server.config import settings

logger = logging.getLogger(__name__)

# SQL schema
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS debate_sessions (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    status TEXT DEFAULT 'idle',
    current_round INTEGER DEFAULT 0,
    current_exchange INTEGER DEFAULT 0,
    config TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS debate_rounds (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES debate_sessions(id) ON DELETE CASCADE,
    round_number INTEGER NOT NULL,
    dimension TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, round_number)
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES debate_sessions(id) ON DELETE CASCADE,
    round_id TEXT NOT NULL REFERENCES debate_rounds(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('A','B','C')),
    round_number INTEGER NOT NULL,
    exchange_number INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    audio_url TEXT,
    message_type TEXT NOT NULL,
    token_count INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON debate_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON debate_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rounds_session ON debate_rounds(session_id, round_number);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_messages_round ON messages(round_id, exchange_number);
"""


async def init_db() -> None:
    """Initialize database and create tables if they don't exist."""
    db_path = Path(settings.DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript(SCHEMA_SQL)
        await db.commit()

    logger.info("Database initialized at %s", db_path)


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(settings.DB_PATH)
    db.row_factory = aiosqlite.Row
    return db
