"""Health, feature-status matrix, and reference lookups for pickers."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_db
from app.core.config import MODEL_DIR, settings
from app.core.logging import get_logger
from app.db.session import SessionLocal, engine
from app.models import Craft, Material, Region, Technique

router = APIRouter(tags=["meta"])
log = get_logger("meta")


def _health_payload() -> dict:
    """Lightweight liveness + DB probe. Never raises — a down DB still returns 200
    with ``database: "error"`` so the client can tell *backend unavailable* apart
    from *DB unavailable* apart from *invalid credentials*."""
    db_status = "error"
    db_backend = engine.url.get_backend_name()
    product_count = 0
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            product_count = db.scalar(select(func.count()).select_from(Craft)) or 0
            db_status = "ok"
        finally:
            db.close()
    except Exception as exc:  # pragma: no cover - only when the DB file is missing/locked
        log.warning("health: database probe failed: %s", exc)
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "database_backend": db_backend,
        "version": __version__,
        "environment": settings.environment,
        "products": product_count,
    }


@router.get("/health")
def health():
    return _health_payload()


@router.get("/meta/features")
def features():
    from app.ai.f2_catalog.asr import asr_status

    f4 = (MODEL_DIR / "f4_price.txt").exists()
    f5 = (MODEL_DIR / "f5_q50.txt").exists()
    _asr = asr_status()
    return {
        "F1": {"name": "AI Product Studio", "mode": "REAL",
               "engine": "OpenCV (GrabCut seg + Laplacian/histogram scoring + CLAHE/Zero-DCE-style enhance)"},
        "F2": {"name": "Multilingual Grounded Auto-Cataloger",
               "mode": "REAL (grounding) + PROTOTYPE (cross-modal heuristic)",
               "engine": f"ASR active='{_asr['active_backend']}' "
                         f"(real={_asr['real_asr_available']}), "
                         f"LLM phrasing={'on' if settings.llm_enabled else 'off'}"},
        "F3": {"name": "Craft Knowledge Graph + Passport", "mode": "REAL",
               "engine": "Relational graph + recursive CTE + spec-§5.I confidence formula"},
        "F4": {"name": "Fair Cost-Aware Pricing",
               "mode": "REAL" if f4 else "FALLBACK",
               "engine": "LightGBM + tree-SHAP" if f4 else "Deterministic cost-plus-market formula"},
        "F5": {"name": "Demand Intelligence",
               "mode": "REAL model / SIMULATED_DATA history" if f5 else "FALLBACK (seasonal-naive)",
               "engine": "LightGBM quantile regression" if f5 else "seasonal-naive + trend"},
        "F6": {"name": "B2B Matching + Cluster Pooling", "mode": "REAL",
               "engine": "OR-Tools CP-SAT MILP + exact Shapley value"},
        "F7": {"name": "Fair Market Discovery + Copilot", "mode": "REAL",
               "engine": "TF-IDF retrieval + exposure-fairness re-rank"},
        "F8": {"name": "Trust & Verification (Verified Artisan / Business)",
               "mode": "REAL (evidence + state machine) / PROTOTYPE (simulated payments)",
               "engine": "Evidence-backed verification axes + trust-status state machine + "
                         "explainable reliability score + AI risk-flag → human review; "
                         "F6 eligibility gate; simulated B2B milestone/commitment flow"},
        "weights": {
            "f7_alpha": settings.f7_alpha, "f7_beta": settings.f7_beta,
            "f7_gamma": settings.f7_gamma, "f7_delta": settings.f7_delta,
            "f6_lambda": settings.f6_lambda, "pricing_min_margin": settings.pricing_min_margin,
        },
    }


@router.get("/reference")
def reference(db: Session = Depends(get_db)):
    return {
        "regions": [{"id": r.region_id, "name": r.name, "state": r.state,
                     "underserved_index": r.underserved_index}
                    for r in db.scalars(select(Region).order_by(Region.name)).all()],
        "crafts": [{"id": c.craft_id, "name": c.name, "region_id": c.region_id,
                    "gi_status": c.gi_status, "rarity_score": c.rarity_score}
                   for c in db.scalars(select(Craft).order_by(Craft.name)).all()],
        "techniques": [{"id": t.technique_id, "name": t.name}
                       for t in db.scalars(select(Technique).order_by(Technique.name)).all()],
        "materials": [{"id": m.material_id, "name": m.name, "cost_prior_inr": m.cost_prior_inr}
                      for m in db.scalars(select(Material).order_by(Material.name)).all()],
        "categories": [row[0] for row in db.execute(
            select(Craft.craft_id)).all()],
    }
