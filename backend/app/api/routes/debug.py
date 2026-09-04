"""Judge-facing "AI System Insights" — technical metadata per feature (spec §35, §45)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import AiRun

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/ai-runs")
def ai_runs(feature: str | None = Query(default=None), limit: int = Query(default=40, le=200),
            subject_id: str | None = Query(default=None), db: Session = Depends(get_db)):
    q = select(AiRun).order_by(desc(AiRun.created_at))
    if feature:
        q = q.where(AiRun.feature == feature.upper())
    if subject_id:
        q = q.where(AiRun.subject_id == subject_id)
    rows = db.scalars(q.limit(limit)).all()
    return {"runs": [{
        "id": r.id, "feature": r.feature, "model": r.model, "version": r.version,
        "mode": r.mode, "subject_id": r.subject_id, "inputs": r.inputs,
        "output": r.output, "latency_ms": round(r.latency_ms, 1),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]}


@router.get("/ai-runs/summary")
def ai_runs_summary(db: Session = Depends(get_db)):
    rows = db.scalars(select(AiRun)).all()
    by_feature: dict[str, dict] = {}
    for r in rows:
        f = by_feature.setdefault(r.feature, {"count": 0, "modes": {}, "avg_latency_ms": 0.0,
                                              "last_model": r.model})
        f["count"] += 1
        f["modes"][r.mode] = f["modes"].get(r.mode, 0) + 1
        f["avg_latency_ms"] += r.latency_ms
        f["last_model"] = r.model
    for f in by_feature.values():
        f["avg_latency_ms"] = round(f["avg_latency_ms"] / max(f["count"], 1), 1)
    return {"summary": by_feature, "total_runs": len(rows)}


@router.get("/f7-explain")
def f7_explain(q: str = Query(default="handwoven cotton"), db: Session = Depends(get_db)):
    """Full F7 score breakdown table for a query (spec §32)."""
    from app.ai.f7_ranking.ranking import rank
    from app.models import Listing, Product
    from app.services.helpers import build_candidates

    listings = db.scalars(select(Listing).join(Product).where(Product.status == "published")).all()
    res = rank(q, build_candidates(db, listings), apply_fairness=True).data
    return {"query": q, "weights": res["weights"],
            "rows": [{"rank": r["rank"], "artisan": r["artisan_name"], "craft": r["craft"],
                      "region": r["region"], **r["score_breakdown"], "why": r["why"]}
                     for r in res["results"]],
            "exposure_gap_metric": res["exposure_gap_metric"]}
