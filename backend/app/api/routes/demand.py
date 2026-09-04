"""F5 — Demand & Market Opportunity Intelligence endpoint (spec §12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.f5_demand.forecast import forecast
from app.api.deps import get_db
from app.models import Artisan, Craft, DemandSignal, Product

router = APIRouter(tags=["demand"])


@router.get("/demand/forecast")
def demand_forecast(
    category: str = Query(...),
    region_id: str | None = Query(default=None),
    window_days: int = Query(default=30, ge=7, le=180),
    artisan_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    capacity = 400
    if artisan_id:
        a = db.get(Artisan, artisan_id)
        if a:
            capacity = a.monthly_capacity_units
            region_id = region_id or a.region_id
    result = forecast(db, category, region_id=region_id, window_days=window_days,
                      artisan_monthly_capacity=capacity)
    result.persist(db, subject_id=f"{category}:{region_id or 'all'}")
    db.commit()
    return {**result.data, "_meta": result.metadata()}


@router.get("/demand/categories")
def demand_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(DemandSignal.category, DemandSignal.region_id).distinct()
    ).all()
    out = []
    for cat, rid in rows:
        out.append({"category": cat, "region_id": rid})
    return {"available": out}


@router.get("/demand/overview")
def demand_overview(artisan_id: str, db: Session = Depends(get_db)):
    """Convenience: forecast for every category the artisan actually sells."""
    a = db.get(Artisan, artisan_id)
    cats = sorted({p.category for p in a.products if p.category}) if a else []
    results = []
    for cat in cats[:4]:
        r = forecast(db, cat, region_id=a.region_id, window_days=30,
                     artisan_monthly_capacity=a.monthly_capacity_units)
        results.append({"category": cat, **r.data})
    return {"artisan_id": artisan_id, "forecasts": results}
