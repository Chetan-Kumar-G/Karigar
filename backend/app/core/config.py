"""Central runtime configuration.

Everything is environment-overridable (see ``.env.example``).  The prototype is
designed to boot with **zero configuration** — SQLite on disk, deterministic AI
fallbacks — and to progressively light up real infrastructure (Postgres, Whisper
ASR, an LLM endpoint) as environment variables are supplied.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_ROOT / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
MODEL_DIR = DATA_DIR / "models"
SEED_DIR = DATA_DIR / "seed"
SAMPLE_DIR = DATA_DIR / "samples"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", BACKEND_ROOT.parent / ".env"),
        env_prefix="SIH_",
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────
    app_name: str = "SIH 26090 — Artisan Market Linkage API"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    # ── Database ──────────────────────────────────────────────────────────
    # Default: local file SQLite. Override with e.g.
    #   SIH_DATABASE_URL=postgresql+psycopg://sih:sih@localhost:5432/sih
    database_url: str = f"sqlite:///{(DATA_DIR / 'sih.db').as_posix()}"
    sql_echo: bool = False

    # ── Auth ──────────────────────────────────────────────────────────────
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 24 * 7
    mock_otp: str = "123456"  # accepted for every phone number in prototype mode

    # ── F2 — ASR + catalog generation ────────────────────────────────────
    asr_backend: str = "auto"          # auto | whisper | api | fallback
    whisper_model: str = "base"        # tiny | base | small | medium (local faster-whisper)
    whisper_language: str = "auto"     # "auto" | ISO code e.g. "hi", "ta"
    asr_api_model: str = "whisper-1"   # model name for the OpenAI-compatible /audio/transcriptions
    llm_enabled: bool = False
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # ── F4 — pricing ────────────────────────────────────────────────────
    pricing_min_margin: float = 0.18   # spec §6.I default sustainable margin

    # ── F6 — allocation ────────────────────────────────────────────────
    f6_lambda: float = 40.0            # cost vs quality/reliability trade-off
    f6_min_lot_size: int = 100
    f6_max_artisans_per_order: int = 8
    f6_solver: str = "cp_sat"          # cp_sat | cbc

    # ── F7 — fair ranking weights (spec §9.I) ──────────────────────────
    f7_alpha: float = 1.0    # relevance
    f7_beta: float = 0.35    # new-seller boost
    f7_gamma: float = 0.25   # underserved-region boost
    f7_delta: float = 0.30   # exposure penalty
    f7_new_seller_sales_threshold: int = 15

    # ── Uploads ───────────────────────────────────────────────────────
    max_upload_mb: int = 15
    allowed_image_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp", "image/heic")
    allowed_audio_types: tuple[str, ...] = (
        "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/aac",
        "audio/m4a", "audio/x-m4a", "audio/ogg", "application/octet-stream",
    )

    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


@lru_cache
def get_settings() -> Settings:
    for d in (DATA_DIR, UPLOAD_DIR, MODEL_DIR):
        d.mkdir(parents=True, exist_ok=True)
    return Settings()


settings = get_settings()
