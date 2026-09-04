"""F6 — B2B matching, cluster order pooling, allocation commit (spec §8, §12, §31)."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.f6_matching.allocation import BuyerOrder, EligibleArtisan, allocate
from app.api.deps import Identity, current_identity, get_db, optional_identity
from app.models import (
    Artisan, Buyer, BuyerRequirement, Craft, DemandSignal, Order, OrderAllocation,
    VerificationProfile,
)
from app.models.ids import new_id
from app.schemas.models import AllocateRequest, ArtisanInput, BuyerMatchRequest
from app.services.helpers import eligible_artisans_for_craft

router = APIRouter(tags=["orders"])


def _order_dict(o: Order, db: Session) -> dict:
    v_profiles = {
        p.subject_id: p for p in db.scalars(
            select(VerificationProfile).where(VerificationProfile.subject_type == "artisan")
        ).all()
    }
    # per-artisan "why" strings stashed on the order's optimization_meta (Phase 12)
    _rat = (o.optimization_meta or {}).get("rationales", {}) if o.optimization_meta else {}
    return {
        "order_id": o.order_id, "buyer_id": o.buyer_id,
        "buyer_name": db.get(Buyer, o.buyer_id).name if db.get(Buyer, o.buyer_id) else None,
        "requirement_id": o.requirement_id,
        "status": o.status, "total_quantity": o.total_quantity,
        "total_allocated": o.total_allocated, "fulfillment_pct": o.fulfillment_pct,
        "total_cost_inr": o.total_cost_inr, "total_buyer_payment_inr": o.total_buyer_payment_inr,
        "objective_value": o.objective_value, "solve_time_ms": o.solve_time_ms,
        "solver": o.solver, "revenue_allocation_method": o.revenue_allocation_method,
        "optimization_meta": o.optimization_meta,
        "allocations": [{
            "allocation_id": al.allocation_id, "artisan_id": al.artisan_id,
            "artisan_name": db.get(Artisan, al.artisan_id).name if db.get(Artisan, al.artisan_id) else al.artisan_id,
            "allocated_units": al.allocated_units, "unit_price_inr": al.unit_price_inr,
            "unit_cost_inr": al.unit_cost_inr, "payment_share_inr": al.payment_share_inr,
            "proportional_share_inr": al.proportional_share_inr,
            "shapley_marginal_inr": al.shapley_marginal, "status": al.status,
            "verification_status": (v_profiles[al.artisan_id].verification_status
                                    if al.artisan_id in v_profiles else "PENDING"),
            "verified": (al.artisan_id in v_profiles
                         and v_profiles[al.artisan_id].verification_status
                         in ("VERIFIED", "REINSTATED")),
            "reliability_pct": (v_profiles[al.artisan_id].reliability_score
                                if al.artisan_id in v_profiles else None),
            "allocation_rationale": _rat.get(al.artisan_id, {}).get("allocation", ""),
            "payment_rationale": _rat.get(al.artisan_id, {}).get("payment", ""),
            "capacity_used_pct": _rat.get(al.artisan_id, {}).get("capacity_used_pct"),
        } for al in o.allocations],
        "created_at": o.created_at.isoformat() if o.created_at else None,
    }


@router.post("/buyer/match")
def buyer_match(
    body: BuyerMatchRequest,
    ident: Identity | None = Depends(optional_identity),
    db: Session = Depends(get_db),
):
    """Run F6: eligibility filter → CP-SAT MILP allocation → Shapley payment split."""
    req = db.get(BuyerRequirement, body.requirement_id) if body.requirement_id else None
    if req:
        quantity = req.quantity
        pmin, pmax = req.price_min, req.price_max
        craft_id = req.craft_id
        material = req.required_material
        fulfillment_min = req.fulfillment_min
        buyer_id = req.buyer_id
        lam = req.lambda_weight
    else:
        if not (body.quantity and body.unit_price_min and body.unit_price_max):
            raise HTTPException(422, "Provide requirement_id, or quantity + price band")
        quantity, pmin, pmax = body.quantity, body.unit_price_min, body.unit_price_max
        craft_id, material = body.required_craft_id, body.required_material
        fulfillment_min = body.fulfillment_min
        buyer_id = ident.buyer_id if ident and ident.role == "buyer" else \
            (db.scalars(select(Buyer)).first().buyer_id)
        lam = body.lambda_weight

    if body.artisans:
        pool = [EligibleArtisan(
            artisan_id=a.artisan_id, name=a.name or a.artisan_id,
            capacity_units=a.capacity_units, unit_cost_inr=a.unit_cost_inr,
            quality_score=a.quality_score, reliability_score=a.reliability_score,
            logistics_cost_inr_per_unit=a.logistics_cost_inr_per_unit, craft_match=a.craft_match,
        ) for a in body.artisans]
    else:
        pool = eligible_artisans_for_craft(db, craft_id, pmax, pmin)

    order_input = BuyerOrder(
        quantity=quantity, unit_price_min=pmin, unit_price_max=pmax,
        required_craft_id=craft_id, required_material=material,
        fulfillment_min=fulfillment_min, lambda_weight=lam,
    )
    result = allocate(order_input, pool)
    d = result.data

    order = Order(
        order_id=new_id("ORD", 5), requirement_id=req.requirement_id if req else None,
        buyer_id=buyer_id, total_quantity=quantity,
        total_allocated=d.get("total_allocated", 0),
        status=d.get("status", "proposed"),
        total_cost_inr=d.get("total_cost_inr", 0.0),
        total_buyer_payment_inr=d.get("total_buyer_payment_inr", 0.0),
        objective_value=d.get("objective_value"), solve_time_ms=d.get("solve_time_ms"),
        solver=d.get("solver", "cp_sat"),
        fulfillment_pct=d.get("fulfillment_pct", 0.0),
        optimization_meta={
            **{k: d.get(k) for k in (
                "capacity_utilization_pct", "shortfall_units", "lambda", "shapley_note",
                "shapley_method", "fairness_check", "solver_optimality", "used_fallback",
                "baseline_greedy", "rejected", "eligibility_trace")},
            "rationales": {
                a["artisan_id"]: {
                    "allocation": a.get("allocation_rationale", ""),
                    "payment": a.get("payment_rationale", ""),
                    "capacity_used_pct": a.get("capacity_used_pct"),
                } for a in d.get("allocations", [])
            },
        },
    )
    db.add(order)
    for al in d.get("allocations", []):
        db.add(OrderAllocation(
            allocation_id=new_id("ALLOC"), order_id=order.order_id,
            artisan_id=al["artisan_id"], allocated_units=al["allocated_units"],
            unit_price_inr=al["unit_price_inr"], unit_cost_inr=al["unit_cost_inr"],
            payment_share_inr=al["payment_share_inr"],
            proportional_share_inr=al["proportional_share_inr"],
            shapley_marginal=al["shapley_marginal_inr"], status="proposed",
        ))
    if req:
        req.status = "matched"
    result.persist(db, subject_id=order.order_id)
    db.commit()
    db.refresh(order)
    return {**_order_dict(order, db), "raw_result": d, "_meta": result.metadata()}


@router.post("/order/allocate")
def order_allocate(body: AllocateRequest, db: Session = Depends(get_db)):
    """Commit an allocation. Declined artisans trigger a re-solve over the rest."""
    order = db.get(Order, body.order_id)
    if not order:
        raise HTTPException(404, "Order not found")

    declined = set(body.declined_allocation_ids or [])
    accepted = set(body.accepted_allocation_ids or
                   [a.allocation_id for a in order.allocations if a.allocation_id not in declined])

    if declined:
        keep_artisans = [db.get(Artisan, a.artisan_id) for a in order.allocations
                         if a.allocation_id not in declined]
        pool = [EligibleArtisan(
            artisan_id=a.artisan_id, name=a.name, capacity_units=a.monthly_capacity_units,
            unit_cost_inr=next(al.unit_cost_inr for al in order.allocations if al.artisan_id == a.artisan_id),
            quality_score=a.quality_score, reliability_score=a.reliability_score,
            logistics_cost_inr_per_unit=a.logistics_cost_per_unit_inr, craft_match=True,
        ) for a in keep_artisans]
        req = db.get(BuyerRequirement, order.requirement_id) if order.requirement_id else None
        oi = BuyerOrder(
            quantity=order.total_quantity,
            unit_price_min=req.price_min if req else 200,
            unit_price_max=req.price_max if req else 260,
            fulfillment_min=req.fulfillment_min if req else 1.0,
        )
        result = allocate(oi, pool)
        d = result.data
        for al in list(order.allocations):
            db.delete(al)
        db.flush()
        for al in d.get("allocations", []):
            db.add(OrderAllocation(
                allocation_id=new_id("ALLOC"), order_id=order.order_id, artisan_id=al["artisan_id"],
                allocated_units=al["allocated_units"], unit_price_inr=al["unit_price_inr"],
                unit_cost_inr=al["unit_cost_inr"], payment_share_inr=al["payment_share_inr"],
                proportional_share_inr=al["proportional_share_inr"],
                shapley_marginal=al["shapley_marginal_inr"], status="accepted",
            ))
        order.total_allocated = d.get("total_allocated", 0)
        order.total_cost_inr = d.get("total_cost_inr", 0.0)
        order.total_buyer_payment_inr = d.get("total_buyer_payment_inr", 0.0)
        order.fulfillment_pct = d.get("fulfillment_pct", 0.0)
        order.objective_value = d.get("objective_value")
        order.solve_time_ms = d.get("solve_time_ms")
        order.solver = d.get("solver", order.solver)
        order.optimization_meta = {
            **(order.optimization_meta or {}),
            "shapley_note": d.get("shapley_note"),
            "shapley_method": d.get("shapley_method"),
            "fairness_check": d.get("fairness_check"),
            "rationales": {
                a["artisan_id"]: {
                    "allocation": a.get("allocation_rationale", ""),
                    "payment": a.get("payment_rationale", ""),
                    "capacity_used_pct": a.get("capacity_used_pct"),
                } for a in d.get("allocations", [])
            },
        }
        result.persist(db, subject_id=order.order_id)
    else:
        for al in order.allocations:
            al.status = "accepted" if al.allocation_id in accepted else "declined"

    order.status = "fully_allocated" if order.fulfillment_pct >= 100 else "partially_allocated"
    # realized demand + reliability/sales feedback (spec §8.G)
    for al in order.allocations:
        if al.status != "accepted":
            continue
        a = db.get(Artisan, al.artisan_id)
        a.verified_sales_count += 1
        a.reliability_score = min(0.99, a.reliability_score + 0.005)
        req = db.get(BuyerRequirement, order.requirement_id) if order.requirement_id else None
        if req and req.craft_id:
            craft = db.get(Craft, req.craft_id)
            db.add(DemandSignal(
                category=(craft.name if craft else "b2b").lower(), region_id=a.region_id,
                date=dt.date.today(), order_count=1, units_sold=al.allocated_units,
                browse_count=0, is_simulated=True,
            ))
    db.commit()
    db.refresh(order)
    return _order_dict(order, db)


@router.get("/orders")
def list_orders(ident: Identity | None = Depends(optional_identity), db: Session = Depends(get_db)):
    q = select(Order).order_by(Order.created_at.desc())
    if ident and ident.role == "buyer":
        q = q.where(Order.buyer_id == ident.buyer_id)
    return {"orders": [_order_dict(o, db) for o in db.scalars(q).all()]}


@router.get("/order/{order_id}")
def get_order(order_id: str, db: Session = Depends(get_db)):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return _order_dict(o, db)


@router.get("/artisan/{artisan_id}/orders")
def artisan_orders(artisan_id: str, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Order).join(OrderAllocation).where(OrderAllocation.artisan_id == artisan_id)
        .order_by(Order.created_at.desc())
    ).unique().all()
    out = []
    for o in rows:
        mine = [a for a in o.allocations if a.artisan_id == artisan_id]
        out.append({"order_id": o.order_id, "status": o.status,
                    "my_units": sum(a.allocated_units for a in mine),
                    "my_payment_inr": sum(a.payment_share_inr for a in mine),
                    "buyer_name": db.get(Buyer, o.buyer_id).name})
    return {"orders": out}
