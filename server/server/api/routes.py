"""REST API routes."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from server.db.database import get_db
from server.db.repository import DebateRepository
from server.services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Request/Response models ──

class CreateDebateRequest(BaseModel):
    topic: str
    mode: str = "standard"
    models: dict[str, str] | None = None
    tts_enabled: bool = False


class DebateResponse(BaseModel):
    id: str
    topic: str
    status: str
    current_round: int = 0
    current_exchange: int = 0
    created_at: str | None = None
    completed_at: str | None = None


# ── Routes ──

@router.post("/debates")
async def create_debate(
    req: CreateDebateRequest,
    background_tasks: BackgroundTasks,
):
    """Create and start a new debate."""
    try:
        result = await session_service.create_debate(
            topic=req.topic,
            mode=req.mode,
            models=req.models,
            tts_enabled=req.tts_enabled,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Run debate in background
    background_tasks.add_task(session_service.run_debate, result["id"])

    return result


@router.get("/debates")
async def list_debates(limit: int = 20, offset: int = 0):
    """List debate sessions."""
    db = await get_db()
    try:
        repo = DebateRepository(db)
        sessions = await repo.list_sessions(limit=limit, offset=offset)
        return {"debates": sessions, "count": len(sessions)}
    finally:
        await db.close()


@router.get("/debates/{session_id}")
async def get_debate(session_id: str):
    """Get debate details."""
    db = await get_db()
    try:
        repo = DebateRepository(db)
        session = await repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")
        messages = await repo.get_messages(session_id)
        rounds = await repo.get_rounds(session_id)
        return {
            "session": session,
            "rounds": rounds,
            "messages": messages,
        }
    finally:
        await db.close()


@router.post("/debates/{session_id}/pause")
async def pause_debate(session_id: str):
    """Pause a running debate."""
    ok = await session_service.pause_debate(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Debate not found")
    return {"status": "paused"}


@router.post("/debates/{session_id}/resume")
async def resume_debate(session_id: str):
    """Resume a paused debate."""
    ok = await session_service.resume_debate(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Debate not found")
    return {"status": "running"}


@router.post("/debates/{session_id}/stop")
async def stop_debate(session_id: str):
    """Stop a debate."""
    ok = await session_service.stop_debate(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Debate not found")
    return {"status": "stopped"}


@router.post("/debates/{session_id}/skip")
async def skip_round(session_id: str):
    """Skip current round."""
    ok = await session_service.skip_round(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Debate not found")
    return {"status": "skipped"}


@router.get("/debates/{session_id}/messages")
async def get_messages(session_id: str, limit: int = 200):
    """Get debate messages."""
    db = await get_db()
    try:
        repo = DebateRepository(db)
        messages = await repo.get_messages(session_id, limit=limit)
        return {"messages": messages, "count": len(messages)}
    finally:
        await db.close()


@router.get("/debates/{session_id}/export")
async def export_debate(session_id: str, format: str = "markdown"):
    """Export debate as Markdown or JSON."""
    db = await get_db()
    try:
        repo = DebateRepository(db)
        session = await repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Debate not found")

        messages = await repo.get_messages(session_id)

        if format == "json":
            return {"session": session, "messages": messages}

        # Markdown format
        role_names = {"A": "主持人 A", "B": "正方 B", "C": "反方 C"}
        lines = [
            f"# MindArena 辩论记录",
            f"",
            f"**话题**: {session['topic']}",
            f"**状态**: {session['status']}",
            f"**轮次**: {session['current_round']}",
            f"",
            f"---",
            f"",
        ]

        for msg in messages:
            role = role_names.get(msg["role"], msg["role"])
            lines.append(f"## {role} — {msg['message_type']}")
            lines.append(f"")
            lines.append(msg["content"])
            lines.append(f"")

        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(
            "\n".join(lines),
            media_type="text/markdown",
            headers={
                "Content-Disposition": f"attachment; filename=debate_{session_id[:8]}.md"
            },
        )
    finally:
        await db.close()


@router.get("/config/models")
async def get_models():
    """Get available model configuration."""
    from engine.llm.model_router import DEFAULT_MODELS, AGENT_ROLES
    return {
        "default_models": DEFAULT_MODELS,
        "agent_roles": AGENT_ROLES,
    }


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "ok", "service": "mind-arena"}


@router.get("/models/health")
async def models_health():
    """Check health of all configured models."""
    from engine.model_health import check_all_models
    from engine.llm.llm_service import LLMService
    from engine.llm.model_router import ModelRouter
    from engine.debate_engine import PROVIDER_CONFIGS, MODEL_PROVIDER_MAP
    from server.config import settings

    # Resolve models from env
    router = ModelRouter({})
    assignments = router.resolve()
    model_ids = {role: a.model for role, a in assignments.items()}

    # Register providers
    llm = LLMService()
    for name, (base_url, env_key) in PROVIDER_CONFIGS.items():
        api_key = os.environ.get(env_key, "")
        if api_key:
            llm.register_provider(name, base_url, api_key)

    # Try loading from OpenClaw auth-profiles.json
    import json as _json
    from pathlib import Path as _Path
    auth_path = _Path.home() / ".openclaw" / "agents" / "main" / "agent" / "auth-profiles.json"
    if auth_path.exists():
        try:
            with open(auth_path, encoding="utf-8") as f:
                auth = _json.load(f)
            profiles = auth.get("profiles", {})
            PROVIDER_AUTH_MAP = {
                "qwen": "qwen:default",
                "nvidia": "nvidia:default",
                "moonshot": "moonshot:default",
                "xiaomi": "xiaomi:default",
            }
            for provider, profile_id in PROVIDER_AUTH_MAP.items():
                if provider in llm._providers:
                    continue
                profile = profiles.get(profile_id, {})
                key = profile.get("key", "") or profile.get("apiKey", "")
                if key and provider in PROVIDER_CONFIGS:
                    base_url = PROVIDER_CONFIGS[provider][0]
                    llm.register_provider(provider, base_url, key)
        except Exception:
            pass

    result = await check_all_models(model_ids, llm)

    return {
        "all_ok": result.all_ok,
        "models": {
            role: {
                "model": s.model_id,
                "provider": s.provider,
                "available": s.available,
                "latency_ms": round(s.latency_ms, 0),
                "error": s.error,
            }
            for role, s in result.models.items()
        },
        "fallback_chain": result.fallback_chain,
    }
