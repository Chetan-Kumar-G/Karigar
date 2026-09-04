"""SIH Demo Mode — load a known scenario / reset everything (spec §36, §37)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.api.deps import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.db.seed import seed
from app.models import Artisan, BuyerRequirement, Complaint, Product, VerificationProfile
from app.services.trust import public_artisan_card

router = APIRouter(prefix="/demo", tags=["demo"])

_SCENARIO = {
    "title": "Meera the Madhubani weaver → 5,000-unit hotel order",
    "artisan_id": "ART-MEERA",
    "artisan_phone": "9800000001",
    "demo_product_id": "PRD-DEMO-DUP",
    "demo_requirement_id": "REQ-DEMO-BASKET",
    "buyer_phone": "9900000001",
    "otp": settings.mock_otp,
    "voice_language_hint": "hi",
    "cost_inputs": {
        "material_cost_inr": 180, "labour_hours": 6, "labour_rate_inr_per_hour": 60,
        "packaging_cost_inr": 40, "logistics_cost_inr": 30,
    },
    "steps": [
        "Login as artisan (9800000001 / 123456)",
        "Open dashboard — see 'things that need attention'",
        "Add Product → capture the poor demo photo → F1 shows ~58/100 → Auto-Enhance",
        "Record voice (or use demo transcript) → F2 attributes + EN/HI + grounding flag",
        "Open Craft Passport → provenance confidence ~0.74",
        "Open Fair Price → floor / range / recommended, floor is a hard constraint",
        "Publish → listing created",
        "Marketplace → search 'handwoven cotton dupatta' → new artisan ranked up (F7)",
        "Business Copilot → 'demand rising' card",
        "Switch to Buyer mode → open the 5,000 bamboo-basket requirement",
        "Run Find Artisan Cluster → F6 CP-SAT allocation across 3-4 artisans in <1s",
        "Show 5,000/5,000 fulfilled + Shapley payment split vs proportional split",
    ],
}

_CAST = {
    "title": "Named demo cast — Thanjavur art-plate cluster",
    "otp": settings.mock_otp,
    "buyers": [
        {"name": "Agneay", "phone": "9600000001", "buyer_id": "BUY-AGNEAY", "type": "B2B",
         "use_for": "the 2,900-plate bulk order that splits across all three artisans"},
        {"name": "Cynthiya", "phone": "9600000002", "buyer_id": "BUY-CYNTHIYA", "type": "retail",
         "use_for": "a small 60-plate order (single artisan)"},
        {"name": "Prarthana", "phone": "9600000003", "buyer_id": "BUY-PRARTHANA", "type": "government",
         "use_for": "raising a fresh requirement live from the buyer screen"},
    ],
    "artisans": [
        {"name": "Chetan", "phone": "9700000001", "artisan_id": "ART-CHETAN",
         "capacity": 900, "note": "highest quality/reliability, closest to the hub"},
        {"name": "Prasannaa", "phone": "9700000002", "artisan_id": "ART-PRASANNAA",
         "capacity": 1500, "note": "largest capacity, cheapest landed cost"},
        {"name": "Deeraj", "phone": "9700000003", "artisan_id": "ART-DEERAJ",
         "capacity": 700, "note": "smallest / furthest — takes the remainder in the split"},
    ],
    "bulk_requirement_id": "REQ-DEMO-THJ",
    "small_requirement_id": "REQ-DEMO-THJ-SM",
    "craft_id": "CRAFT-THANJAVUR",
    "walkthrough": [
        "Login as buyer Agneay (9600000001 / 123456)",
        "Open the requirement 'Thanjavur art plates' → Find Artisan Cluster (F6)",
        "See the CP-SAT split: Prasannaa ~1500 + Chetan ~900 + Deeraj ~500 = 2,900",
        "See the Shapley payment split vs a plain by-units split, with a per-artisan reason",
        "Confirm the allocation",
        "Switch role → login as artisan Prasannaa (9700000002 / 123456)",
        "Open Orders → the pooled order is there with this artisan's units + payment share",
        "(Small order) login as Cynthiya (9600000002) → 60-plate requirement → goes to one maker",
    ],
}

_TRUST_SCENARIO = {
    "title": "Trust & Verification — a new artisan is verified, then investigated",
    "demo_artisan_id": "ART-RupA",
    "demo_artisan_name": "Rupa Yadav",
    "reported_by": "BUY-BOUTIQUE",
    "steps": [
        "Open Profile → Verification — Rupa has submitted identity, craft, product, region "
        "and a certification claim; status is PENDING",
        "Open Reviewer dashboard → pick Rupa → see evidence, F1 readiness, F2 claims, "
        "F3 passport + GI status, order history, reliability score",
        "Tap Approve → Identity Verified ✓, Craft Verified ✓, GI: Pending Verification → "
        "badge becomes 🟢 VERIFIED ARTISAN",
        "A buyer taps Report an issue → 'Product not as described'",
        "System records the complaint, attaches an AI RISK FLAG (not a verdict), and moves "
        "the account to UNDER_REVIEW",
        "Reviewer investigates → Suspend (temporary) or Reinstate — the final call is human",
    ],
    "state_machine": ["PENDING", "VERIFIED", "UNDER_REVIEW", "SUSPENDED", "REINSTATED",
                      "(REJECTED)"],
}


@router.get("/scenario")
def scenario(db: Session = Depends(get_db)):
    demo_product = db.get(Product, _SCENARIO["demo_product_id"])
    req = db.get(BuyerRequirement, _SCENARIO["demo_requirement_id"])
    return {
        **_SCENARIO,
        "demo_product_exists": demo_product is not None,
        "demo_requirement_exists": req is not None,
        "artisan_token_hint": "POST /api/auth/otp/verify {phone:'9800000001', otp:'123456'}",
        "trust_scenario": _TRUST_SCENARIO,
        "cast": _CAST,
    }


@router.get("/cast")
def cast(db: Session = Depends(get_db)):
    """Named demo cast (Agneay/Cynthiya/Prarthana + Chetan/Prasannaa/Deeraj) with
    live existence checks so the walkthrough can't reference a missing row."""
    from app.models import Artisan, Buyer

    return {
        **_CAST,
        "buyers": [{**b, "exists": db.get(Buyer, b["buyer_id"]) is not None}
                   for b in _CAST["buyers"]],
        "artisans": [{**a, "exists": db.get(Artisan, a["artisan_id"]) is not None}
                     for a in _CAST["artisans"]],
        "bulk_requirement_exists": db.get(BuyerRequirement, _CAST["bulk_requirement_id"]) is not None,
        "small_requirement_exists": db.get(BuyerRequirement, _CAST["small_requirement_id"]) is not None,
    }


