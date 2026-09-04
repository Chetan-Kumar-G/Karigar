"""F3 — Craft Knowledge Graph + Digital Craft Passport.

**Mode: REAL.**  The graph is the relational schema in ``models/geo_craft.py``;
"related crafts" are found with a genuine **recursive CTE** over
``craft_relation`` (works on both SQLite and Postgres — spec §13/§33).  Entity
resolution maps colloquial voice terms onto canonical KG nodes with
``difflib`` ratio + token overlap.

Passport ``provenance_confidence`` is spec §5.I verbatim::

    0.40·GovSourceVerified + 0.25·GroundingGuardPass
  + 0.20·VisualConsistencyScore + 0.15·ArtisanSelfReportConsistency
"""
from __future__ import annotations

import difflib

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.ai.base import REAL, AiResult, timed
from app.models.geo_craft import Craft, Material, Region, Technique
from app.models.ids import new_id
from app.models.passport import Certification, CraftPassport


# ── entity resolution ───────────────────────────────────────────────────
def _best_match(value: str, options: list[tuple[str, str]]) -> tuple[str | None, float]:
    """options = [(id, name)]; returns (id, score 0..1)."""
    if not value:
        return None, 0.0
    v = value.strip().lower()
    best_id, best = None, 0.0
    for oid, name in options:
        n = name.lower()
        ratio = difflib.SequenceMatcher(None, v, n).ratio()
        tok = len(set(v.split()) & set(n.split())) / max(len(set(v.split()) | set(n.split())), 1)
        score = max(ratio, 0.5 * ratio + 0.5 * tok)
        if v in n or n in v:
            score = max(score, 0.9)
        if score > best:
            best_id, best = oid, score
    return best_id, round(best, 3)


def resolve(db: Session, *, craft: str | None = None, technique: str | None = None,
            material: str | None = None, region: str | None = None) -> dict:
    out: dict = {}
    if craft is not None:
        opts = [(c.craft_id, c.name) for c in db.scalars(select(Craft)).all()]
        cid, sc = _best_match(craft, opts)
        out["craft"] = {"id": cid, "score": sc, "input": craft}
    if technique is not None:
        opts = [(t.technique_id, t.name) for t in db.scalars(select(Technique)).all()]
        tid, sc = _best_match(technique, opts)
        out["technique"] = {"id": tid, "score": sc, "input": technique}
    if material is not None:
        opts = [(m.material_id, m.name) for m in db.scalars(select(Material)).all()]
        mid, sc = _best_match(material, opts)
        out["material"] = {"id": mid, "score": sc, "input": material}
    if region is not None:
        opts = [(r.region_id, f"{r.name} {r.state}") for r in db.scalars(select(Region)).all()]
        rid, sc = _best_match(region, opts)
        out["region"] = {"id": rid, "score": sc, "input": region}
    return out


# ── graph queries ──────────────────────────────────────────────────────
_RELATED_CTE = text(
    """
    WITH RECURSIVE walk(craft_id, depth) AS (
        SELECT :root, 0
        UNION
        SELECT cr.dst_craft_id, walk.depth + 1
        FROM craft_relation cr
        JOIN walk ON cr.src_craft_id = walk.craft_id
        WHERE walk.depth < 2
    )
    SELECT DISTINCT craft_id FROM walk WHERE craft_id <> :root
    """
)


def related_crafts(db: Session, craft_id: str, limit: int = 6) -> list[dict]:
    rows = db.execute(_RELATED_CTE, {"root": craft_id}).fetchall()
    ids = [r[0] for r in rows][:limit]
    if not ids:
        return []
    crafts = db.scalars(select(Craft).where(Craft.craft_id.in_(ids))).all()
    return [{"craft_id": c.craft_id, "name": c.name, "region": c.region.name if c.region else None}
            for c in crafts]


def craft_node(db: Session, craft_id: str) -> dict | None:
    c = db.get(Craft, craft_id)
    if not c:
        return None
    return {
        "craft_id": c.craft_id,
        "name": c.name,
        "description": c.description,
        "heritage_note": c.heritage_note,
        "rarity_score": c.rarity_score,
        "gi_status": c.gi_status,
        "gi_reference": c.gi_reference,
        "odop_cluster": c.odop_cluster,
        "region": {"id": c.region.region_id, "name": c.region.name, "state": c.region.state}
        if c.region else None,
        "techniques": [{"id": t.technique_id, "name": t.name, "description": t.description}
                       for t in c.techniques],
        "materials": [{"id": m.material_id, "name": m.name} for m in c.materials],
        "related_crafts": related_crafts(db, craft_id),
    }


