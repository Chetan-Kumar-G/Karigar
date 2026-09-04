"""Trust & Verification API — Verified Artisan / Verified Business, reviewer
dashboard, complaints, reliability, B2B order commitment (spec add-on).

Nothing here bypasses F1–F7. It reads their outputs (F1 readiness, F2 extracted
claims + visual consistency, F3 passport / GI status) to help a reviewer decide.
"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Identity, get_db, optional_identity
from app.models import (
    Artisan, Buyer, Complaint, CraftPassport, Order, OrderAllocation, Product,
    ProductAttribute, ProductImage, TrustEvent, VerificationEvidence,
    VerificationProfile, VerificationReview,
)
from app.models.ids import new_id
from app.models.trust import (
    B2BOrderCommitment, GI_PENDING, TRUST_ACTIVE_STATES, TRUST_PENDING,
)
from app.services.trust import (
    apply_review_action, badges_for, get_or_create_profile, public_artisan_card,
    public_business_card, raise_risk_flag, recompute_reliability,
)

router = APIRouter(tags=["trust"])

_COMPLAINT_CATEGORIES = [
    "product_not_as_described", "fake_counterfeit", "wrong_material", "wrong_quantity",
    "poor_quality", "not_delivered", "repeated_cancellation", "misleading_gi_claim", "other",
]
_RISK_BY_CATEGORY = {
    "product_not_as_described": "Buyer report conflicts with the listed product claims.",
    "fake_counterfeit": "Counterfeit claim raised — craft/authenticity evidence needs re-check.",
    "wrong_material": "Reported material differs from the F2 extracted material claim.",
    "poor_quality": "Repeated quality signal against this artisan.",
    "not_delivered": "Fulfilment / delivery reliability signal.",
    "repeated_cancellation": "Cancellation-rate signal above threshold.",
    "misleading_gi_claim": "Possible misleading GI/certification claim — route to GI review.",
}
_DEFAULT_MILESTONES = [
    {"label": "Order confirmation", "pct": 20},
    {"label": "Production start", "pct": 30},
    {"label": "Production completion", "pct": 30},
    {"label": "Delivery", "pct": 20},
]
_COMMIT_FLOW = [
    "DRAFT", "BUYER_CONFIRMED", "ADVANCE_PAID", "ARTISANS_ALLOCATED",
    "PRODUCTION_STARTED", "PRODUCTION_COMPLETED", "READY_FOR_SHIPMENT",
    "SHIPPED", "DELIVERED", "COMPLETED",
]


# ── schemas ──────────────────────────────────────────────────────────────
class EvidenceSubmit(BaseModel):
    subject_type: str = "artisan"
    subject_id: str | None = None
    kind: str
    axis: str = "identity"
    label: str | None = None
    detail: dict = Field(default_factory=dict)
    note: str | None = None


class ReviewAction(BaseModel):
    action: str  # approve | request_more_evidence | reject | place_under_review | suspend | reinstate
    reviewer: str = "platform-review"
    note: str | None = None


class ComplaintCreate(BaseModel):
    subject_id: str                      # artisan_id being reported
    order_id: str | None = None
    category: str
    severity: str = "medium"
    description: str | None = None
    reported_by: str | None = None


class ComplaintResolve(BaseModel):
    resolution: str
    outcome: str = "dismissed"  # dismissed | suspend | reinstate | keep_under_review


class CommitAction(BaseModel):
    by: str = "buyer"  # buyer | artisan
    note: str | None = None


# ── public cards ─────────────────────────────────────────────────────────
@router.get("/trust/artisan/{artisan_id}")
def artisan_card(artisan_id: str, db: Session = Depends(get_db)):
    card = public_artisan_card(db, artisan_id)
    if not card:
        raise HTTPException(404, "Artisan not found")
    return card


@router.get("/trust/business/{buyer_id}")
def business_card(buyer_id: str, db: Session = Depends(get_db)):
    card = public_business_card(db, buyer_id)
    if not card:
        raise HTTPException(404, "Business not found")
    return card


# ── owner-facing verification status + onboarding evidence ───────────────
@router.get("/trust/profile/{subject_id}")
def get_profile(subject_id: str, db: Session = Depends(get_db)):
    prof = db.scalars(
        select(VerificationProfile).where(VerificationProfile.subject_id == subject_id)
    ).first()
    if not prof:
        stype = "business" if db.get(Buyer, subject_id) else "artisan"
        prof = get_or_create_profile(db, stype, subject_id)
    if prof.subject_type == "artisan":
        recompute_reliability(db, prof)
        db.commit()
    return _profile_dict(db, prof)


@router.post("/trust/verify/submit")
def submit_evidence(body: EvidenceSubmit, ident: Identity | None = Depends(optional_identity),
                    db: Session = Depends(get_db)):
    subject_id = body.subject_id or (ident.artisan_id if ident else None) or \
        (ident.buyer_id if ident else None)
    if not subject_id:
        raise HTTPException(422, "subject_id required")
    prof = get_or_create_profile(db, body.subject_type, subject_id, commit=False)
    ev = VerificationEvidence(
        profile_id=prof.profile_id, kind=body.kind, axis=body.axis,
        label=body.label or body.kind.replace("_", " ").title(),
        detail=body.detail, note=body.note, status="submitted",
        ai_assisted=body.kind in ("product_sample", "gi_document"),
    )
    db.add(ev)
    # auto-accept the low-friction checks so the prototype flow feels real
    if body.kind == "phone_otp":
        ev.status = "accepted"
        prof.identity_verified = True if body.subject_type == "artisan" else prof.identity_verified
        if body.subject_type == "business":
            prof.contact_verified = True
    db.add(TrustEvent(subject_id=subject_id, subject_type=body.subject_type,
                      event_type="evidence", summary=f"Evidence submitted: {ev.label}",
                      detail={"kind": body.kind, "axis": body.axis}))
    db.commit()
    db.refresh(prof)
    return {"submitted": True, "profile": _profile_dict(db, prof),
            "message": "Evidence received. A platform reviewer will confirm it."}


# ── reviewer dashboard ───────────────────────────────────────────────────
@router.get("/trust/reviewer/queue")
def reviewer_queue(db: Session = Depends(get_db)):
    profs = db.scalars(select(VerificationProfile)).all()
    complaints = db.scalars(
        select(Complaint).order_by(Complaint.created_at.desc())
    ).all()
    open_complaint_ids = {c.subject_id for c in complaints if c.status in ("open", "investigating")}

    def _row(p: VerificationProfile) -> dict:
        name = None
        if p.subject_type == "artisan":
            a = db.get(Artisan, p.subject_id)
            name = a.name if a else p.subject_id
        else:
            b = db.get(Buyer, p.subject_id)
            name = b.name if b else p.subject_id
        return {
            "profile_id": p.profile_id, "subject_type": p.subject_type,
            "subject_id": p.subject_id, "name": name,
            "verification_status": p.verification_status,
            "gi_status": p.gi_status,
            "reliability_score": p.reliability_score,
            "open_complaints": p.subject_id in open_complaint_ids,
            "needs_attention": p.verification_status in (TRUST_PENDING, "UNDER_REVIEW")
            or p.subject_id in open_complaint_ids,
            "is_demo": p.is_demo,
        }

    rows = [_row(p) for p in profs]
    rows.sort(key=lambda r: (not r["needs_attention"], r["name"] or ""))
    return {
        "queue": rows,
        "complaints": [_complaint_dict(c, db) for c in complaints],
        "counts": {
            "pending": sum(1 for r in rows if r["verification_status"] == TRUST_PENDING),
            "under_review": sum(1 for r in rows if r["verification_status"] == "UNDER_REVIEW"),
            "suspended": sum(1 for r in rows if r["verification_status"] == "SUSPENDED"),
            "open_complaints": sum(1 for c in complaints if c.status in ("open", "investigating")),
        },
    }


@router.get("/trust/reviewer/{profile_id}")
def reviewer_detail(profile_id: str, db: Session = Depends(get_db)):
    p = db.get(VerificationProfile, profile_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    out = _profile_dict(db, p)

    if p.subject_type == "artisan":
        a = db.get(Artisan, p.subject_id)
        recompute_reliability(db, p)
        db.commit()
        products = a.products if a else []
        prod_rows = []
        for prod in products:
            img = next((i for i in prod.images if i.is_primary), None)
            claims = [{"key": at.attribute_key, "value": at.attribute_value,
                       "source": at.source, "grounding_status": at.grounding_status,
                       "visual_consistency": at.visual_consistency}
                      for at in prod.attributes]
            ps: CraftPassport | None = prod.passport
            prod_rows.append({
                "product_id": prod.product_id, "title": prod.title, "status": prod.status,
                "f1_readiness": img.readiness_score if img else None,
                "f1_decision": img.decision if img else None,
                "image_url": (img.enhanced_url or img.url) if img else None,
                "f2_claims": claims,
                "f2_visual_consistency": (ps.visual_authenticity_status if ps else None),
                "f3_provenance_confidence": (ps.provenance_confidence if ps else None),
                "f3_gi_status": (ps.gi_status if ps else None),
            })
        my_orders = db.scalars(
            select(Order).join(OrderAllocation)
            .where(OrderAllocation.artisan_id == p.subject_id)
        ).unique().all()
        out["reviewer_view"] = {
            "region": a.region.name if a and a.region else None,
            "craft": next((prod.craft.name for prod in products if prod.craft), None),
            "products": prod_rows,
            "order_history": [{"order_id": o.order_id, "status": o.status,
                               "units": sum(al.allocated_units for al in o.allocations
                                            if al.artisan_id == p.subject_id)}
                              for o in my_orders],
            "reliability_breakdown": p.reliability_breakdown,
        }
    else:
        b = db.get(Buyer, p.subject_id)
        orders = db.scalars(select(Order).where(Order.buyer_id == p.subject_id)).all()
        out["reviewer_view"] = {
            "type": b.type if b else None,
            "order_history": [{"order_id": o.order_id, "status": o.status,
                               "quantity": o.total_quantity} for o in orders],
        }

    out["complaints"] = [
        _complaint_dict(c, db) for c in db.scalars(
            select(Complaint).where(Complaint.subject_id == p.subject_id)
            .order_by(Complaint.created_at.desc())
        ).all()
    ]
    out["timeline"] = [
        {"event_type": e.event_type, "summary": e.summary, "actor": e.actor,
         "created_at": e.created_at.isoformat() if e.created_at else None}
        for e in db.scalars(
            select(TrustEvent).where(TrustEvent.subject_id == p.subject_id)
            .order_by(TrustEvent.created_at.desc()).limit(40)
        ).all()
    ]
    return out


@router.post("/trust/reviewer/{profile_id}/action")
def reviewer_action(profile_id: str, body: ReviewAction, db: Session = Depends(get_db)):
    p = db.get(VerificationProfile, profile_id)
    if not p:
        raise HTTPException(404, "Profile not found")
    res = apply_review_action(db, p, body.action, reviewer=body.reviewer, note=body.note)
    if not res["ok"]:
        raise HTTPException(409, res["message"])
    db.refresh(p)
    return {**res, "profile": _profile_dict(db, p)}


# ── complaints ───────────────────────────────────────────────────────────
@router.get("/trust/complaints")
def list_complaints(subject_id: str | None = None, status: str | None = None,
                    db: Session = Depends(get_db)):
    q = select(Complaint).order_by(Complaint.created_at.desc())
    if subject_id:
        q = q.where(Complaint.subject_id == subject_id)
    if status:
        q = q.where(Complaint.status == status)
    return {"categories": _COMPLAINT_CATEGORIES,
            "complaints": [_complaint_dict(c, db) for c in db.scalars(q).all()]}


@router.post("/trust/complaints")
def create_complaint(body: ComplaintCreate, ident: Identity | None = Depends(optional_identity),
                     db: Session = Depends(get_db)):
    if body.category not in _COMPLAINT_CATEGORIES:
        raise HTTPException(422, f"category must be one of {_COMPLAINT_CATEGORIES}")
    if not db.get(Artisan, body.subject_id):
        raise HTTPException(404, "Artisan not found")
    reporter = body.reported_by or (ident.buyer_id if ident and ident.role == "buyer" else None) \
        or (ident.subject if ident else "BUYER-UNKNOWN")
    c = Complaint(
        complaint_id=new_id("CMP", 4), reported_by=reporter, subject_type="artisan",
        subject_id=body.subject_id, order_id=body.order_id, category=body.category,
        severity=body.severity, status="open", description=body.description,
    )
    # AI assist: attach an advisory risk flag (NOT a verdict) and move to review
    risk = _RISK_BY_CATEGORY.get(body.category)
    if risk:
        c.risk_flag = risk
    db.add(c)
    db.flush()
    db.add(TrustEvent(subject_id=body.subject_id, subject_type="artisan",
                      event_type="complaint",
                      summary=f"Complaint {c.complaint_id}: {body.category}",
                      detail={"complaint_id": c.complaint_id, "severity": body.severity}))
    flag_res = {}
    if risk:
        flag_res = raise_risk_flag(db, body.subject_id, risk, source="complaint-triage")
    db.commit()
    return {"created": True, "complaint": _complaint_dict(c, db), "risk_flag_result": flag_res}


@router.post("/trust/complaints/{complaint_id}/resolve")
def resolve_complaint(complaint_id: str, body: ComplaintResolve, db: Session = Depends(get_db)):
    c = db.get(Complaint, complaint_id)
    if not c:
        raise HTTPException(404, "Complaint not found")
    c.status = "resolved"
    c.resolution = body.resolution
    prof = db.scalars(
        select(VerificationProfile).where(VerificationProfile.subject_id == c.subject_id)
    ).first()
    action_res = None
    if prof and body.outcome in ("suspend", "reinstate"):
        action_res = apply_review_action(
            db, prof, "suspend" if body.outcome == "suspend" else "reinstate",
            reviewer="complaint-review", note=f"Complaint {complaint_id}: {body.resolution}",
        )
    db.add(TrustEvent(subject_id=c.subject_id, subject_type="artisan", event_type="complaint",
                      summary=f"Complaint {complaint_id} resolved ({body.outcome})",
                      detail={"resolution": body.resolution}))
    db.commit()
    return {"resolved": True, "complaint": _complaint_dict(c, db), "action_result": action_res}


# ── reliability ──────────────────────────────────────────────────────────
@router.get("/trust/reliability/{artisan_id}")
def reliability(artisan_id: str, db: Session = Depends(get_db)):
    if not db.get(Artisan, artisan_id):
        raise HTTPException(404, "Artisan not found")
    prof = get_or_create_profile(db, "artisan", artisan_id, commit=False)
    recompute_reliability(db, prof)
    db.commit()
    return {"artisan_id": artisan_id, "reliability_score": prof.reliability_score,
            "breakdown": prof.reliability_breakdown}


# ── B2B order commitment (simulated milestone payments + cancellation) ────
@router.get("/order/{order_id}/commitment")
def get_commitment(order_id: str, db: Session = Depends(get_db)):
    return _commitment_dict(_ensure_commitment(db, order_id), db)


@router.post("/order/{order_id}/commitment/advance")
def commitment_advance(order_id: str, db: Session = Depends(get_db)):
    cm = _ensure_commitment(db, order_id)
    if cm.commitment_status in ("DRAFT",):
        cm.commitment_status = "BUYER_CONFIRMED"
    _set_milestone(cm, "Order confirmation", "paid")
    if cm.commitment_status == "BUYER_CONFIRMED":
        cm.commitment_status = "ADVANCE_PAID"
    db.commit()
    return _commitment_dict(cm, db)


@router.post("/order/{order_id}/commitment/advance-stage")
def commitment_next_stage(order_id: str, db: Session = Depends(get_db)):
    cm = _ensure_commitment(db, order_id)
    try:
        i = _COMMIT_FLOW.index(cm.commitment_status)
        cm.commitment_status = _COMMIT_FLOW[min(i + 1, len(_COMMIT_FLOW) - 1)]
    except ValueError:
        cm.commitment_status = "BUYER_CONFIRMED"
    # release the milestone that matches the new stage
    stage_to_ms = {
        "ADVANCE_PAID": "Order confirmation",
        "PRODUCTION_STARTED": "Production start",
        "PRODUCTION_COMPLETED": "Production completion",
        "DELIVERED": "Delivery",
    }
    if cm.commitment_status in stage_to_ms:
        _set_milestone(cm, stage_to_ms[cm.commitment_status], "paid")
    cm.delivery_status = {
        "PRODUCTION_STARTED": "preparing", "PRODUCTION_COMPLETED": "consolidating",
        "READY_FOR_SHIPMENT": "consolidating", "SHIPPED": "bulk_shipped",
        "DELIVERED": "delivered", "COMPLETED": "delivered",
    }.get(cm.commitment_status, cm.delivery_status)
    db.commit()
    return _commitment_dict(cm, db)


@router.post("/order/{order_id}/commitment/cancel")
def commitment_cancel(order_id: str, body: CommitAction, db: Session = Depends(get_db)):
    cm = _ensure_commitment(db, order_id)
    order = db.get(Order, order_id)
    stage = cm.commitment_status
    before_production = stage in ("DRAFT", "BUYER_CONFIRMED", "ADVANCE_PAID", "ARTISANS_ALLOCATED")
    production_started = stage in ("PRODUCTION_STARTED",)
    completed = stage in ("PRODUCTION_COMPLETED", "READY_FOR_SHIPMENT", "SHIPPED")

    total_cost = float(order.total_cost_inr or 0) if order else 0.0
    if before_production:
        consequence = "Normal cancellation — no artisan cost committed yet."
        committed = 0.0
        retained = 0.0
    elif production_started:
        committed = round(total_cost * 0.5, 2)
        retained = round(total_cost * 0.2, 2)
        consequence = ("Production has started. Advance is retained to protect committed "
                       "artisan material and labour cost.")
    elif completed:
        committed = round(total_cost * 0.9, 2)
        retained = round(total_cost * 0.5, 2)
        consequence = ("Goods are already made. A stronger cancellation / compensation "
                       "rule applies to protect the artisans.")
    else:
        committed = total_cost
        retained = total_cost
        consequence = "Order shipped or delivered — cancellation is no longer available."

    cm.commitment_status = "CANCELLED_BY_BUYER" if body.by == "buyer" else "CANCELLED_BY_ARTISAN"
    cm.cancellation_stage = stage
    cm.artisan_committed_cost_inr = committed
    cm.advance_retained_inr = retained
    cm.tracking_note = consequence
    if order:
        order.status = "cancelled"
    db.commit()
    return {**_commitment_dict(cm, db),
            "cancellation_stage": stage,
            "artisan_committed_cost_inr": committed,
            "advance_retained_inr": retained,
            "consequence": consequence,
            "disclaimer": "Prototype Payment Flow / Simulated — not a legally enforceable "
                          "escrow. Production can connect this to a real payment provider."}


# ── helpers ──────────────────────────────────────────────────────────────
def _profile_dict(db: Session, p: VerificationProfile) -> dict:
    name = None
    if p.subject_type == "artisan":
        a = db.get(Artisan, p.subject_id)
        name = a.name if a else p.subject_id
    else:
        b = db.get(Buyer, p.subject_id)
        name = b.name if b else p.subject_id
    return {
        "profile_id": p.profile_id, "subject_type": p.subject_type,
        "subject_id": p.subject_id, "name": name,
        "verification_status": p.verification_status,
        "badges": badges_for(p),
        "identity_verified": p.identity_verified, "craft_verified": p.craft_verified,
        "product_verified": p.product_verified, "business_verified": p.business_verified,
        "contact_verified": p.contact_verified,
        "gi_status": p.gi_status, "gi_reference": p.gi_reference,
        "reliability_score": p.reliability_score,
        "reliability_breakdown": p.reliability_breakdown,
        "completed_orders": p.completed_orders, "on_time_pct": p.on_time_pct,
        "b2b_eligible": p.b2b_eligible and p.verification_status in TRUST_ACTIVE_STATES,
        "verification_date": p.verification_date, "verified_by": p.verified_by,
        "suspension_reason": p.suspension_reason,
        "is_demo": p.is_demo,
        "evidence": [{"kind": e.kind, "axis": e.axis, "label": e.label, "status": e.status,
                      "ai_assisted": e.ai_assisted, "note": e.note}
                     for e in p.evidence],
        "reviews": [{"action": r.action, "reviewer": r.reviewer, "from": r.from_status,
                     "to": r.to_status, "note": r.note,
                     "at": r.created_at.isoformat() if r.created_at else None}
                    for r in p.reviews],
    }


def _complaint_dict(c: Complaint, db: Session) -> dict:
    a = db.get(Artisan, c.subject_id)
    return {
        "complaint_id": c.complaint_id, "reported_by": c.reported_by,
        "artisan_id": c.subject_id, "artisan_name": a.name if a else c.subject_id,
        "order_id": c.order_id, "category": c.category, "severity": c.severity,
        "status": c.status, "description": c.description, "resolution": c.resolution,
        "risk_flag": c.risk_flag, "is_demo": c.is_demo,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _ensure_commitment(db: Session, order_id: str) -> B2BOrderCommitment:
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    cm = db.get(B2BOrderCommitment, order_id)
    if cm:
        return cm
    status = "ARTISANS_ALLOCATED" if order.allocations else "BUYER_CONFIRMED"
    cm = B2BOrderCommitment(
        order_id=order_id, commitment_status=status, delivery_status="not_started",
        payment_milestones=[
            {**m, "status": "pending",
             "amount_inr": round(float(order.total_buyer_payment_inr or 0) * m["pct"] / 100)}
            for m in _DEFAULT_MILESTONES
        ],
    )
    db.add(cm)
    db.commit()
    db.refresh(cm)
    return cm


def _set_milestone(cm: B2BOrderCommitment, label: str, status: str) -> None:
    ms = list(cm.payment_milestones or [])
    for m in ms:
        if m.get("label") == label:
            m["status"] = status
    cm.payment_milestones = ms


def _commitment_dict(cm: B2BOrderCommitment, db: Session) -> dict:
    order = db.get(Order, cm.order_id)
    paid = sum(m.get("amount_inr", 0) for m in (cm.payment_milestones or [])
               if m.get("status") == "paid")
    return {
        "order_id": cm.order_id,
        "commitment_status": cm.commitment_status,
        "commitment_flow": _COMMIT_FLOW,
        "delivery_status": cm.delivery_status,
        "payment_milestones": cm.payment_milestones,
        "paid_inr": paid,
        "total_buyer_payment_inr": round(float(order.total_buyer_payment_inr or 0)) if order else 0,
        "cancellation_stage": cm.cancellation_stage,
        "artisan_committed_cost_inr": cm.artisan_committed_cost_inr,
        "advance_retained_inr": cm.advance_retained_inr,
        "tracking_note": cm.tracking_note,
        "is_simulated": cm.is_simulated,
        "disclaimer": "Prototype Payment Flow / Simulated. Milestones: 20% confirm · 30% "
                      "production start · 30% completion · 20% delivery.",
    }
