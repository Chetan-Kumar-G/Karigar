"""End-to-end API smoke test via FastAPI TestClient — the full demo journey."""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

c = TestClient(app)
PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {name} {extra}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def poor_photo() -> bytes:
    img = Image.new("RGB", (1100, 850), (70, 62, 55))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=45)
    return buf.getvalue()


print("\n== demo/load ==")
r = c.post("/api/demo/load")
check("demo load", r.status_code == 200, r.status_code)
data = r.json()
atoken = data["artisan"]["token"]
btoken = data["buyer"]["token"]
AH = {"Authorization": f"Bearer {atoken}"}
BH = {"Authorization": f"Bearer {btoken}"}

print("\n== meta ==")
r = c.get("/api/meta/features")
check("features F1..F7", all(k in r.json() for k in ["F1", "F2", "F3", "F4", "F5", "F6", "F7"]))
check("F4 mode REAL", r.json()["F4"]["mode"] == "REAL", r.json()["F4"]["mode"])
check("F6 mode REAL", r.json()["F6"]["mode"] == "REAL")

print("\n== auth ==")
r = c.post("/api/auth/otp/verify", json={"phone": "9800000001", "otp": "123456"})
check("artisan login", r.status_code == 200 and r.json()["role"] == "artisan")

print("\n== F1 analyze ==")
r = c.post("/api/product", data={"title": "Test dupatta", "craft_id": "CRAFT-MADH",
                                 "category": "dupatta"}, headers=AH)
check("create product", r.status_code == 200, r.status_code)
pid = r.json()["product_id"]
r = c.post("/api/product/analyze",
           files={"image": ("p.jpg", poor_photo(), "image/jpeg")},
           data={"product_id": pid, "product_category_hint": "textile"}, headers=AH)
check("F1 analyze 200", r.status_code == 200, r.status_code)
j = r.json()
check("F1 readiness present", "readiness_score" in j, j.get("readiness_score"))
check("F1 decision valid", j.get("decision") in ("accept", "auto_enhance", "retake"), j.get("decision"))
check("F1 component scores", set(j["component_scores"]) == {
    "sharpness", "exposure", "framing", "background_cleanliness", "resolution",
    "colour_fidelity"})
check("F1 enhancement gate verdict", j["enhancement_gate"]["verdict"] in
      ("USE_ENHANCED", "ACCEPT_ORIGINAL", "REQUEST_RETAKE"),
      j["enhancement_gate"]["verdict"])

print("\n== F2 catalog ==")
r = c.post("/api/catalog/generate", data={"product_id": pid, "language_hint": "hi",
                                          "craft_id": "CRAFT-MADH",
                                          "visual_context": '{"detected_colors":["yellow","red"],'
                                                            '"segmentation_present":true,'
                                                            '"product_type_hint":"cotton dupatta textile"}'})
check("F2 200", r.status_code == 200, r.status_code)
j = r.json()
check("F2 extracted material", j["extracted_attributes"]["material"] == "cotton", j["extracted_attributes"])
check("F2 grounding region flagged",
      j["grounding_check"].get("region_claimed") == "flagged_unverified_gi_claim",
      j["grounding_check"])
check("F2 EN + HI copy", bool(j["description_en"]) and bool(j["description_hi"]))
_valid = {"SUPPORTED", "VISUALLY_CONSISTENT", "CONTRADICTED", "UNKNOWN", "NEEDS_HUMAN_REVIEW"}
check("F2 claim block present", isinstance(j.get("claims"), list) and len(j["claims"]) > 0)
check("F2 claim statuses canonical",
      all(cl["status"] in _valid for cl in j.get("claims", [])),
      [cl["status"] for cl in j.get("claims", [])])
check("F2 handmade claim is UNKNOWN",
      any(cl["attribute"] == "handmade" and cl["status"] == "UNKNOWN" for cl in j["claims"]))
_reg = next((cl for cl in j["claims"] if cl["attribute"] == "region"), None)
check("F2 region claim is consistency-only (never CV-proven GI)",
      _reg is not None and _reg["status"] in ("NEEDS_HUMAN_REVIEW", "SUPPORTED")
      and "documentation" in _reg["evidence"].lower(),
      _reg)
check("F2 summary headline honest",
      j["verification_summary"]["headline"].startswith("AI checks whether"),
      j["verification_summary"].get("headline"))

print("\n== F3 passport ==")
r = c.get(f"/api/passport/{pid}")
check("F3 200", r.status_code == 200, r.status_code)
j = r.json()
check("F3 provenance_confidence", 0 < j["provenance_confidence"] <= 1, j["provenance_confidence"])
check("F3 confidence breakdown terms", set(j["confidence_breakdown"]) >= {
    "gov_source_verified", "grounding_guard_pass", "visual_consistency_score",
    "artisan_self_report_consistency"})
r = c.get("/api/craft/CRAFT-MADH")
check("F3 related crafts via CTE", len(r.json()["related_crafts"]) > 0, r.json()["related_crafts"])

