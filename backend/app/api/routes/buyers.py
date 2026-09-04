"""Buyer directory + B2B requirement CRUD (spec §6, §12)."""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Identity, get_db, optional_identity
from app.models import Buyer, BuyerRequirement, Craft
from app.models.ids import new_id
from app.schemas.models import RequirementCreate

router = APIRouter(tags=["buyers"])


def _req_dict(r: BuyerRequirement, db: Session) -> dict:
    craft = db.get(Craft, r.craft_id) if r.craft_id else None
    buyer = db.get(Buyer, r.buyer_id)
    return {
        "requirement_id": r.requirement_id, "title": r.title,
        "buyer_id": r.buyer_id, "buyer_name": buyer.name if buyer else None,
        "buyer_type": buyer.type if buyer else None,
        "craft_id": r.craft_id, "craft_name": craft.name if craft else None,
        "required_material": r.required_material, "quantity": r.quantity,
        "price_min": r.price_min, "price_max": r.price_max,
        "deadline": r.deadline.isoformat() if r.deadline else None,
        "days_left": (r.deadline - dt.date.today()).days if r.deadline else None,
        "fulfillment_min": r.fulfillment_min, "status": r.status,
        "notes": r.notes, "is_demo": r.is_demo,
    }


@router.get("/buyers")
def list_buyers(db: Session = Depends(get_db)):
    return {"buyers": [{"buyer_id": b.buyer_id, "name": b.name, "type": b.type,
                        "verified": b.verified, "note": b.contact_note}
                       for b in db.scalars(select(Buyer)).all()]}


@router.get("/requirements")
def list_requirements(db: Session = Depends(get_db)):
    rows = db.scalars(select(BuyerRequirement).order_by(BuyerRequirement.created_at.desc())).all()
    return {"requirements": [_req_dict(r, db) for r in rows]}


@router.get("/requirement/{requirement_id}")
def get_requirement(requirement_id: str, db: Session = Depends(get_db)):
    r = db.get(BuyerRequirement, requirement_id)
    if not r:
        raise HTTPException(404, "Requirement not found")
    return _req_dict(r, db)


@router.post("/requirements")
def create_requirement(
    body: RequirementCreate,
    ident: Identity | None = Depends(optional_identity),
    db: Session = Depends(get_db),
):
    buyer_id = body.buyer_id or (ident.buyer_id if ident and ident.role == "buyer" else None)
    if not buyer_id:
        buyer_id = db.scalars(select(Buyer)).first().buyer_id
    if not db.get(Buyer, buyer_id):
        raise HTTPException(404, "Buyer not found")
    if body.price_max < body.price_min:
        raise HTTPException(422, "price_max must be >= price_min")

    r = BuyerRequirement(
        requirement_id=new_id("REQ", 5), buyer_id=buyer_id, title=body.title,
        craft_id=body.craft_id, required_material=body.required_material,
        quantity=body.quantity, price_min=body.price_min, price_max=body.price_max,
        deadline=body.deadline or (dt.date.today() + dt.timedelta(days=45)),
        fulfillment_min=body.fulfillment_min, notes=body.notes, status="open",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return _req_dict(r, db)
