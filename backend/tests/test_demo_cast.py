"""Named demo cast (Agneay/Cynthiya/Prarthana + Chetan/Prasannaa/Deeraj) must
stay wired end-to-end: login → bulk match splits 3 ways → artisan sees the order."""
from __future__ import annotations


def _tok(client, phone, role=None):
    body = {"phone": phone, "otp": "123456"}
    if role:
        body["role"] = role
    return client.post("/api/auth/otp/verify", json=body).json()["access_token"]


def test_cast_endpoint_all_present(client):
    j = client.get("/api/demo/cast").json()
    assert [b["name"] for b in j["buyers"]] == ["Agneay", "Cynthiya", "Prarthana"]
    assert [a["name"] for a in j["artisans"]] == ["Chetan", "Prasannaa", "Deeraj"]
    assert all(b["exists"] for b in j["buyers"])
    assert all(a["exists"] for a in j["artisans"])
    assert j["bulk_requirement_exists"] and j["small_requirement_exists"]


def test_agneay_bulk_order_splits_across_all_three_artisans(client):
    tok = _tok(client, "9600000001", "buyer")
    r = client.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-THJ"},
                    headers={"Authorization": f"Bearer {tok}"}).json()
    assert r["total_allocated"] == 2900
    names = {a["artisan_name"] for a in r["raw_result"]["allocations"]}
    assert names == {"Chetan", "Prasannaa", "Deeraj"}
    # every allocated artisan gets a positive, explained payment share
    for a in r["raw_result"]["allocations"]:
        assert a["payment_share_inr"] > 0
        assert a["payment_rationale"]
    assert r["raw_result"]["fairness_check"]["no_artisan_over_capacity"]


def test_artisan_prasannaa_sees_the_pooled_order(client):
    btok = _tok(client, "9600000001", "buyer")
    m = client.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-THJ"},
                    headers={"Authorization": f"Bearer {btok}"}).json()
    client.post("/api/order/allocate", json={"order_id": m["order_id"]},
                headers={"Authorization": f"Bearer {btok}"})
    _tok(client, "9700000002")  # Prasannaa logs in
    orders = client.get("/api/artisan/ART-PRASANNAA/orders").json()["orders"]
    assert any(o["order_id"] == m["order_id"] for o in orders)


def test_cynthiya_small_order_is_single_maker(client):
    tok = _tok(client, "9600000002", "buyer")
    r = client.post("/api/buyer/match", json={"requirement_id": "REQ-DEMO-THJ-SM"},
                    headers={"Authorization": f"Bearer {tok}"}).json()
    assert r["total_allocated"] == 60
    assert len(r["raw_result"]["allocations"]) == 1
