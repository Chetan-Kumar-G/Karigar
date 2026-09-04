"""API validation + the end-to-end create→catalog→price→publish→search→match flow."""
from __future__ import annotations

import io

from PIL import Image


def _img(dim=(1100, 850), shade=70):
    b = io.BytesIO()
    Image.new("RGB", dim, (shade, shade - 8, shade - 15)).save(b, "JPEG", quality=45)
    return b.getvalue()


def test_health_and_features(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    h = r.json()
    # Phase 2 contract: status + database + version, DB probe reports "ok".
    assert h["status"] == "ok"
    assert h["database"] == "ok"
    assert h["version"] and isinstance(h["version"], str)
    assert h["products"] >= 0
    # Bare alias works too (plain `curl host:8000/health`).
    assert client.get("/health").json()["database"] == "ok"
    feats = client.get("/api/meta/features").json()
    assert set(feats) >= {"F1", "F2", "F3", "F4", "F5", "F6", "F7"}
    assert feats["F6"]["mode"] == "REAL"


def test_auth_rejects_bad_otp(client):
    r = client.post("/api/auth/otp/verify", json={"phone": "9999999999", "otp": "000000"})
    assert r.status_code == 401


def test_analyze_rejects_tiny_payload(client):
    r = client.post("/api/product/analyze", files={"image": ("x.jpg", b"x", "image/jpeg")})
    assert r.status_code in (422, 415)


def test_price_predict_validates_negative(client):
    r = client.post("/api/price/predict", json={"material_cost_inr": -5, "labour_hours": 1,
                                                "labour_rate_inr_per_hour": 10})
    assert r.status_code == 422


def test_full_journey(client):
    tok = client.post("/api/auth/otp/verify",
                      json={"phone": "9800000001", "otp": "123456"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}

    pid = client.post("/api/product", data={"title": "Flow dupatta", "craft_id": "CRAFT-MADH",
                                            "category": "dupatta"}, headers=H).json()["product_id"]

    a = client.post("/api/product/analyze", files={"image": ("p.jpg", _img(), "image/jpeg")},
                    data={"product_id": pid}, headers=H).json()
    assert 0 <= a["readiness_score"] <= 100

    cat = client.post("/api/catalog/generate",
                      data={"product_id": pid, "language_hint": "hi", "craft_id": "CRAFT-MADH"}).json()
    assert cat["description_en"] and cat["description_hi"]
    assert cat["grounding_check"]["region_claimed"] == "flagged_unverified_gi_claim"

    passport = client.get(f"/api/passport/{pid}").json()
    assert 0 < passport["provenance_confidence"] <= 1

    price = client.post("/api/price/predict", json={
        "product_id": pid, "material_cost_inr": 180, "labour_hours": 6,
        "labour_rate_inr_per_hour": 60, "packaging_cost_inr": 40, "logistics_cost_inr": 30,
        "category": "dupatta"}).json()
    assert price["recommended_price_inr"] >= price["sustainable_floor_inr"]

    pub = client.post("/api/product/publish", json={"product_id": pid}, headers=H)
    assert pub.status_code == 200 and pub.json()["status"] == "published"

    s = client.get("/api/search", params={"q": "handwoven cotton dupatta"}).json()
    assert s["count"] > 0
    assert "final_score" in s["results"][0]["score_breakdown"]


def test_b2b_pooling_endpoint(client):
    tok = client.post("/api/auth/otp/verify",
                      json={"phone": "9900000001", "otp": "123456", "role": "buyer"}
                      ).json()["access_token"]
    r = client.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-BASKET"},
                    headers={"Authorization": f"Bearer {tok}"}).json()
    assert r["total_allocated"] == 5000
    assert len(r["allocations"]) >= 2
    shp = [x["payment_share_inr"] for x in r["allocations"]]
    prp = [x["proportional_share_inr"] for x in r["allocations"]]
    assert shp != prp


def test_publish_below_floor_rejected(client, db):
    from app.models import Listing
    tok = client.post("/api/auth/otp/verify",
                      json={"phone": "9800000001", "otp": "123456"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    pid = client.post("/api/product", data={"title": "Floor test", "craft_id": "CRAFT-MADH",
                                            "category": "dupatta"}, headers=H).json()["product_id"]
    client.post("/api/price/predict", json={
        "product_id": pid, "material_cost_inr": 400, "labour_hours": 12,
        "labour_rate_inr_per_hour": 90, "packaging_cost_inr": 60, "logistics_cost_inr": 80,
        "category": "dupatta"})
    r = client.post("/api/product/publish", json={"product_id": pid, "price_inr": 100}, headers=H)
    assert r.status_code == 422
