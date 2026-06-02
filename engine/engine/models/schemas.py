"""Pydantic data models for MindArena debate system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class DebateConfig(BaseModel):
    """辩论配置"""
    max_rounds: int = 5
    max_exchanges_per_round: int = 10
    cold_start_threshold: int = 2
    message_min_length: int = 50
    message_max_length: int = 1500
    similarity_threshold: float = 0.85
    auto_play_audio: bool = True
    streaming_output: bool = True
    mode: Literal["quick", "standard", "deep"] = "standard"
    models: dict[str, str] = Field(default_factory=lambda: {
        "A": "deepseek-r1",
        "B": "kimi-k2",
        "C": "qwen3.5-plus",
    })


# Mode presets
MODE_PRESETS: dict[str, dict] = {
    "quick":    {"max_rounds": 2, "max_exchanges_per_round": 5},
    "standard": {"max_rounds": 5, "max_exchanges_per_round": 10},
    "deep":     {"max_rounds": 8, "max_exchanges_per_round": 15},
}


class DebateSession(BaseModel):
    """辩论会话"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    status: Literal[
        "idle", "running", "paused", "completed", "stopped", "error"
    ] = "idle"
    current_round: int = 0
    current_exchange: int = 0
    config: DebateConfig = Field(default_factory=DebateConfig)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class DebateRound(BaseModel):
    """辩论轮次"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    round_number: int
    dimension: str | None = None
    status: Literal["active", "completed"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)


MessageType = Literal[
    "topic_intro", "opening", "argument", "rebuttal",
    "summary", "level_up", "verdict",
]


class Message(BaseModel):
    """单条辩论消息"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    round_id: str
    role: Literal["A", "B", "C"]
    round_number: int
    exchange_number: int = 0
    content: str
    audio_url: str | None = None
    message_type: MessageType
    model: str | None = None  # 实际使用的模型
    token_count: int | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# --- WebSocket protocol models ---

class ServerMessage(BaseModel):
    """服务端 → 客户端 WS 消息"""
    type: Literal[
        "session_created", "state_change", "message_start",
        "message_chunk", "message_complete", "message_audio",
        "round_change", "exchange_update", "debate_completed", "error",
    ]
    data: dict = Field(default_factory=dict)


class ClientMessage(BaseModel):
    """客户端 → 服务端 WS 消息"""
    type: Literal["start", "pause", "resume", "skip_round", "stop"]
    data: dict = Field(default_factory=dict)
