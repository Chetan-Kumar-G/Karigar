"""Product lifecycle + F1 AI Product Studio (spec §8, §12, §18)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.f1_studio.analyzer import analyze
from app.api.deps import Identity, current_identity, get_db, optional_identity
from app.core.config import UPLOAD_DIR, settings
from app.models import Artisan, Craft, Inventory, Listing, PriceHistory, Product, ProductImage
from app.models.ids import new_id
from app.schemas.models import PublishRequest

router = APIRouter(tags=["products"])


def _save_bytes(data: bytes, suffix: str) -> str:
    name = f"{new_id('IMG', 10)}.{suffix}"
    (UPLOAD_DIR / name).write_bytes(data)
    return f"/media/{name}"


def _product_dict(p: Product) -> dict:
    img = next((i for i in p.images if i.is_primary), p.images[0] if p.images else None)
    return {
        "product_id": p.product_id, "title": p.title, "status": p.status,
        "category": p.category, "craft_id": p.craft_id,
        "craft_name": p.craft.name if p.craft else None,
        "description_en": p.description_en, "description_hi": p.description_hi,
        "seo_title": p.seo_title, "seo_keywords": p.seo_keywords,
        "artisan_id": p.artisan_id, "artisan_name": p.artisan.name if p.artisan else None,
        "primary_image": (img.enhanced_url or img.url) if img else None,
        "images": [{"image_id": i.image_id, "url": i.url, "enhanced_url": i.enhanced_url,
                    "mask_url": i.mask_url, "readiness_score": i.readiness_score,
                    "component_scores": i.component_scores, "decision": i.decision}
                   for i in p.images],
        "listing": None if not p.listing else {
            "listing_id": p.listing.listing_id, "price_inr": p.listing.current_price_inr,
            "sustainable_floor_inr": p.listing.sustainable_floor_inr,
            "rating": p.listing.rating, "exposure_score": p.listing.exposure_score,
        },
        "passport_id": p.passport.passport_id if p.passport else None,
        "inventory": None if not p.inventory else {
            "available_units": p.inventory.available_units,
            "reserved_units": p.inventory.reserved_units,
        },
        "is_demo": p.is_demo,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.post("/product")
def create_product(
    title: str = Form("Untitled product"),
    craft_id: str | None = Form(None),
    category: str | None = Form(None),
    ident: Identity = Depends(current_identity),
    db: Session = Depends(get_db),
):
    if ident.role != "artisan":
        raise HTTPException(403, "Only artisans can create products")
    craft = db.get(Craft, craft_id) if craft_id else None
    p = Product(
        product_id=new_id("PRD"), artisan_id=ident.artisan_id, craft_id=craft_id,
        title=title, category=category or (craft.name if craft else None), status="draft",
    )
    db.add(p)
    db.add(Inventory(product_id=p.product_id, available_units=0))
    db.commit()
    db.refresh(p)
    return _product_dict(p)


@router.get("/products")
def list_products(ident: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Product).where(Product.artisan_id == ident.artisan_id)
        .order_by(Product.created_at.desc())
    ).all()
    return {"products": [_product_dict(p) for p in rows]}


@router.get("/product/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return _product_dict(p)


@router.post("/product/analyze")
async def product_analyze(
    image: UploadFile = File(...),
    product_id: str | None = Form(None),
    product_category_hint: str | None = Form(None),
    ident: Identity | None = Depends(optional_identity),
    db: Session = Depends(get_db),
):
    """F1 — run the readiness pipeline on an uploaded photo."""
    if image.content_type not in settings.allowed_image_types and image.content_type != "application/octet-stream":
        raise HTTPException(415, f"Unsupported image type: {image.content_type}")
    raw = await image.read()
    if len(raw) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Image exceeds {settings.max_upload_mb} MB limit")
    if len(raw) < 512:
        raise HTTPException(422, "Image looks empty or corrupt")

    try:
        result = analyze(raw, product_category_hint)
    except Exception as exc:  # malformed image / decode failure
        raise HTTPException(422, f"Could not process this image: {exc}")

    original_url = _save_bytes(raw, "jpg")
    data = dict(result.data)
    enhanced_png = data.pop("_enhanced_png", None)
    mask_png = data.pop("_mask_png", None)
    enhanced_url = _save_bytes(enhanced_png, "png") if enhanced_png else None
    mask_url = _save_bytes(mask_png, "png") if mask_png else None

    image_id = new_id("IMG")
    if product_id:
        p = db.get(Product, product_id)
        if p:
            for i in p.images:
                i.is_primary = False
            db.add(ProductImage(
                image_id=image_id, product_id=product_id, url=original_url,
                enhanced_url=enhanced_url, mask_url=mask_url,
                readiness_score=data["readiness_score"],
                component_scores=data["component_scores"], decision=data["decision"],
                is_primary=True,
            ))
            if p.status == "draft":
                p.status = "analyzing"
            result.persist(db, subject_id=product_id)
            db.commit()

    return {
        "image_id": image_id,
        "original_url": original_url,
        "enhanced_url": enhanced_url,
        "mask_url": mask_url,
        **data,
        "_meta": result.metadata(),
    }


@router.post("/product/{product_id}/select-image")
def select_image(product_id: str, image_id: str = Form(...), use_enhanced: bool = Form(True),
                 db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    found = False
    for i in p.images:
        i.is_primary = (i.image_id == image_id)
        found = found or i.is_primary
    if not found:
        raise HTTPException(404, "Image not found on this product")
    db.commit()
    return _product_dict(p)


@router.post("/product/publish")
def publish(body: PublishRequest, ident: Identity = Depends(current_identity),
            db: Session = Depends(get_db)):
    p = db.get(Product, body.product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    if p.artisan_id != ident.artisan_id:
        raise HTTPException(403, "Not your product")

    price = body.price_inr
    floor = None
    if p.listing:
        price = price or p.listing.current_price_inr
        floor = p.listing.sustainable_floor_inr
    price = price or 500.0
    if floor and price < floor:
        raise HTTPException(422, f"Price ₹{price:.0f} is below the sustainable floor ₹{floor:.0f}")

    img = next((i for i in p.images if i.is_primary), p.images[0] if p.images else None)
    quality = (img.readiness_score / 100) if img and img.readiness_score else 0.7

    if p.listing:
        p.listing.current_price_inr = price
    else:
        db.add(Listing(listing_id=new_id("LST"), product_id=p.product_id,
                       current_price_inr=price, sustainable_floor_inr=floor,
                       quality_score=quality, exposure_score=0.0, rating=0.0, rating_count=0))
    db.add(PriceHistory(product_id=p.product_id, price_inr=price, source="listed"))
    if not p.inventory:
        db.add(Inventory(product_id=p.product_id, available_units=10))
    p.status = "published"
    db.commit()
    db.refresh(p)
    return {"published": True, **_product_dict(p)}


@router.get("/inventory")
def my_inventory(ident: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Product).where(Product.artisan_id == ident.artisan_id,
                              Product.status == "published")
    ).all()
    items = []
    for p in rows:
        inv = p.inventory
        items.append({
            "product_id": p.product_id, "title": p.title,
            "primary_image": next((i.enhanced_url or i.url for i in p.images if i.is_primary),
                                  p.images[0].url if p.images else None),
            "price_inr": p.listing.current_price_inr if p.listing else None,
            "available_units": inv.available_units if inv else 0,
            "reserved_units": inv.reserved_units if inv else 0,
        })
    return {"items": items, "total_units": sum(i["available_units"] for i in items)}


@router.post("/product/{product_id}/inventory")
def set_inventory(product_id: str, available_units: int = Form(...),
                  ident: Identity = Depends(current_identity), db: Session = Depends(get_db)):
    p = db.get(Product, product_id)
    if not p or p.artisan_id != ident.artisan_id:
        raise HTTPException(404, "Product not found")
    if available_units < 0:
        raise HTTPException(422, "available_units cannot be negative")
    if not p.inventory:
        db.add(Inventory(product_id=product_id, available_units=available_units))
    else:
        p.inventory.available_units = available_units
    db.commit()
    return {"product_id": product_id, "available_units": available_units}


@router.get("/artisan/{artisan_id}/products")
def artisan_products(artisan_id: str, db: Session = Depends(get_db)):
    a = db.get(Artisan, artisan_id)
    if not a:
        raise HTTPException(404, "Artisan not found")
    rows = db.scalars(select(Product).where(Product.artisan_id == artisan_id)).all()
    return {"artisan": a.name, "products": [_product_dict(p) for p in rows]}
