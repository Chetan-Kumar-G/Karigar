"""F2 — Multilingual Grounded Auto-Cataloger endpoint (spec §12)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.f2_catalog.asr import asr_status
from app.ai.f2_catalog.cataloger import generate_catalog
from app.ai.f2_catalog.claims import HEADLINE, NEEDS_HUMAN_REVIEW, summarize
from app.ai.f2_catalog.vision import extract_dominant_colors
from app.ai.f3_graph.graph import build_passport
from app.api.deps import get_db
from app.core.config import UPLOAD_DIR, settings
from app.core.logging import get_logger
from app.models import Product, ProductAttribute
from app.schemas.models import CatalogClaimsBlock, CatalogRequest

log = get_logger("f2.catalog")
router = APIRouter(tags=["catalog"])

# claim status -> the grounding_status we persist on ProductAttribute
_CLAIM_TO_GROUNDING = {
    "SUPPORTED": "supported",
    "VISUALLY_CONSISTENT": "visually_consistent",
    "CONTRADICTED": "contradicted",
    "UNKNOWN": "unknown",
    "NEEDS_HUMAN_REVIEW": "needs_human_review",
}


def _primary_image_bytes(p: Product) -> bytes | None:
    """Load the product's primary photo from disk so F2 can colour-check claims."""
    img = next((i for i in p.images if i.is_primary), p.images[0] if p.images else None)
    if not img:
        return None
    src = img.url or img.enhanced_url or ""
    fp = UPLOAD_DIR / Path(src).name
    try:
        return fp.read_bytes() if fp.is_file() else None
    except OSError:
        return None


def _validate_claims(data: dict) -> None:
    """Backend contract check before the block is sent to Flutter (spec §21).

    On a schema violation we do NOT 500 the whole catalog — we replace the block
    with a single NEEDS_HUMAN_REVIEW claim and log the technical detail."""
    try:
        CatalogClaimsBlock(claims=data.get("claims", []),
                           verification_summary=data.get("verification_summary", {}))
    except ValidationError as exc:
        log.error("F2 claim block failed validation: %s", exc)
        fallback = [{
            "claim": "Artisan claims could not be assessed automatically",
            "attribute": "all",
            "status": NEEDS_HUMAN_REVIEW,
            "confidence": 0.0,
            "evidence": "The automated consistency check produced an invalid result; "
                        "a human reviewer must assess these claims.",
            "checkable": False,
        }]
        data["claims"] = fallback
        data["verification_summary"] = {**summarize(fallback), "headline": HEADLINE,
                                        "validation_error": True}


@router.get("/catalog/asr-status")
def catalog_asr_status():
    """Whether real speech-to-text is available on this server (Phase 5)."""
    return asr_status()


def _apply_to_product(db: Session, product_id: str, data: dict) -> None:
    p = db.get(Product, product_id)
    if not p:
        return
    p.description_en = data["description_en"]
    p.description_hi = data["description_hi"]
    p.seo_title = data["seo_title"]
    p.seo_keywords = data["seo_keywords"]
    if data.get("resolved_craft_id") and not p.craft_id:
        p.craft_id = data["resolved_craft_id"]
    ea = data["extracted_attributes"]
    grounding = data["grounding_check"]
    visual = data["visual_consistency_check"]
    # canonical claim status per attribute (Phase: F2 claim-consistency)
    claim_by_attr = {c["attribute"]: c for c in data.get("claims", [])}
    keep = {a.attribute_key: a for a in p.attributes if a.source not in ("voice", "visual")}
    p.attributes[:] = list(keep.values())
    for key in ("material", "technique", "region_claimed"):
        val = ea.get(key)
        if not val:
            continue
        attr_name = key.replace("_claimed", "")
        claim = claim_by_attr.get("region" if key == "region_claimed" else attr_name)
        gstatus = (_CLAIM_TO_GROUNDING.get(claim["status"]) if claim
                   else grounding.get(key, "unverified"))
        p.attributes.append(ProductAttribute(
            product_id=product_id, attribute_key=attr_name,
            attribute_value=str(val), source="voice",
            grounding_status=gstatus,
            visual_consistency=(claim["status"] if claim
                                else (visual.get(key) or {}).get("label")),
            confidence=(claim["confidence"] if claim else data.get("confidence")),
        ))
    if ea.get("colors"):
        p.attributes.append(ProductAttribute(
            product_id=product_id, attribute_key="colors",
            attribute_value=", ".join(ea["colors"]), source="visual",
            grounding_status="visual", confidence=0.7))
    if p.status in ("draft", "analyzing"):
        p.status = "catalogued"
    db.flush()
    build_passport(
        db, p,
        grounding_pass_ratio=data["grounding_pass_ratio"],
        visual_consistency_score=data["visual_consistency_score"],
        self_report_consistency=0.75,
    )


@router.post("/catalog/generate")
async def catalog_generate(
    voice_note: UploadFile | None = File(default=None),
    payload: str | None = Form(default=None),
    typed_transcript: str | None = Form(default=None),
    language_hint: str | None = Form(default="hi"),
    craft_id: str | None = Form(default=None),
    product_id: str | None = Form(default=None),
    visual_context: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    """Accepts multipart (voice_note + fields) OR a JSON ``payload`` field."""
    body = CatalogRequest()
    if payload:
        try:
            body = CatalogRequest(**json.loads(payload))
        except Exception as exc:
            raise HTTPException(422, f"Bad payload JSON: {exc}")
    body.typed_transcript = typed_transcript or body.typed_transcript
    body.language_hint = language_hint or body.language_hint
    body.craft_id = craft_id or body.craft_id
    body.product_id = product_id or body.product_id
    if visual_context:
        try:
            body.visual_context = json.loads(visual_context)
        except Exception:
            pass

    audio = None
    if voice_note is not None:
        if (voice_note.content_type or "").split(";")[0] not in settings.allowed_audio_types:
            raise HTTPException(415, f"Unsupported audio type: {voice_note.content_type}")
        audio = await voice_note.read()
        if len(audio) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, "Audio too large")

    if not audio and not body.typed_transcript:
        # graceful: fall through to the deterministic demo transcript
        pass

    # Cross-modal colour evidence: if the caller did not supply detected colours,
    # read them from the product's own primary photo so colour claims can be
    # scored against real pixels rather than against nothing.
    vc = dict(body.visual_context or {})
    if not vc.get("detected_colors") and body.product_id:
        _p = db.get(Product, body.product_id)
        img_bytes = _primary_image_bytes(_p) if _p else None
        if img_bytes:
            try:
                vc["detected_colors"] = extract_dominant_colors(img_bytes)
                vc.setdefault("segmentation_present", True)
                vc["color_source"] = "product_primary_photo"
            except Exception as exc:  # never let a colour read break cataloguing
                log.warning("dominant-colour read failed: %s", exc)
    body.visual_context = vc

    try:
        result = generate_catalog(
            db, audio_bytes=audio, typed_transcript=body.typed_transcript,
            language_hint=body.language_hint, visual_context=body.visual_context,
            craft_id=body.craft_id,
            audio_filename=(voice_note.filename if voice_note is not None else None),
        )
    except Exception as exc:
        raise HTTPException(500, f"Catalog generation failed: {exc}")

    _validate_claims(result.data)

    if body.product_id:
        _apply_to_product(db, body.product_id, result.data)
        result.persist(db, subject_id=body.product_id)
    db.commit()
    return {**result.data, "_meta": result.metadata()}
