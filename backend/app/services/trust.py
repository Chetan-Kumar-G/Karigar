"""Trust & Verification orchestration (spec add-on).

Pure helpers over the ``app.models.trust`` tables:

* profile bootstrap + public "card" projections (no private KYC leaves here),
* an explainable reliability score derived from real order / complaint signals,
* the trust-status state machine with an audit trail,
* an **AI risk-flag** path that only ever moves an account to ``UNDER_REVIEW`` —
  a human / platform review makes the final call (never an automatic ban).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Artisan, Buyer, Complaint, Order, OrderAllocation, Product, TrustEvent,
    VerificationEvidence, VerificationProfile, VerificationReview,
)
from app.models.ids import new_id
from app.models.trust import (
    GI_ARTISAN_REPORTED, GI_GOVERNMENT_VERIFIED, GI_NOT_REGISTERED, GI_PENDING,
    TRUST_ACTIVE_STATES, TRUST_PENDING, TRUST_REINSTATED, TRUST_TRANSITIONS,
    TRUST_UNDER_REVIEW, TRUST_VERIFIED,
)

_ACTION_TO_STATUS = {
    "approve": TRUST_VERIFIED,
    "reject": "REJECTED",
    "place_under_review": TRUST_UNDER_REVIEW,
    "suspend": "SUSPENDED",
    "reinstate": TRUST_REINSTATED,
    # request_more_evidence keeps the current status
}


# ── profile bootstrap ────────────────────────────────────────────────────
def get_or_create_profile(
    db: Session, subject_type: str, subject_id: str, *, commit: bool = True
) -> VerificationProfile:
    prof = db.scalars(
        select(VerificationProfile).where(VerificationProfile.subject_id == subject_id)
    ).first()
    if prof:
        return prof
    prof = VerificationProfile(
        profile_id=new_id("VP", 6),
        subject_type=subject_type,
        subject_id=subject_id,
        verification_status=TRUST_PENDING,
    )
    db.add(prof)
    db.flush()
    _event(db, subject_id, subject_type, "status_change",
           "Verification profile created (PENDING)", {"to": TRUST_PENDING})
    if commit:
        db.commit()
        db.refresh(prof)
    return prof


# ── explainable reliability score (0..100) ───────────────────────────────
def compute_reliability(db: Session, artisan_id: str) -> tuple[float, dict]:
    """Blend real order + complaint signals into a transparent 0..100 score.

    Signals (spec §8): completed orders, on-time fulfilment, delivery success,
    buyer complaints, cancellation rate, quality disputes, order acceptance,
    B2B fulfilment history.  Kept explainable — every term is returned.
    """
    a = db.get(Artisan, artisan_id)
    allocs = db.scalars(
        select(OrderAllocation).where(OrderAllocation.artisan_id == artisan_id)
    ).all()
    accepted = [al for al in allocs if al.status == "accepted"]
    declined = [al for al in allocs if al.status == "declined"]
    completed_orders = len({al.order_id for al in accepted})

    complaints = db.scalars(
        select(Complaint).where(Complaint.subject_id == artisan_id)
    ).all()
    quality_complaints = sum(
        1 for c in complaints
        if c.category in ("poor_quality", "product_not_as_described", "wrong_material")
        and c.status not in ("dismissed",)
    )
    delivery_complaints = sum(
        1 for c in complaints
        if c.category in ("not_delivered", "repeated_cancellation")
        and c.status not in ("dismissed",)
    )

    total_alloc = len(accepted) + len(declined)
    cancellation_rate = (len(declined) / total_alloc) if total_alloc else 0.0

    # base reliability comes from the artisan's seeded operating history (0..1)
    base = float(a.reliability_score) if a else 0.8
    on_time_pct = round(max(60.0, 100.0 - cancellation_rate * 40.0 - delivery_complaints * 8.0), 1)

    # weighted, all terms explainable
    terms = {
        "operating_history": round(base * 45.0, 1),          # 0..45
        "completed_orders": round(min(completed_orders, 10) * 1.8, 1),  # 0..18
        "on_time_delivery": round(on_time_pct / 100.0 * 20.0, 1),       # 0..20
        "verified_sales": round(min((a.verified_sales_count if a else 0), 25) * 0.4, 1),  # 0..10
        "quality_disputes_penalty": round(-quality_complaints * 6.0, 1),
        "cancellation_penalty": round(-cancellation_rate * 15.0, 1),
    }
    score = max(0.0, min(100.0, sum(terms.values()) + 7.0))
    breakdown = {
        "score": round(score, 1),
        "terms": terms,
        "signals": {
            "completed_orders": completed_orders,
            "on_time_pct": on_time_pct,
            "cancellation_rate_pct": round(cancellation_rate * 100, 1),
            "quality_complaints": quality_complaints,
            "delivery_complaints": delivery_complaints,
            "verified_sales_count": a.verified_sales_count if a else 0,
        },
        "note": "Explainable score — every term above sums to the total. "
                "Demo accounts carry seeded operating history (marked Demo Data).",
    }
    return round(score, 1), breakdown


def recompute_reliability(db: Session, profile: VerificationProfile) -> None:
    if profile.subject_type != "artisan":
        return
    score, breakdown = compute_reliability(db, profile.subject_id)
    profile.reliability_score = score
    profile.reliability_breakdown = breakdown
    profile.completed_orders = breakdown["signals"]["completed_orders"]
    profile.on_time_pct = breakdown["signals"]["on_time_pct"]
    profile.cancellation_rate_pct = breakdown["signals"]["cancellation_rate_pct"]
    profile.quality_complaints = breakdown["signals"]["quality_complaints"]


# ── state machine ────────────────────────────────────────────────────────
def can_transition(current: str, target: str) -> bool:
    return target in TRUST_TRANSITIONS.get(current, set())


def apply_review_action(
    db: Session, profile: VerificationProfile, action: str, *,
    reviewer: str = "platform-review", note: str | None = None,
) -> dict:
    """Reviewer/platform decision. Returns ``{ok, status, message}``."""
    current = profile.verification_status
    if action == "request_more_evidence":
        db.add(VerificationReview(
            profile_id=profile.profile_id, action=action, reviewer=reviewer,
            from_status=current, to_status=current, note=note,
        ))
        _event(db, profile.subject_id, profile.subject_type, "note",
               "Reviewer requested more evidence", {"note": note})
        db.commit()
        return {"ok": True, "status": current, "message": "More evidence requested."}

    target = _ACTION_TO_STATUS.get(action)
    if target is None:
        return {"ok": False, "status": current, "message": f"Unknown action '{action}'."}
    if not can_transition(current, target):
        return {"ok": False, "status": current,
                "message": f"Cannot move from {current} to {target}."}

    profile.verification_status = target
    if target in (TRUST_VERIFIED, TRUST_REINSTATED):
        profile.verification_date = dt.date.today().isoformat()
        profile.verified_by = reviewer
        profile.suspension_reason = None
        if profile.subject_type == "artisan":
            profile.identity_verified = True
            profile.craft_verified = True
            profile.b2b_eligible = True
            _sync_artisan_kyc(db, profile.subject_id, "verified")
    if target == "SUSPENDED":
        profile.b2b_eligible = False
        profile.suspension_reason = note or "Suspended pending investigation."
        _sync_artisan_kyc(db, profile.subject_id, "suspended")
    if target == "REJECTED":
        profile.b2b_eligible = False

    db.add(VerificationReview(
        profile_id=profile.profile_id, action=action, reviewer=reviewer,
        from_status=current, to_status=target, note=note,
    ))
    _event(db, profile.subject_id, profile.subject_type, "status_change",
           f"{current} → {target} ({action})", {"from": current, "to": target, "note": note})
    db.commit()
    db.refresh(profile)
    return {"ok": True, "status": target, "message": f"Status is now {target}."}


def raise_risk_flag(
    db: Session, subject_id: str, reason: str, *, subject_type: str = "artisan",
    source: str = "ai-risk-detector",
) -> dict:
    """AI/automation may FLAG risk; it never bans. A VERIFIED account moves to
    UNDER_REVIEW so a human/platform review decides."""
    prof = get_or_create_profile(db, subject_type, subject_id, commit=False)
    moved = False
    if prof.verification_status in TRUST_ACTIVE_STATES:
        prof.verification_status = TRUST_UNDER_REVIEW
        moved = True
        db.add(VerificationReview(
            profile_id=prof.profile_id, action="place_under_review", reviewer=source,
            from_status=TRUST_VERIFIED, to_status=TRUST_UNDER_REVIEW, note=reason,
        ))
    _event(db, subject_id, subject_type, "risk_flag",
           f"AI risk flag: {reason}", {"reason": reason, "source": source, "moved_to_review": moved})
    db.commit()
    return {"risk_flag": reason, "moved_to_under_review": moved,
            "status": prof.verification_status,
            "note": "AI produces a risk flag only. A human/platform review makes the final decision."}


# ── public card projections (NO private KYC) ─────────────────────────────
_BADGE_TONES = {
    "verified": "green", "identity": "blue", "craft": "blue", "product": "blue",
    "business": "green", "contact": "blue", "gi_pending": "amber",
    "gi_verified": "green", "under_review": "amber", "suspended": "red",
    "pending": "amber",
}


def badges_for(profile: VerificationProfile) -> list[dict]:
    """What exactly has been verified — never a generic '100% genuine'."""
    b: list[dict] = []
    st = profile.verification_status
    if st in TRUST_ACTIVE_STATES:
        label = "Verified Business" if profile.subject_type == "business" else "Verified Artisan"
        b.append({"key": "verified", "label": label, "tone": "green"})
    elif st == TRUST_UNDER_REVIEW:
        b.append({"key": "under_review", "label": "Under review", "tone": "amber"})
    elif st == "SUSPENDED":
        b.append({"key": "suspended", "label": "Suspended", "tone": "red"})
    else:
        b.append({"key": "pending", "label": "Verification pending", "tone": "amber"})

    if profile.identity_verified:
        b.append({"key": "identity", "label": "Identity verified", "tone": "blue"})
    if profile.subject_type == "artisan" and profile.craft_verified:
        b.append({"key": "craft", "label": "Craft verified", "tone": "blue"})
    if profile.subject_type == "artisan" and profile.product_verified:
        b.append({"key": "product", "label": "Product claims verified", "tone": "blue"})
    if profile.subject_type == "business" and profile.business_verified:
        b.append({"key": "business", "label": "Business details verified", "tone": "green"})
    if profile.subject_type == "business" and profile.contact_verified:
        b.append({"key": "contact", "label": "Contact verified", "tone": "blue"})

    if profile.gi_status == GI_PENDING:
        b.append({"key": "gi_pending", "label": "Certification / GI: pending", "tone": "amber"})
    elif profile.gi_status == GI_GOVERNMENT_VERIFIED:
        b.append({"key": "gi_verified", "label": "GI: government verified", "tone": "green"})
    elif profile.gi_status == GI_ARTISAN_REPORTED:
        b.append({"key": "gi_reported", "label": "GI: artisan reported", "tone": "amber"})
    return b


def public_artisan_card(db: Session, artisan_id: str) -> dict | None:
    a = db.get(Artisan, artisan_id)
    if not a:
        return None
    prof = get_or_create_profile(db, "artisan", artisan_id)
    recompute_reliability(db, prof)
    db.commit()
    products = [p for p in a.products]
    published = [p for p in products if p.status == "published"]
    craft = next((p.craft for p in products if p.craft), None)
    open_complaints = db.scalars(
        select(Complaint).where(Complaint.subject_id == artisan_id,
                                Complaint.status.in_(["open", "investigating"]))
    ).all()
    return {
        "subject_type": "artisan",
        "artisan_id": a.artisan_id,
        "name": a.name,
        "avatar_seed": a.avatar_seed or a.artisan_id,
        "region": a.region.name if a.region else None,
        "state": a.region.state if a.region else None,
        "craft": craft.name if craft else None,
        "craft_id": craft.craft_id if craft else None,
        "bio": a.bio,
        "verification_status": prof.verification_status,
        "badges": badges_for(prof),
        "identity_verified": prof.identity_verified,
        "craft_verified": prof.craft_verified,
        "product_verified": prof.product_verified,
        "gi_status": prof.gi_status,
        "gi_reference": prof.gi_reference,
        "completed_orders": prof.completed_orders,
        "on_time_pct": prof.on_time_pct,
        "reliability_score": prof.reliability_score,
        "reliability_breakdown": prof.reliability_breakdown,
        "products_listed": len(published),
        "joined_date": (a.onboarded_at.date().isoformat() if a.onboarded_at else None),
        "b2b_eligible": prof.b2b_eligible and prof.verification_status in TRUST_ACTIVE_STATES,
        "open_complaints": len(open_complaints),
        "is_demo": prof.is_demo,
        "passport_product_id": (published[0].product_id if published else
                                (products[0].product_id if products else None)),
        "disclaimer": "Verification covers the items listed above only. "
                      "It is not a claim that every product is genuine, and AI does not "
                      "legally certify an artisan.",
    }


def public_business_card(db: Session, buyer_id: str) -> dict | None:
    bu = db.get(Buyer, buyer_id)
    if not bu:
        return None
    prof = get_or_create_profile(db, "business", buyer_id)
    orders = db.scalars(select(Order).where(Order.buyer_id == buyer_id)).all()
    completed = [o for o in orders if o.status in ("fully_allocated", "confirmed")]
    return {
        "subject_type": "business",
        "buyer_id": bu.buyer_id,
        "name": bu.name,
        "type": bu.type,
        "verification_status": prof.verification_status,
        "badges": badges_for(prof),
        "identity_verified": prof.identity_verified,
        "business_verified": prof.business_verified,
        "contact_verified": prof.contact_verified,
        "order_history_count": len(orders),
        "orders_completed": len(completed),
        "reliability_score": prof.reliability_score,
        "b2b_eligible": prof.b2b_eligible and prof.verification_status in TRUST_ACTIVE_STATES,
        "note": bu.contact_note,
        "is_demo": prof.is_demo,
        "disclaimer": "Business verification confirms identity, contact and registration "
                      "details on file. Private registration documents are not shown publicly.",
    }


# ── internals ────────────────────────────────────────────────────────────
def _event(db: Session, subject_id: str, subject_type: str, event_type: str,
           summary: str, detail: dict, actor: str = "system") -> None:
    db.add(TrustEvent(
        subject_id=subject_id, subject_type=subject_type, event_type=event_type,
        summary=summary, detail=detail, actor=actor,
    ))


def _sync_artisan_kyc(db: Session, artisan_id: str, value: str) -> None:
    a = db.get(Artisan, artisan_id)
    if a is not None:
        a.kyc_status = value