@router.get("/trust")
def trust_scenario(db: Session = Depends(get_db)):
    """Live state of the trust-focused demo subject + the script to follow."""
    aid = _TRUST_SCENARIO["demo_artisan_id"]
    prof = db.scalars(
        select(VerificationProfile).where(VerificationProfile.subject_id == aid)
    ).first()
    complaints = db.scalars(
        select(Complaint).where(Complaint.subject_id == aid)
    ).all()
    return {
        **_TRUST_SCENARIO,
        "current": {
            "verification_status": prof.verification_status if prof else None,
            "gi_status": prof.gi_status if prof else None,
            "reliability_score": prof.reliability_score if prof else None,
            "open_complaints": sum(1 for c in complaints if c.status in ("open", "investigating")),
            "card": public_artisan_card(db, aid),
        },
        "endpoints": {
            "reviewer_queue": "GET /api/trust/reviewer/queue",
            "reviewer_detail": f"GET /api/trust/reviewer/{{profile_id}} (profile_id="
                               f"{prof.profile_id if prof else '?'})",
            "reviewer_action": "POST /api/trust/reviewer/{profile_id}/action "
                               "{action: approve|suspend|reinstate|reject|place_under_review}",
            "report_issue": "POST /api/trust/complaints {subject_id, category, ...}",
        },
    }


@router.post("/reset")
def reset(db: Session = Depends(get_db)):
    """Reset the whole database to the known demo dataset (spec §36)."""
    counts = seed(reset=True)
    return {"reset": True, "counts": counts, "scenario": _SCENARIO["title"]}


@router.post("/load")
def load(db: Session = Depends(get_db)):
    """Same as reset, plus hand back ready-to-use artisan + buyer tokens."""
    counts = seed(reset=True)
    a = db.get(Artisan, _SCENARIO["artisan_id"])
    artisan_token = create_access_token(a.artisan_id, {"role": "artisan", "artisan_id": a.artisan_id,
                                                       "name": a.name})
    from app.models import Buyer
    b = db.query(Buyer).filter(Buyer.phone == _SCENARIO["buyer_phone"]).first()
    buyer_token = create_access_token(b.buyer_id, {"role": "buyer", "buyer_id": b.buyer_id,
                                                   "name": b.name})
    return {"loaded": True, "counts": counts,
            "artisan": {"token": artisan_token, "artisan_id": a.artisan_id, "name": a.name},
            "buyer": {"token": buyer_token, "buyer_id": b.buyer_id, "name": b.name},
            "scenario": _SCENARIO}