print("\n== F4 pricing ==")
r = c.post("/api/price/predict", json={"product_id": pid, "material_cost_inr": 180,
                                       "labour_hours": 6, "labour_rate_inr_per_hour": 60,
                                       "packaging_cost_inr": 40, "logistics_cost_inr": 30,
                                       "category": "dupatta"})
check("F4 200", r.status_code == 200, r.status_code)
j = r.json()
check("F4 rec >= floor", j["recommended_price_inr"] >= j["sustainable_floor_inr"],
      f'{j["recommended_price_inr"]} vs {j["sustainable_floor_inr"]}')
check("F4 range", len(j["competitive_range_inr"]) == 2)
# floor-binding case
r = c.post("/api/price/predict", json={"material_cost_inr": 500, "labour_hours": 12,
                                       "labour_rate_inr_per_hour": 90, "packaging_cost_inr": 60,
                                       "logistics_cost_inr": 80, "category_median_price_inr": 150})
j = r.json()
check("F4 floor binding never below", j["recommended_price_inr"] >= j["sustainable_floor_inr"] and j["floor_is_binding"],
      j)

print("\n== F5 demand ==")
r = c.get("/api/demand/forecast", params={"category": "basket", "region_id": "REG-ASM-MAJ",
                                          "window_days": 30, "artisan_id": "ART-BHASKAR"})
check("F5 200", r.status_code == 200, r.status_code)
j = r.json()
check("F5 predicted units", j["predicted_demand_units"] > 0, j["predicted_demand_units"])
check("F5 CI ordered", j["confidence_interval"][0] <= j["confidence_interval"][1])
check("F5 action text", "text_en" in j["action_recommendation"])
check("F5 simulated flagged", j["is_simulated"] is True)

print("\n== publish + F7 search ==")
r = c.post("/api/product/publish", json={"product_id": pid}, headers=AH)
check("publish 200", r.status_code == 200, (r.status_code, r.text[:160]))
r = c.get("/api/search", params={"q": "handwoven cotton dupatta", "fairness": True})
check("F7 200", r.status_code == 200, r.status_code)
j = r.json()
check("F7 results", j["count"] > 0, j["count"])
check("F7 breakdown fields", set(j["results"][0]["score_breakdown"]) >= {
    "relevance", "new_seller_boost", "underserved_region_boost", "exposure_penalty", "final_score"})
r = c.get("/api/search/compare", params={"q": "handwoven cotton dupatta"})
check("F7 compare on/off", "fairness_on" in r.json() and "fairness_off" in r.json())

print("\n== F6 buyer match (5000 units) ==")
r = c.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-BASKET"}, headers=BH)
check("F6 200", r.status_code == 200, r.status_code)
j = r.json()
check("F6 fully allocated", j["total_allocated"] == 5000, j["total_allocated"])
check("F6 multi-artisan", len(j["allocations"]) >= 2, len(j["allocations"]))
check("F6 solve time recorded", j["solve_time_ms"] is not None and j["solve_time_ms"] < 5000,
      j["solve_time_ms"])
shap = [a["payment_share_inr"] for a in j["allocations"]]
prop = [a["proportional_share_inr"] for a in j["allocations"]]
check("F6 shapley != proportional", shap != prop, f"shapley={shap} prop={prop}")
check("F6 fairness_check ok", j["raw_result"]["fairness_check"]["no_artisan_over_capacity"]
      and j["raw_result"]["fairness_check"]["payment_shares_sum_to_total"],
      j["raw_result"].get("fairness_check"))
check("F6 per-artisan rationale", all(a.get("allocation_rationale") and a.get("payment_rationale")
                                     for a in j["raw_result"]["allocations"]))
oid = j["order_id"]
r = c.post("/api/order/allocate", json={"order_id": oid})
check("F6 allocate commit", r.status_code == 200 and r.json()["status"] in
      ("fully_allocated", "partially_allocated"), r.json().get("status"))

print("\n== Business Copilot + dashboard ==")
r = c.get("/api/artisan/ART-MEERA/insights")
check("copilot 200", r.status_code == 200, r.status_code)
check("copilot cards", len(r.json()["insights"]) >= 1, len(r.json()["insights"]))
r = c.get("/api/artisan/ART-MEERA/dashboard")
check("dashboard 200", r.status_code == 200 and "summary" in r.json())

print("\n== judge debug ==")
r = c.get("/api/debug/ai-runs/summary")
check("ai-runs summary", r.status_code == 200 and r.json()["total_runs"] > 0,
      r.json().get("total_runs"))
r = c.get("/api/debug/f7-explain", params={"q": "cotton"})
check("f7-explain rows", len(r.json()["rows"]) > 0)

print(f"\n{'='*50}\n  {PASS} passed, {FAIL} failed\n{'='*50}")
raise SystemExit(1 if FAIL else 0)
