"""FastAPI application entry point (spec §2, §12, §21, §26)."""
from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app import __version__
from app.core.config import UPLOAD_DIR, settings
from app.core.logging import get_logger
from app.db.base import Base
from app.db.session import SessionLocal, engine

log = get_logger("app")


def _ensure_db() -> None:
    import app.models  # noqa: F401  (register mappers)

    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        from app.models import Artisan

        if db.query(Artisan).count() == 0:
            log.info("Empty database — seeding demo dataset ...")
            from app.db.seed import seed

            seed(db, reset=False)
    finally:
        db.close()


def create_app() -> FastAPI:
    _ensure_db()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="AI-Driven Market Linkage & Smart Cataloging for Marginalized Artisans "
                    "— SIH PS 26090 prototype backend.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(UPLOAD_DIR)), name="media")

    from app.api.routes import (
        auth, buyers, catalog, craft, debug, demand, demo, discovery, meta, orders, pricing,
        products, trust,
    )

    for r in (meta, auth, products, catalog, craft, pricing, demand, buyers, orders,
              discovery, debug, demo, trust):
        app.include_router(r.router, prefix=settings.api_prefix)

    @app.exception_handler(OperationalError)
    async def _db_locked(request: Request, exc: OperationalError):  # spec §26 db failure
        # Two near-simultaneous writes on SQLite (e.g. a fast double-tap on
        # Inventory's +/-) can race for the writer lock. The *first* request
        # already committed by the time the *second* sees this — it is safe
        # (and usually correct) to just retry.
        log.warning("DB write contention on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=503,
            content={
                "detail": "The server was busy saving another change. Please try again.",
                "error_type": "OperationalError",
                "retryable": True,
                "path": request.url.path,
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):  # human-readable, no raw 500s
        log.error("Unhandled error on %s: %s\n%s", request.url.path, exc, traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={
                "detail": "We couldn't process that right now. Your work is safe — please try again.",
                "error_type": type(exc).__name__,
                "path": request.url.path,
            },
        )

    @app.get("/")
    def root():
        return {"service": settings.app_name, "version": __version__,
                "docs": "/docs", "health": f"{settings.api_prefix}/health"}

    @app.get("/health")
    def health_alias():
        # Bare alias so a plain `curl http://host:8000/health` works too.
        from app.api.routes.meta import _health_payload

        return _health_payload()

    _log_asr_banner()
    return app


def _log_asr_banner() -> None:
    """One clear line on boot so you know if live voice (F2) is active."""
    try:
        from app.ai.f2_catalog.asr import asr_status

        s = asr_status()
        if s["real_asr_available"]:
            log.info("F2 voice: REAL speech-to-text ACTIVE via %s (model=%s, lang=%s)",
                     s["active_backend"], s.get("whisper_model"), s.get("whisper_language"))
        else:
            log.warning("F2 voice: no ASR engine — recorded audio uses a marked demo "
                        "transcript. Set SIH_LLM_API_KEY or run under .venv312 "
                        "(faster-whisper). Check: GET /api/catalog/asr-status")
    except Exception as exc:  # pragma: no cover
        log.warning("F2 voice: could not determine ASR status: %s", exc)


app = create_app()