# ── passport construction ──────────────────────────────────────────────
def build_passport(
    db: Session,
    product,
    *,
    grounding_pass_ratio: float = 0.5,
    visual_consistency_score: float = 0.5,
    self_report_consistency: float = 0.7,
) -> AiResult:
    with timed() as t:
        craft = db.get(Craft, product.craft_id) if product.craft_id else None
        gov_verified = 0.0
        if craft:
            gov_verified = {"registered": 1.0, "pending": 0.55, "unregistered": 0.15}.get(
                craft.gi_status, 0.15
            )
            if craft.odop_cluster:
                gov_verified = min(1.0, gov_verified + 0.25)

        confidence = (
            0.40 * gov_verified
            + 0.25 * float(min(max(grounding_pass_ratio, 0), 1))
            + 0.20 * float(min(max(visual_consistency_score, 0), 1))
            + 0.15 * float(min(max(self_report_consistency, 0), 1))
        )
        breakdown = {
            "gov_source_verified": round(gov_verified, 3),
            "grounding_guard_pass": round(grounding_pass_ratio, 3),
            "visual_consistency_score": round(visual_consistency_score, 3),
            "artisan_self_report_consistency": round(self_report_consistency, 3),
            "weights": {"gov": 0.40, "grounding": 0.25, "visual": 0.20, "self_report": 0.15},
        }

        vstatus = (
            "contradiction_under_review" if visual_consistency_score < 0.35
            else "entailment" if visual_consistency_score > 0.7
            else "neutral"
        )

        passport = product.passport or CraftPassport(
            passport_id=new_id("CP"), product_id=product.product_id
        )
        passport.craft_id = product.craft_id
        passport.technique_id = craft.techniques[0].technique_id if craft and craft.techniques else None
        passport.region_id = craft.region_id if craft else product.artisan.region_id
        passport.artisan_id = product.artisan_id
        passport.material_ids = [m.material_id for m in craft.materials] if craft else []
        passport.gi_status = craft.gi_status if craft else "unregistered"
        passport.gi_reference = craft.gi_reference if craft else None
        passport.odop_cluster = craft.odop_cluster if craft else None
        passport.provenance_confidence = round(confidence, 3)
        passport.confidence_breakdown = breakdown
        passport.visual_authenticity_status = vstatus
        passport.related_craft_ids = [r["craft_id"] for r in related_crafts(db, product.craft_id)] \
            if product.craft_id else []
        passport.story_snippet_en = _story(craft, product, "en")
        passport.story_snippet_hi = _story(craft, product, "hi")

        if passport.passport_id and not product.passport:
            db.add(passport)
            if craft and craft.gi_status in ("registered", "pending"):
                db.add(Certification(
                    certification_id=new_id("CERT"), passport_id=passport.passport_id,
                    type="GI", status="sample_record",
                    label="Sample Verification Record (demo data — not a real GI certificate)",
                    issued_note=f"Demo record linked to craft {craft.name}.",
                ))
        db.flush()

        data = {
            "passport_id": passport.passport_id,
            "provenance_confidence": passport.provenance_confidence,
            "confidence_breakdown": breakdown,
            "visual_authenticity_status": vstatus,
            "gi_status": passport.gi_status,
            "odop_cluster": passport.odop_cluster,
            "related_craft_ids": passport.related_craft_ids,
        }
    return AiResult(
        data=data, feature="F3",
        model="Relational craft graph + recursive-CTE traversal + spec-§5.I confidence formula",
        mode=REAL,
        inputs={"product_id": product.product_id, "craft_id": product.craft_id or "",
                "grounding_pass_ratio": grounding_pass_ratio,
                "visual_consistency_score": visual_consistency_score},
        latency_ms=t["ms"],
    )


def _story(craft, product, lang: str) -> str:
    if not craft:
        return ("यह वस्तु एक कारीगर द्वारा हाथ से बनाई गई है।" if lang == "hi"
                else "This piece is handmade by an independent artisan.")
    if lang == "hi":
        return (
            f"{craft.name} की परंपरा {craft.region.name if craft.region else 'भारत'} से आती है। "
            f"यह वस्तु उसी विरासत तकनीक से बनाई गई है।"
        )
    note = craft.heritage_note or f"{craft.name} is a traditional craft of {craft.region.name if craft.region else 'India'}."
    return f"{note} This piece continues that lineage, handmade by {product.artisan.name}."
