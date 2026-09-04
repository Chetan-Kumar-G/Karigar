"""Trust & Verification — cards, reviewer state machine, complaints, F6 gate."""
from __future__ import annotations


def test_public_artisan_card_hides_no_and_lists_badges(client):
    r = client.get("/api/trust/artisan/ART-MEERA")
    assert r.status_code == 200
    card = r.json()
    assert card["verification_status"] == "VERIFIED"
    # GI is its own axis — pending, not "certified" just for being a GI craft
    assert card["gi_status"] == "pending_verification"
    labels = [b["label"] for b in card["badges"]]
    assert "Verified Artisan" in labels
    assert any("GI" in x for x in labels)
    # never leaks a raw KYC document field
    assert "kyc_document" not in card and "gov_kyc" not in card


def test_business_card(client):
    r = client.get("/api/trust/business/BUY-TAJHOTEL").json()
    assert r["verification_status"] == "VERIFIED"
    assert r["b2b_eligible"] is True


def test_reviewer_state_machine_and_risk_flag(client):
    q = client.get("/api/trust/reviewer/queue").json()
    row = next(x for x in q["queue"] if x["subject_id"] == "ART-RupA")
    pid = row["profile_id"]
    assert row["verification_status"] == "PENDING"

    # reviewer detail exposes F1/F2/F3 signals for the decision
    d = client.get(f"/api/trust/reviewer/{pid}").json()
    assert "reviewer_view" in d and d["reviewer_view"]["products"]

    # approve → VERIFIED
    a = client.post(f"/api/trust/reviewer/{pid}/action", json={"action": "approve"}).json()
    assert a["status"] == "VERIFIED"

    # buyer complaint → AI risk flag → UNDER_REVIEW (never an auto-ban)
    c = client.post("/api/trust/complaints", json={
        "subject_id": "ART-RupA", "category": "product_not_as_described",
        "description": "colour mismatch"}).json()
    assert c["complaint"]["risk_flag"]
    assert c["risk_flag_result"]["moved_to_under_review"] is True
    assert client.get(f"/api/trust/reviewer/{pid}").json()["verification_status"] == "UNDER_REVIEW"

    # human decides: suspend then reinstate
    assert client.post(f"/api/trust/reviewer/{pid}/action",
                       json={"action": "suspend", "note": "investigating"}).json()["status"] == "SUSPENDED"
    assert client.post(f"/api/trust/reviewer/{pid}/action",
                       json={"action": "reinstate"}).json()["status"] == "REINSTATED"

    # illegal transition is refused (REINSTATED → REINSTATED)
    bad = client.post(f"/api/trust/reviewer/{pid}/action", json={"action": "reinstate"})
    assert bad.status_code == 409


def test_reliability_score_is_explainable(client):
    r = client.get("/api/trust/reliability/ART-SUNITA").json()
    assert 0 <= r["reliability_score"] <= 100
    terms = r["breakdown"]["terms"]
    assert abs(sum(terms.values()) + 7.0 - r["reliability_score"]) < 0.5


def test_f6_eligibility_trace_present_and_demo_still_fills(client):
    tok = client.post("/api/auth/otp/verify",
                      json={"phone": "9900000001", "otp": "123456", "role": "buyer"}
                      ).json()["access_token"]
    m = client.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-BASKET"},
                    headers={"Authorization": f"Bearer {tok}"}).json()
    assert m["total_allocated"] == 5000
    trace = m["raw_result"]["eligibility_trace"]
    assert trace["eligible"] >= 2
    assert "verification_ok" in trace
    for al in m["allocations"]:
        assert "verification_status" in al


def test_b2b_order_commitment_is_simulated(client):
    tok = client.post("/api/auth/otp/verify",
                      json={"phone": "9900000001", "otp": "123456", "role": "buyer"}
                      ).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    oid = client.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-BASKET"},
                      headers=H).json()["order_id"]
    cm = client.get(f"/api/order/{oid}/commitment").json()
    assert cm["is_simulated"] is True
    assert [m["pct"] for m in cm["payment_milestones"]] == [20, 30, 30, 20]
    canc = client.post(f"/api/order/{oid}/commitment/cancel", json={"by": "buyer"}).json()
    assert "consequence" in canc and canc["commitment_status"] == "CANCELLED_BY_BUYER"
