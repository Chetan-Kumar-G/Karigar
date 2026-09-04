"""F4 — Fair Cost-Aware Pricing endpoint (spec §12, §30)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.f4_pricing.features import PriceFeatures
from app.ai.f4_pricing.pricing import predict
from app.api.deps import Identity, get_db, optional_identity
from app.models import Listing, PriceHistory, Product
from app.models.ids import new_id
from app.services.helpers import demand_index, market_median
from app.schemas.models import PriceRequest

router = APIRouter(tags=["pricing"])


@router.post("/price/predict")
def price_predict(
    body: PriceRequest,
    ident: Identity | None = Depends(optional_identity),
    db: Session = Depends(get_db),
):
    category = body.category
    craft_id = None
    quality = 0.7
    rarity = 0.5
    region_id = None

    product = db.get(Product, body.product_id) if body.product_id else None
    if product:
        craft_id = product.craft_id
        category = category or product.category
        region_id = product.artisan.region_id if product.artisan else None
        if product.craft:
            rarity = product.craft.rarity_score
        img = next((i for i in product.images if i.is_primary), None)
        if img and img.readiness_score:
            quality = img.readiness_score / 100

    median = body.category_median_price_inr or market_median(db, category=category, craft_id=craft_id)
    di = demand_index(db, category, region_id)

    feats = PriceFeatures(
        material_cost_inr=body.material_cost_inr,
        labour_hours=body.labour_hours,
        labour_rate_inr_per_hour=body.labour_rate_inr_per_hour,
        packaging_cost_inr=body.packaging_cost_inr,
        logistics_cost_inr=body.logistics_cost_inr,
        category_median_price_inr=median,
        seasonality_index=body.seasonality_index,
        rarity_score=rarity,
        quality_score=quality,
        demand_index=di,
    )
    result = predict(feats, body.min_margin)

    # hard invariant (spec §30) — belt & braces on top of the formula
    if result.data["recommended_price_inr"] < result.data["sustainable_floor_inr"]:
        raise HTTPException(500, "Invariant violation: recommended price below floor")

    if product:
        if product.listing:
            product.listing.sustainable_floor_inr = result.data["sustainable_floor_inr"]
            product.listing.competitive_low_inr = result.data["competitive_range_inr"][0]
            product.listing.competitive_high_inr = result.data["competitive_range_inr"][1]
            product.listing.premium_opportunity_inr = result.data["premium_opportunity_inr"]
            if product.listing.current_price_inr < result.data["sustainable_floor_inr"]:
                product.listing.current_price_inr = result.data["recommended_price_inr"]
        else:
            product.listing = Listing(
                listing_id=new_id("LST"),
                product_id=product.product_id,
                current_price_inr=result.data["recommended_price_inr"],
                sustainable_floor_inr=result.data["sustainable_floor_inr"],
                competitive_low_inr=result.data["competitive_range_inr"][0],
                competitive_high_inr=result.data["competitive_range_inr"][1],
                premium_opportunity_inr=result.data["premium_opportunity_inr"],
                quality_score=quality,
            )
            db.add(product.listing)
        db.add(PriceHistory(product_id=product.product_id,
                            price_inr=result.data["recommended_price_inr"], source="recommended"))
        if product.status == "catalogued":
            product.status = "priced"
        result.persist(db, subject_id=product.product_id)
        db.commit()

    return {**result.data, "market_median_used_inr": round(median), "demand_index_used": round(di, 2),
            "_meta": result.metadata()}
