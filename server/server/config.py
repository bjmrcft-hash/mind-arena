"""Server configuration — loads from .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (mind-arena/.env)
_project_root = Path(__file__).parent.parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


class Settings:
    """Server settings loaded from environment."""

    HOST: str = os.environ.get("SERVER_HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("SERVER_PORT", "8000"))
    DEBUG: bool = os.environ.get("SERVER_DEBUG", "false").lower() == "true"

    # Database
    DB_PATH: str = os.environ.get(
        "DB_PATH", str(_project_root / "data" / "mindarena.db")
    )

    # Audio
    AUDIO_DIR: str = os.environ.get(
        "AUDIO_DIR", str(_project_root / "server" / "audio")
    )

    # LLM (passed to engine)
    LLM_BASE_URL: str = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_API_KEY: str = os.environ.get("LLM_API_KEY", "***")

    # CORS
    CORS_ORIGINS: list[str] = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(",")


settings = Settings()
