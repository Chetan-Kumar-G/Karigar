"""F3 — Craft Knowledge Graph node + Digital Craft Passport (spec §12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.f3_graph.graph import build_passport, craft_node
from app.api.deps import get_db
from app.models import Craft, Material, Product, Region

router = APIRouter(tags=["craft"])


@router.get("/crafts")
def list_crafts(db: Session = Depends(get_db)):
    return {"crafts": [craft_node(db, c.craft_id)
                       for c in db.scalars(select(Craft).order_by(Craft.name)).all()]}


@router.get("/craft/{craft_id}")
def get_craft(craft_id: str, db: Session = Depends(get_db)):
    node = craft_node(db, craft_id)
    if not node:
        raise HTTPException(404, "Craft not found")
    return node


@router.get("/passport/{product_id}")
def get_passport(product_id: str, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    if not p.passport:
        build_passport(db, p)
        db.commit()
        db.refresh(p)
    ps = p.passport
    craft = db.get(Craft, ps.craft_id) if ps.craft_id else None
    region = db.get(Region, ps.region_id) if ps.region_id else None
    mats = db.scalars(select(Material).where(Material.material_id.in_(ps.material_ids or []))).all()
    related = [craft_node(db, cid) for cid in (ps.related_craft_ids or [])]
    return {
        "passport_id": ps.passport_id,
        "product_id": ps.product_id,
        "product_title": p.title,
        "craft": {"id": craft.craft_id, "name": craft.name} if craft else None,
        "technique": next(({"id": t.technique_id, "name": t.name}
                           for t in (craft.techniques if craft else []) if t.technique_id == ps.technique_id),
                          None),
        "materials": [{"id": m.material_id, "name": m.name} for m in mats],
        "region": {"id": region.region_id, "name": region.name, "state": region.state}
        if region else None,
        "artisan": {"id": p.artisan.artisan_id, "name": p.artisan.name,
                    "kyc_status": p.artisan.kyc_status} if p.artisan else None,
        "gi_status": ps.gi_status,
        "gi_reference": ps.gi_reference,
        "odop_cluster": ps.odop_cluster,
        "provenance_confidence": ps.provenance_confidence,
        "confidence_breakdown": ps.confidence_breakdown,
        "visual_authenticity_status": ps.visual_authenticity_status,
        "story_snippet_en": ps.story_snippet_en,
        "story_snippet_hi": ps.story_snippet_hi,
        "heritage_note": craft.heritage_note if craft else None,
        "related_crafts": [{"craft_id": r["craft_id"], "name": r["name"],
                            "region": r["region"]} for r in related if r],
        "certifications": [{"type": c.type, "status": c.status, "label": c.label,
                            "note": c.issued_note} for c in ps.certifications],
        "disclaimer": "Certification entries shown here are Sample Verification Records "
                      "(demo data), not real government GI certificates.",
    }
