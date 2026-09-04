"""F6 — MILP allocation + Shapley payment split (spec §8, §31)."""
from __future__ import annotations

from app.ai.f6_matching.allocation import BuyerOrder, EligibleArtisan, allocate

POOL = [
    EligibleArtisan("A", "A", 1200, 210, 0.88, 0.91, 4),
    EligibleArtisan("B", "B", 800, 225, 0.80, 0.95, 6),
    EligibleArtisan("C", "C", 2000, 205, 0.85, 0.87, 3),
    EligibleArtisan("D", "D", 1500, 215, 0.90, 0.93, 5),
]


def test_full_allocation_meets_demand_exactly():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    assert out["total_allocated"] == 5000
    assert out["fulfillment_pct"] == 100.0
    assert sum(a["allocated_units"] for a in out["allocations"]) == 5000


def test_no_artisan_exceeds_capacity():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    cap = {a.artisan_id: a.capacity_units for a in POOL}
    for a in out["allocations"]:
        assert a["allocated_units"] <= cap[a["artisan_id"]]


def test_partial_when_capacity_short():
    small = [EligibleArtisan("A", "A", 300, 210, 0.8, 0.9, 4),
             EligibleArtisan("B", "B", 200, 220, 0.8, 0.9, 5)]
    out = allocate(BuyerOrder(5000, 200, 260), small).data
    assert out["status"] in ("partially_allocated",)
    assert out["total_allocated"] == 500
    assert out["shortfall_units"] == 4500


def test_price_ceiling_filters_expensive_artisans():
    pool = POOL + [EligibleArtisan("X", "X", 9999, 400, 0.99, 0.99, 1)]
    out = allocate(BuyerOrder(5000, 200, 250), pool).data
    assert "X" not in [a["artisan_id"] for a in out["allocations"]]


def test_shapley_sums_to_buyer_payment_and_differs_from_proportional():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    shap = sum(a["payment_share_inr"] for a in out["allocations"])
    assert abs(shap - out["total_buyer_payment_inr"]) <= len(out["allocations"]) + 1
    prop = [a["proportional_share_inr"] for a in out["allocations"]]
    shp = [a["payment_share_inr"] for a in out["allocations"]]
    assert shp != prop  # unequal quality/reliability ⇒ the two must diverge


def test_solver_is_fast():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    assert out["solve_time_ms"] < 3000
    assert out["solver"] == "cp_sat"


def test_greedy_baseline_present_for_comparison():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    assert "baseline_greedy" in out
    assert out["baseline_greedy"]["filled_units"] > 0


# ── Phase 12 hardening ─────────────────────────────────────────────────
def test_fairness_check_block_and_capacity_invariant():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    fc = out["fairness_check"]
    assert fc["no_artisan_over_capacity"] is True
    assert fc["all_shares_non_negative"] is True
    assert fc["payment_shares_sum_to_total"] is True


def test_one_artisan_unavailable_still_allocates():
    pool = [a for a in POOL if a.artisan_id != "C"]  # drop the biggest
    out = allocate(BuyerOrder(3000, 200, 260), pool).data
    assert out["total_allocated"] == 3000
    ids = {a["artisan_id"] for a in out["allocations"]}
    assert "C" not in ids


def test_shapley_symmetry_two_identical_artisans_get_equal_pay():
    twins = [
        EligibleArtisan("P", "P", 1000, 210, 0.85, 0.90, 5),
        EligibleArtisan("Q", "Q", 1000, 210, 0.85, 0.90, 5),
        EligibleArtisan("R", "R", 1000, 240, 0.70, 0.75, 9),
    ]
    out = allocate(BuyerOrder(1800, 200, 260), twins).data
    pay = {a["artisan_id"]: a["payment_share_inr"] for a in out["allocations"]}
    if "P" in pay and "Q" in pay:
        assert abs(pay["P"] - pay["Q"]) <= 2  # symmetry axiom


def test_greedy_fallback_used_when_cpsat_unavailable(monkeypatch):
    import app.ai.f6_matching.allocation as alloc_mod

    def boom(*_a, **_k):
        raise RuntimeError("simulated OR-Tools import failure")

    monkeypatch.setattr(alloc_mod, "_solve_cpsat", boom)
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    assert out["used_fallback"] is True
    assert out["solver"] == "greedy_fallback"
    assert out["total_allocated"] > 0
    cap = {a.artisan_id: a.capacity_units for a in POOL}
    for a in out["allocations"]:
        assert a["allocated_units"] <= cap[a["artisan_id"]]
    # Shapley still runs on the fallback allocation
    assert out["fairness_check"]["payment_shares_sum_to_total"] is True


def test_montecarlo_shapley_kicks_in_for_large_coalition(monkeypatch):
    import app.ai.f6_matching.allocation as alloc_mod

    monkeypatch.setattr(alloc_mod, "SHAPLEY_EXACT_MAX", 3)
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data  # 4 members > 3
    assert out["shapley_method"].startswith("montecarlo")
    assert out["fairness_check"]["payment_shares_sum_to_total"] is True


def test_allocation_and_payment_rationales_present():
    out = allocate(BuyerOrder(5000, 200, 250), POOL).data
    for a in out["allocations"]:
        assert a["allocation_rationale"]
        assert a["payment_rationale"]
        assert a["capacity_used_pct"] <= 100.0


def test_infeasible_zero_capacity_pool_is_handled():
    dead = [EligibleArtisan("Z", "Z", 0, 210, 0.8, 0.9, 4)]
    out = allocate(BuyerOrder(1000, 200, 260), dead).data
    assert out["status"] in ("no_eligible_artisans", "infeasible")
    assert out["total_allocated"] == 0
