from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
PACK_DIR = BASE_DIR / "challenge_pack"
DATA_DIR = PACK_DIR / "data"


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    demo_mode: bool = _bool("DEMO_MODE", True)
    live_fetch_enabled: bool = _bool("LIVE_FETCH_ENABLED", False)
    allow_internal_data_to_external_ai: bool = _bool("ALLOW_INTERNAL_DATA_TO_EXTERNAL_AI", False)
    cors_origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip())
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_research_model: str = os.getenv("OPENAI_RESEARCH_MODEL", "gpt-5.5")
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    gemini_research_model: str = os.getenv("GEMINI_RESEARCH_MODEL", "gemini-3.8-flash")
    microsoft_research_url: str | None = os.getenv("MICROSOFT_RESEARCH_URL") or None
    microsoft_research_token: str | None = os.getenv("MICROSOFT_RESEARCH_TOKEN") or None
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY") or None
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "90"))
    source_max_bytes: int = int(os.getenv("SOURCE_MAX_BYTES", "1500000"))
    pipeline_db_path: str = os.getenv("PIPELINE_DB_PATH", "/tmp/grantcurrent.db")
    rag_max_context_chars: int = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "16000"))


settings = Settings()
