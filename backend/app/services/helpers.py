"""Shared orchestration helpers used by more than one route."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.f6_matching.allocation import EligibleArtisan
from app.ai.f7_ranking.ranking import Candidate
from app.models import (
    Artisan, Craft, DemandSignal, Listing, MarketPrice, Product, VerificationProfile,
)
from app.models.trust import TRUST_ACTIVE_STATES


# ── F4 helpers ──────────────────────────────────────────────────────
def market_median(db: Session, *, category: str | None, craft_id: str | None) -> float:
    q = select(MarketPrice)
    if category:
        q = q.where(MarketPrice.category == category)
    row = db.scalars(q.order_by(MarketPrice.observed_at.desc())).first()
    if row:
        return row.median_price_inr
    if craft_id:
        craft = db.get(Craft, craft_id)
        if craft and craft.materials:
            return max(c.cost_prior_inr or 0 for c in craft.materials) * 3.0
    return 600.0


def demand_index(db: Session, category: str | None, region_id: str | None) -> float:
    if not category:
        return 0.5
    recent = dt.date.today() - dt.timedelta(days=30)
    q = select(func.avg(DemandSignal.units_sold)).where(
        DemandSignal.category == category, DemandSignal.date >= recent
    )
    older = select(func.avg(DemandSignal.units_sold)).where(
        DemandSignal.category == category,
        DemandSignal.date < recent, DemandSignal.date >= recent - dt.timedelta(days=60),
    )
    a, b = db.scalar(q) or 0, db.scalar(older) or 0
    if not b:
        return 0.5
    return float(max(0.05, min(0.95, 0.5 + (a - b) / max(b, 1))))


# ── F6 helpers ──────────────────────────────────────────────────────
def eligible_artisans_for_craft(
    db: Session, craft_id: str | None, unit_price_max: float, unit_price_min: float
) -> list[EligibleArtisan]:
    q = select(Artisan)
    craft = db.get(Craft, craft_id) if craft_id else None
    region_family = None
    if craft:
        region_family = {
            c.craft_id for c in db.scalars(
                select(Craft).where(Craft.region_id == craft.region_id)
            ).all()
        }
        region_family.add(craft.craft_id)
    profiles = {
        p.subject_id: p for p in db.scalars(
            select(VerificationProfile).where(VerificationProfile.subject_type == "artisan")
        ).all()
    }
    out: list[EligibleArtisan] = []
    for a in db.scalars(q).all():
        prof = profiles.get(a.artisan_id)
        v_status = prof.verification_status if prof else "PENDING"
        v_reliability = prof.reliability_score if prof else round(a.reliability_score * 100, 1)
        # per-unit cost estimate from the artisan's cheapest published listing
        cheapest = db.scalars(
            select(func.min(Listing.current_price_inr)).join(Product)
            .where(Product.artisan_id == a.artisan_id)
        ).first()
        # B2B unit cost ≈ making cost, well under retail and inside the buyer's
        # band (an artisan quoting a bulk order prices to win it).
        base_price = cheapest or unit_price_min or 200
        unit_cost = round(min(base_price * 0.45, (unit_price_max or base_price) * 0.92), 2)
        unit_cost = max(unit_cost, (unit_price_min or 0) * 0.8, 20.0)
        if not craft_id:
            craft_match = True
        else:
            allowed = region_family or {craft_id}
            craft_match = any(p.craft_id in allowed for p in a.products)
        out.append(EligibleArtisan(
            artisan_id=a.artisan_id, name=a.name,
            capacity_units=a.monthly_capacity_units,
            unit_cost_inr=max(unit_cost, 20.0),
            quality_score=a.quality_score, reliability_score=a.reliability_score,
            logistics_cost_inr_per_unit=a.logistics_cost_per_unit_inr,
            craft_match=bool(craft_match),
            verified=v_status in TRUST_ACTIVE_STATES,
            verification_status=v_status,
            reliability_pct=v_reliability,
        ))
    return out


# ── F7 helpers ──────────────────────────────────────────────────────
def build_candidates(db: Session, listings: list[Listing]) -> list[Candidate]:
    cands: list[Candidate] = []
    for l in listings:
        p: Product = l.product
        a: Artisan = p.artisan
        craft = p.craft
        img = next((i for i in p.images if i.is_primary), p.images[0] if p.images else None)
        kw = " ".join(p.seo_keywords or [])
        text = " ".join(filter(None, [
            p.title, p.description_en, craft.name if craft else "", p.category,
            a.region.name if a.region else "", a.region.state if a.region else "", kw,
        ]))
        cands.append(Candidate(
            listing_id=l.listing_id, product_id=p.product_id, text=text,
            craft=craft.name if craft else "Handmade craft",
            region=f"{a.region.name}, {a.region.state}" if a.region else "India",
            artisan_name=a.name, price_inr=l.current_price_inr, rating=l.rating,
            quality_score=l.quality_score, verified_sales_count=a.verified_sales_count,
            region_underserved_index=a.region.underserved_index if a.region else 0.5,
            exposure_score=l.exposure_score,
            thumbnail_url=(img.enhanced_url or img.url) if img else None,
        ))
    return cands
