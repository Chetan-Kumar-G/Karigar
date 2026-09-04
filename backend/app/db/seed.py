"""Build the full demo dataset from ``seed_data`` (spec §19, §20, §36).

``seed(reset=True)`` drops and rebuilds every table, regenerates placeholder
product images, ~200 days of **simulated** demand history, skewed exposure
history, market-price comparables, and one Digital Craft Passport per product.
Safe to run repeatedly — it is what "Reset Demo" calls.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import math
import random

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import UPLOAD_DIR
from app.core.logging import get_logger
from app.db.base import Base
from app.db.seed_data import (
    ARTISANS, BUYERS, CRAFT_RELATIONS, CRAFTS, MATERIALS, PRODUCTS,
    REGIONS, REQUIREMENTS, TECHNIQUES,
)
from app.db.session import SessionLocal, engine
from app.models import (
    Artisan, Buyer, BuyerRequirement, Cluster, Craft, CraftRelation, DemandSignal,
    Exposure, Inventory, Listing, Material, MarketPrice, PriceHistory, Product,
    ProductAttribute, ProductImage, Region, Technique,
)
from app.models.ids import new_id

log = get_logger("seed")
_RNG = random.Random(26090)

_COLOR_HEX = {
    "yellow": (240, 200, 70), "red": (200, 70, 60), "blue": (60, 90, 180),
    "green": (70, 150, 90), "black": (40, 40, 45), "white": (240, 238, 232),
    "brown": (140, 90, 55), "natural": (205, 180, 140),
}


def _make_image(path, title: str, colors: list[str], poor: bool = False) -> None:
    w = h = 900
    base = _COLOR_HEX.get(colors[0] if colors else "natural", (200, 190, 170))
    img = Image.new("RGB", (w, h), base)
    d = ImageDraw.Draw(img)
    for i, c in enumerate(colors[:3]):
        col = _COLOR_HEX.get(c, (180, 170, 150))
        d.ellipse([120 + i * 90, 200 + i * 60, 640 + i * 90, 720 + i * 60], fill=col)
    d.rectangle([60, 60, w - 60, h - 60], outline=(255, 255, 255), width=6)
    d.text((80, w - 120), title[:46], fill=(255, 255, 255))
    if poor:  # deliberately dim + noisy for the F1 demo
        img = Image.eval(img, lambda p: int(p * 0.45))
    img.save(path, "JPEG", quality=60 if poor else 88)


def _demand_series(category: str, region_id: str, start: dt.date, days: int):
    seed = int(hashlib.md5(f"{category}{region_id}".encode()).hexdigest(), 16)
    rng = random.Random(seed)
    base = rng.uniform(4, 22)
    trend = rng.uniform(-0.15, 0.7)
    amp = rng.uniform(0.2, 0.55)
    rows = []
    for i in range(days):
        day = start + dt.timedelta(days=i)
        doy = day.timetuple().tm_yday
        weekly = 1 + 0.18 * math.sin(2 * math.pi * i / 7)
        annual = 1 + amp * math.sin(2 * math.pi * doy / 365 - 1.0)
        festival = 1.55 if 250 < doy < 300 else 1.0
        level = base * (1 + trend * i / days)
        units = max(0, round(level * weekly * annual * festival * rng.uniform(0.8, 1.2)))
        rows.append(DemandSignal(
            category=category, region_id=region_id, date=day,
            browse_count=units * rng.randint(6, 14), order_count=max(1, units // 3),
            units_sold=units, is_simulated=True,
        ))
    return rows


def seed(db: Session | None = None, *, reset: bool = True) -> dict:
    close = False
    if db is None:
        db, close = SessionLocal(), True
    try:
        if reset:
            log.info("Dropping and recreating all tables ...")
            Base.metadata.drop_all(engine)
            Base.metadata.create_all(engine)
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        # ── regions + clusters ──────────────────────────────────────────
        for rid, name, state, odop, us, lat, lon in REGIONS:
            db.add(Region(region_id=rid, name=name, state=state, odop_cluster_id=odop,
                          underserved_index=us, lat=lat, lon=lon))
            db.add(Cluster(cluster_id=f"CL-{rid.split('-', 1)[1]}", region_id=rid,
                           name=f"{name} artisan cluster", total_capacity_estimate=0,
                           description=f"Registered {name} craft cluster ({state})."))
        db.flush()

        # ── techniques + materials ─────────────────────────────────────
        for tid, name, desc, kw in TECHNIQUES:
            db.add(Technique(technique_id=tid, name=name, description=desc, visual_keywords=kw))
        for mid, name, cost in MATERIALS:
            db.add(Material(material_id=mid, name=name, cost_prior_inr=cost))
        db.flush()

        # ── crafts + edges ────────────────────────────────────────────
        for cid, name, rid, rar, gi, giref, odop, techs, mats, heritage in CRAFTS:
            craft = Craft(craft_id=cid, name=name, region_id=rid, rarity_score=rar,
                          gi_status=gi, gi_reference=giref, odop_cluster=odop,
                          heritage_note=heritage, description=heritage[:180])
            craft.techniques = [db.get(Technique, t) for t in techs]
            craft.materials = [db.get(Material, m) for m in mats]
            db.add(craft)
        db.flush()
        for s, dst, rel, w in CRAFT_RELATIONS:
            db.add(CraftRelation(src_craft_id=s, dst_craft_id=dst, relation=rel, weight=w))
        db.flush()

        # ── artisans ─────────────────────────────────────────────────
        for (aid, name, phone, lang, rid, cid, cap, q, rel, logi, sales, kyc, bio) in ARTISANS:
            db.add(Artisan(
                artisan_id=aid, name=name, phone=phone, language=lang, region_id=rid,
                cluster_id=f"CL-{rid.split('-', 1)[1]}", kyc_status=kyc,
                reliability_score=rel, quality_score=q, monthly_capacity_units=cap,
                logistics_cost_per_unit_inr=logi, verified_sales_count=sales,
                avatar_seed=aid, bio=bio,
            ))
        db.flush()
        for cl in db.scalars(select(Cluster)).all():
            cl.total_capacity_estimate = sum(
                a.monthly_capacity_units for a in db.scalars(
                    select(Artisan).where(Artisan.cluster_id == cl.cluster_id)
                ).all()
            )

        # ── products, images, attributes, listings, passports ────────
        from app.ai.f3_graph.graph import build_passport

        categories: set[tuple[str, str]] = set()
        for (pid, aid, cid, title, cat, colors, material, price, floor, rating,
             rcount, quality, exposure_seed, is_demo, desc) in PRODUCTS:
            artisan = db.get(Artisan, aid)
            craft = db.get(Craft, cid)
            product = Product(
                product_id=pid, artisan_id=aid, craft_id=cid, title=title, category=cat,
                status="published", description_en=desc,
                description_hi=f"{title} — हस्तनिर्मित।", seo_title=title,
                seo_keywords=[f"{craft.name.lower()}", f"handmade {material}", cat],
                dimensions={}, is_demo=is_demo,
            )
            db.add(product)
            db.flush()

            img_id = new_id("IMG")
            fname = f"{img_id}.jpg"
            _make_image(UPLOAD_DIR / fname, title, colors, poor=is_demo)
            db.add(ProductImage(
                image_id=img_id, product_id=pid, url=f"/media/{fname}",
                readiness_score=58 if is_demo else _RNG.randint(72, 92),
                component_scores={}, decision="auto_enhance" if is_demo else "accept",
                is_primary=True,
            ))
            for key, val, src in [
                ("material", material, "voice"),
                ("technique", craft.techniques[0].name if craft.techniques else "handcraft", "voice"),
                ("region", craft.region.name, "manual"),
                ("colors", ", ".join(colors), "visual"),
            ]:
                db.add(ProductAttribute(
                    product_id=pid, attribute_key=key, attribute_value=val, source=src,
                    grounding_status="confirmed_from_voice" if src == "voice" else "artisan_reported",
                    confidence=0.85,
                ))

            db.add(Listing(
                listing_id=new_id("LST"), product_id=pid, current_price_inr=float(price),
                sustainable_floor_inr=float(floor),
                competitive_low_inr=float(floor), competitive_high_inr=float(price) * 1.25,
                premium_opportunity_inr=float(price) * 1.4, rating=rating, rating_count=rcount,
                quality_score=quality, exposure_score=float(exposure_seed),
                impressions_total=exposure_seed * 20, clicks_total=exposure_seed * 2,
            ))
            db.add(Inventory(product_id=pid, available_units=_RNG.randint(4, 40)))
            db.add(PriceHistory(product_id=pid, price_inr=float(price), source="listed"))
            db.flush()

            db.refresh(product)
            build_passport(
                db, product,
                grounding_pass_ratio=0.5 if is_demo else 0.85,
                visual_consistency_score=0.55 if is_demo else 0.8,
                self_report_consistency=0.7 if is_demo else 0.85,
            )
            categories.add((cat, craft.region_id))

        # ── market price comparables ────────────────────────────────
        for cat, rid in categories:
            listings = db.scalars(
                select(Listing).join(Product).where(Product.category == cat)
            ).all()
            prices = sorted(l.current_price_inr for l in listings) or [500]
            mid = prices[len(prices) // 2]
            db.add(MarketPrice(
                category=cat, region_id=rid, median_price_inr=float(mid),
                p25_price_inr=float(prices[0]), p75_price_inr=float(prices[-1]),
                sample_size=len(prices),
                source_note="Curated comparable table (demo data — not live scraped prices).",
            ))

        # ── ~200 days simulated demand history ─────────────────────
        start = dt.date.today() - dt.timedelta(days=200)
        for cat, rid in categories:
            for row in _demand_series(cat, rid, start, 200):
                db.add(row)

        # ── skewed exposure history (last 30 days) ─────────────────
        for listing in db.scalars(select(Listing)).all():
            artisan = listing.product.artisan
            established = artisan.verified_sales_count >= 15
            for k in range(30):
                day = dt.date.today() - dt.timedelta(days=k)
                imp = _RNG.randint(40, 120) if established else _RNG.randint(2, 14)
                db.add(Exposure(
                    listing_id=listing.listing_id, date=day, impressions=imp,
                    clicks=max(0, imp // _RNG.randint(6, 12)),
                    new_seller_boost_applied=not established,
                ))

        # ── buyers + B2B requirements ──────────────────────────────
        for bid, name, btype, phone, verified, note in BUYERS:
            db.add(Buyer(buyer_id=bid, name=name, type=btype, phone=phone,
                         verified=verified, contact_note=note,
                         reliability_weight=1.3 if btype == "government" else 1.0))
        db.flush()
        for (rqid, bid, cid, title, mat, qty, pmin, pmax, ddays, fmin, is_demo, notes) in REQUIREMENTS:
            db.add(BuyerRequirement(
                requirement_id=rqid, buyer_id=bid, craft_id=cid, title=title,
                required_material=mat, quantity=qty, price_min=float(pmin), price_max=float(pmax),
                deadline=dt.date.today() + dt.timedelta(days=ddays), fulfillment_min=fmin,
                status="open", notes=notes, is_demo=is_demo,
            ))
        db.flush()

        # ── trust & verification profiles (Verified Artisan / Business) ──
        _seed_trust(db)

        db.commit()
        from app.models import Complaint, VerificationProfile
        counts = {
            "regions": db.query(Region).count(),
            "crafts": db.query(Craft).count(),
            "artisans": db.query(Artisan).count(),
            "products": db.query(Product).count(),
            "listings": db.query(Listing).count(),
            "buyers": db.query(Buyer).count(),
            "requirements": db.query(BuyerRequirement).count(),
            "demand_signals": db.query(DemandSignal).count(),
            "exposure_rows": db.query(Exposure).count(),
            "verification_profiles": db.query(VerificationProfile).count(),
            "complaints": db.query(Complaint).count(),
        }
        log.info("Seed complete: %s", counts)
        return counts
    finally:
        if close:
            db.close()


def _seed_trust(db: Session) -> None:
    """Verified-Artisan / Verified-Business profiles + one demo complaint.

    All rows are marked ``is_demo`` (spec: mark demo accounts/data as Demo Data).
    GI status is set on its *own* axis — never inferred from craft/region alone.
    """
    import datetime as _dt

    from app.models import Buyer, Complaint, TrustEvent, VerificationEvidence, VerificationProfile
    from app.models.ids import new_id
    from app.models.trust import (
        GI_ARTISAN_REPORTED, GI_GOVERNMENT_VERIFIED, GI_NOT_REGISTERED, GI_PENDING,
        TRUST_PENDING, TRUST_VERIFIED,
    )
    from app.services.trust import compute_reliability

    # explicit GI overrides — only where the artisan/workshop actually reports it
    _GI_OVERRIDE = {
        "ART-MEERA": GI_PENDING,             # demo scenario: "GI: Pending Verification"
        "ART-ARSHAD": GI_GOVERNMENT_VERIFIED,  # bio: GI-registered workshop
    }

    today = _dt.date.today().isoformat()
    for a in db.scalars(select(Artisan)).all():
        verified = a.kyc_status == "verified"
        craft = next((p.craft for p in a.products if p.craft), None)
        gi = _GI_OVERRIDE.get(a.artisan_id)
        if gi is None:
            gi = GI_ARTISAN_REPORTED if (craft and craft.gi_status == "registered") \
                else GI_NOT_REGISTERED
        prof = VerificationProfile(
            profile_id=new_id("VP", 6), subject_type="artisan", subject_id=a.artisan_id,
            verification_status=TRUST_VERIFIED if verified else TRUST_PENDING,
            identity_verified=True,  # phone OTP always done at onboarding
            craft_verified=verified,
            product_verified=verified and any(p.status == "published" for p in a.products),
            gi_status=gi,
            gi_reference=(craft.gi_reference if craft and gi == GI_GOVERNMENT_VERIFIED else None),
            b2b_eligible=verified,
            verification_date=today if verified else None,
            verified_by="platform-review" if verified else None,
            is_demo=True,
        )
        db.add(prof)
        db.flush()
        score, breakdown = compute_reliability(db, a.artisan_id)
        prof.reliability_score = score
        prof.reliability_breakdown = breakdown
        prof.completed_orders = breakdown["signals"]["completed_orders"]
        prof.on_time_pct = breakdown["signals"]["on_time_pct"]

        db.add(VerificationEvidence(
            profile_id=prof.profile_id, kind="phone_otp", axis="identity",
            label="Phone number (OTP)", status="accepted", ai_assisted=False,
            note="Verified at onboarding.",
        ))
        if verified:
            db.add(VerificationEvidence(
                profile_id=prof.profile_id, kind="gov_kyc", axis="identity",
                label="Government KYC on file", status="accepted",
                note="Reviewed by platform. Document not shown publicly.",
            ))
            db.add(VerificationEvidence(
                profile_id=prof.profile_id, kind="product_sample", axis="craft",
                label="Craft / product samples", status="accepted", ai_assisted=True,
                note="F1 readiness + F2 attribute grounding assisted the reviewer.",
            ))
        else:
            db.add(VerificationEvidence(
                profile_id=prof.profile_id, kind="product_sample", axis="craft",
                label="Craft / product samples", status="more_needed", ai_assisted=True,
                note="We need one more proof for your craft claim.",
            ))
        db.add(TrustEvent(
            subject_id=a.artisan_id, subject_type="artisan", event_type="status_change",
            summary=f"Seeded profile ({prof.verification_status})",
            detail={"to": prof.verification_status}, actor="seed",
        ))

    for b in db.scalars(select(Buyer)).all():
        prof = VerificationProfile(
            profile_id=new_id("VP", 6), subject_type="business", subject_id=b.buyer_id,
            verification_status=TRUST_VERIFIED if b.verified else TRUST_PENDING,
            identity_verified=b.verified, business_verified=b.verified,
            contact_verified=b.verified, b2b_eligible=b.verified,
            gi_status=GI_NOT_REGISTERED,
            verification_date=today if b.verified else None,
            verified_by="platform-review" if b.verified else None,
            is_demo=True,
        )
        db.add(prof)
        db.flush()
        db.add(VerificationEvidence(
            profile_id=prof.profile_id, kind="business_registration", axis="business",
            label="Business registration / KYC", status="accepted" if b.verified else "submitted",
            note="Registration details on file. Not shown publicly.",
        ))

    # one open demo complaint so the reviewer dashboard is not empty
    demo_target = db.get(Artisan, "ART-RupA")
    if demo_target is not None:
        c = Complaint(
            complaint_id=new_id("CMP", 4), reported_by="BUY-BOUTIQUE", subject_type="artisan",
            subject_id="ART-RupA", order_id=None, category="product_not_as_described",
            severity="medium", status="open", is_demo=True,
            description="Card set colours were lighter than the listing photo.",
            risk_flag="Buyer report conflicts with the listed product claims.",
        )
        db.add(c)
        db.add(TrustEvent(
            subject_id="ART-RupA", subject_type="artisan", event_type="complaint",
            summary=f"Demo complaint {c.complaint_id}: product_not_as_described",
            detail={"complaint_id": c.complaint_id}, actor="seed",
        ))
    db.flush()


if __name__ == "__main__":  # pragma: no cover
    seed(reset=True)
