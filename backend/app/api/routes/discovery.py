"""F7 — Fair Market Discovery, exposure recording, Business Copilot, dashboard."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.f4_pricing.features import PriceFeatures
from app.ai.f4_pricing.pricing import predict as predict_price
from app.ai.f5_demand.forecast import forecast
from app.ai.f7_ranking.ranking import rank
from app.api.deps import Identity, current_identity, get_db, optional_identity
from app.models import (
    Artisan, Craft, Exposure, Interaction, Listing, Order, OrderAllocation, Product,
)
from app.models.ids import new_id
from app.services.helpers import build_candidates, demand_index, market_median

router = APIRouter(tags=["discovery"])


@router.get("/search")
def search(
    q: str = Query(default=""),
    category: str | None = Query(default=None),
    region_id: str | None = Query(default=None),
    fairness: bool = Query(default=True),
    limit: int = Query(default=20, le=50),
    session_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Listing).join(Product).where(Product.status == "published")
    if category:
        stmt = stmt.where(Product.category == category)
    if region_id:
        stmt = stmt.join(Artisan, Product.artisan_id == Artisan.artisan_id).where(
            Artisan.region_id == region_id
        )
    listings = db.scalars(stmt).all()
    cands = build_candidates(db, listings)
    result = rank(q, cands, apply_fairness=fairness)
    results = result.data["results"][:limit]

    # record one impression per shown listing (spec §32) — updates exposure state
    sid = session_id or new_id("SESS", 8)
    today = dt.date.today()
    for row in results:
        listing = db.get(Listing, row["listing_id"])
        if not listing:
            continue
        listing.impressions_total += 1
        listing.exposure_score = round(listing.exposure_score + 0.6, 3)
        exp = db.scalars(
            select(Exposure).where(Exposure.listing_id == listing.listing_id, Exposure.date == today)
        ).first()
        boost = row["score_breakdown"]["new_seller_boost"] > 0.3
        if exp:
            exp.impressions += 1
        else:
            db.add(Exposure(listing_id=listing.listing_id, date=today, impressions=1,
                            clicks=0, new_seller_boost_applied=boost))
        db.add(Interaction(interaction_id=new_id("IX"), buyer_session_id=sid,
                           listing_id=listing.listing_id, type="view", query=q))
    result.persist(db, subject_id=q or "browse")
    db.commit()

    return {"session_id": sid, "query": q, "count": len(results), "results": results,
            "weights": result.data["weights"],
            "fairness_applied": result.data["fairness_applied"],
            "exposure_gap_metric": result.data["exposure_gap_metric"],
            "_meta": result.metadata()}


@router.post("/search/click")
def record_click(listing_id: str = Query(...), session_id: str = Query(...),
                 db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing:
        raise HTTPException(404, "Listing not found")
    listing.clicks_total += 1
    today = dt.date.today()
    exp = db.scalars(
        select(Exposure).where(Exposure.listing_id == listing_id, Exposure.date == today)
    ).first()
    if exp:
        exp.clicks += 1
    db.add(Interaction(interaction_id=new_id("IX"), buyer_session_id=session_id,
                       listing_id=listing_id, type="click"))
    db.commit()
    return {"ok": True, "clicks_total": listing.clicks_total}


@router.get("/search/compare")
def search_compare(q: str = Query(...), db: Session = Depends(get_db)):
    """Judge view: same query ranked with fairness ON vs OFF."""
    listings = db.scalars(select(Listing).join(Product).where(Product.status == "published")).all()
    cands = build_candidates(db, listings)
    on = rank(q, cands, apply_fairness=True).data
    off = rank(q, cands, apply_fairness=False).data
    return {
        "query": q,
        "fairness_on": [{"rank": r["rank"], "artisan": r["artisan_name"], "craft": r["craft"],
                         "final": r["score_breakdown"]["final_score"]} for r in on["results"][:8]],
        "fairness_off": [{"rank": r["rank"], "artisan": r["artisan_name"], "craft": r["craft"],
                          "final": r["score_breakdown"]["final_score"]} for r in off["results"][:8]],
        "exposure_gap_on": on["exposure_gap_metric"], "exposure_gap_off": off["exposure_gap_metric"],
        "weights": on["weights"],
    }


# ── Business Copilot (F7) ─────────────────────────────────────────────
@router.get("/artisan/{artisan_id}/insights")
def artisan_insights(artisan_id: str, db: Session = Depends(get_db)):
    a = db.get(Artisan, artisan_id)
    if not a:
        raise HTTPException(404, "Artisan not found")
    cards: list[dict] = []

    for p in a.products:
        if not p.category:
            continue
        # ── demand (F5) ──
        fc = forecast(db, p.category, region_id=a.region_id, window_days=30,
                      artisan_monthly_capacity=a.monthly_capacity_units).data
        if fc["trend_pct"] >= 8 and fc["action_recommendation"]["recommended_additional_units"] > 0:
            cards.append({
                "type": "opportunity", "colour": "blue", "feature": "F5",
                "title": f"Demand rising for {p.category}",
                "observation": f"Forecast demand is up {fc['trend_pct']}% over the next 30 days "
                               f"({fc['predicted_demand_units']} units).",
                "action": fc["action_recommendation"]["text_en"],
                "supporting_signals": ["F5 demand forecast (simulated history)"],
                "confidence": 0.68,
                "product_id": p.product_id,
            })

        # ── pricing (F4) ──
        if p.listing and p.listing.sustainable_floor_inr:
            median = market_median(db, category=p.category, craft_id=p.craft_id)
            di = demand_index(db, p.category, a.region_id)
            img = next((i for i in p.images if i.is_primary), None)
            quality = (img.readiness_score / 100) if img and img.readiness_score else p.listing.quality_score
            feats = PriceFeatures(
                material_cost_inr=p.listing.current_price_inr * 0.35,
                labour_hours=8, labour_rate_inr_per_hour=60,
                packaging_cost_inr=p.listing.current_price_inr * 0.05,
                logistics_cost_inr=a.logistics_cost_per_unit_inr * 5,
                category_median_price_inr=median,
                rarity_score=p.craft.rarity_score if p.craft else 0.5,
                quality_score=quality, demand_index=di,
            )
            pr = predict_price(feats).data
            if pr["recommended_price_inr"] > p.listing.current_price_inr * 1.06:
                cards.append({
                    "type": "pricing", "colour": "green", "feature": "F4",
                    "title": f"You may be underpricing “{p.title}”",
                    "observation": f"Current price ₹{round(p.listing.current_price_inr)}. "
                                   f"A fair price is around ₹{pr['recommended_price_inr']}.",
                    "action": f"Try ₹{pr['recommended_price_inr']} — "
                              + pr["why_plain"],
                    "supporting_signals": ["F4 pricing model", "F5 demand index"],
                    "confidence": pr["confidence"], "product_id": p.product_id,
                })

        # ── listing quality (F1) ──
        img = next((i for i in p.images if i.is_primary), None)
        if img and img.readiness_score and img.readiness_score < 70:
            cards.append({
                "type": "listing", "colour": "orange", "feature": "F1",
                "title": f"Photo quality is low for “{p.title}”",
                "observation": f"Readiness score {img.readiness_score}/100 "
                               f"(decision: {img.decision}).",
                "action": "Open AI Product Studio and use Auto-Enhance, or retake the photo.",
                "supporting_signals": ["F1 readiness score"],
                "confidence": 0.8, "product_id": p.product_id,
            })

    # ── B2B opportunities (F6) ──
    from app.models import BuyerRequirement
    open_reqs = db.scalars(
        select(BuyerRequirement).where(BuyerRequirement.status.in_(["open", "matched"]))
    ).all()
    my_crafts = {p.craft_id for p in a.products}
    my_regions = {a.region_id}
    for r in open_reqs:
        craft = db.get(Craft, r.craft_id) if r.craft_id else None
        if r.craft_id in my_crafts or (craft and craft.region_id in my_regions):
            cards.append({
                "type": "buyer", "colour": "blue", "feature": "F6",
                "title": f"B2B buyer needs {r.quantity:,} units",
                "observation": f"{r.title} — budget ₹{round(r.price_min)}–₹{round(r.price_max)}/unit.",
                "action": "View the opportunity — the order can be pooled across your cluster.",
                "supporting_signals": ["F6 buyer requirement"],
                "confidence": 0.72, "requirement_id": r.requirement_id,
            })

    priority = {"buyer": 0, "opportunity": 1, "pricing": 2, "listing": 3}
    cards.sort(key=lambda c: priority.get(c["type"], 9))
    return {"artisan_id": artisan_id, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "insights": cards,
            "note": "Every card is generated from structured F1/F4/F5/F6 outputs; "
                    "an LLM (if enabled) only rephrases them (spec §17)."}


# ── Artisan dashboard (spec §7) ─────────────────────────────────────
@router.get("/artisan/{artisan_id}/dashboard")
def dashboard(artisan_id: str, db: Session = Depends(get_db)):
    a = db.get(Artisan, artisan_id)
    if not a:
        raise HTTPException(404, "Artisan not found")
    products = a.products
    published = [p for p in products if p.status == "published"]
    my_alloc = db.scalars(
        select(OrderAllocation).where(OrderAllocation.artisan_id == artisan_id)
    ).all()
    revenue = sum(al.payment_share_inr for al in my_alloc if al.status == "accepted")
    active_orders = len({al.order_id for al in my_alloc
                         if al.status in ("proposed", "accepted")})
    insights = artisan_insights(artisan_id, db)["insights"]
    return {
        "greeting": _greeting(),
        "artisan_name": a.name,
        "summary": {
            "products_listed": len(published),
            "drafts": len(products) - len(published),
            "b2b_orders": active_orders,
            "b2b_revenue_inr": round(revenue),
            "pending_actions": len(insights),
        },
        "attention": insights[:3],
        "quick_actions": ["add_product", "record_voice", "check_price", "find_buyers"],
    }


def _greeting() -> str:
    h = dt.datetime.now().hour
    return "Good morning" if h < 12 else "Good afternoon" if h < 17 else "Good evening"
