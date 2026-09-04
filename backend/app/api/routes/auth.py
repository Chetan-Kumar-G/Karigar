"""Mock phone-OTP auth (spec §3, §12)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Identity, current_identity, get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models import Artisan, Buyer
from app.models.ids import new_id
from app.schemas.models import OtpRequest, OtpVerify, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

DEMO_ACCOUNTS = {
    "artisan": {"phone": "9800000001", "label": "Meera Devi (Madhubani artisan)"},
    "buyer": {"phone": "9900000001", "label": "Meridian Hotels procurement"},
}


@router.post("/otp/request")
def request_otp(body: OtpRequest):
    # Prototype: no SMS is sent — every number accepts the mock OTP.
    return {
        "sent": True,
        "phone": body.phone,
        "hint": f"Use OTP {settings.mock_otp} (prototype mock).",
        "mock_otp": settings.mock_otp,
    }


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(body: OtpVerify, db: Session = Depends(get_db)):
    if body.otp != settings.mock_otp:
        raise HTTPException(401, "Incorrect OTP. Prototype OTP is " + settings.mock_otp)

    if body.role == "buyer":
        buyer = db.scalars(select(Buyer).where(Buyer.phone == body.phone)).first()
        if not buyer:
            buyer = Buyer(buyer_id=new_id("BUY"), name=f"Buyer {body.phone[-4:]}",
                          type="B2B", phone=body.phone, verified=True)
            db.add(buyer)
            db.commit()
        token = create_access_token(buyer.buyer_id, {"role": "buyer", "buyer_id": buyer.buyer_id,
                                                     "name": buyer.name})
        return TokenResponse(access_token=token, role="buyer",
                             profile={"buyer_id": buyer.buyer_id, "name": buyer.name,
                                      "type": buyer.type, "verified": buyer.verified})

    artisan = db.scalars(select(Artisan).where(Artisan.phone == body.phone)).first()
    if not artisan:
        # auto-provision a fresh artisan onto the first region/cluster
        from app.models import Region
        region = db.scalars(select(Region)).first()
        artisan = Artisan(artisan_id=new_id("ART"), name=f"Artisan {body.phone[-4:]}",
                          phone=body.phone, region_id=region.region_id,
                          cluster_id=f"CL-{region.region_id.split('-', 1)[1]}",
                          kyc_status="pending")
        db.add(artisan)
        db.commit()
    token = create_access_token(artisan.artisan_id, {"role": "artisan",
                                                     "artisan_id": artisan.artisan_id,
                                                     "name": artisan.name})
    return TokenResponse(access_token=token, role="artisan",
                         profile=_artisan_profile(db, artisan))


@router.get("/me")
def me(ident: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    if ident.role == "buyer":
        buyer = db.get(Buyer, ident.buyer_id)
        return {"role": "buyer", "profile": {"buyer_id": buyer.buyer_id, "name": buyer.name,
                                             "type": buyer.type, "verified": buyer.verified}}
    artisan = db.get(Artisan, ident.artisan_id)
    return {"role": "artisan", "profile": _artisan_profile(db, artisan)}


@router.get("/demo-accounts")
def demo_accounts():
    return {"accounts": DEMO_ACCOUNTS, "otp": settings.mock_otp}


def _artisan_profile(db: Session, a: Artisan) -> dict:
    return {
        "artisan_id": a.artisan_id, "name": a.name, "phone": a.phone,
        "language": a.language, "kyc_status": a.kyc_status,
        "region": a.region.name if a.region else None,
        "state": a.region.state if a.region else None,
        "cluster": a.cluster.name if a.cluster else None,
        "monthly_capacity_units": a.monthly_capacity_units,
        "quality_score": a.quality_score, "reliability_score": a.reliability_score,
        "verified_sales_count": a.verified_sales_count,
        "bio": a.bio,
    }
