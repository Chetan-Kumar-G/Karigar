"""F7 — exposure-fairness re-ranking behaviour (spec §9, §32)."""
from __future__ import annotations

from app.ai.f7_ranking.ranking import Candidate, rank


def _c(lid, sales, exposure, underserved, text="handwoven cotton dupatta madhubani"):
    return Candidate(lid, f"P{lid}", text, "Madhubani", "Bihar", f"Artisan {lid}",
                     600, 4.5, 0.8, sales, underserved, exposure)


def test_new_seller_ranked_above_established_when_relevance_equal():
    cands = [_c("established", sales=120, exposure=90, underserved=0.3),
             _c("newbie", sales=0, exposure=1, underserved=0.3)]
    out = rank("handwoven cotton dupatta madhubani", cands).data
    assert out["results"][0]["listing_id"] == "newbie"


def test_fairness_off_reverses_it():
    cands = [_c("established", 120, 90, 0.3), _c("newbie", 0, 1, 0.3)]
    on = rank("handwoven cotton dupatta madhubani", cands, apply_fairness=True).data
    off = rank("handwoven cotton dupatta madhubani", cands, apply_fairness=False).data
    assert on["results"][0]["listing_id"] == "newbie"
    assert off["fairness_applied"] is False


def test_new_seller_boost_decays_to_zero_past_threshold():
    cands = [_c("x", sales=999, exposure=1, underserved=0.5)]
    b = rank("cotton", cands).data["results"][0]["score_breakdown"]
    assert b["new_seller_boost"] == 0.0


def test_breakdown_has_all_terms():
    out = rank("cotton dupatta", [_c("a", 0, 1, 0.5)]).data
    b = out["results"][0]["score_breakdown"]
    for k in ("relevance", "new_seller_boost", "underserved_region_boost",
              "exposure_penalty", "final_score", "fairness_adjustment"):
        assert k in b


def test_irrelevant_query_still_returns_ranked_list():
    out = rank("zzz nonsense", [_c("a", 0, 1, 0.5), _c("b", 50, 5, 0.5)]).data
    assert len(out["results"]) == 2


def test_exposure_gap_metric_present():
    cands = [_c("e", 120, 90, 0.3), _c("n", 0, 1, 0.3)]
    out = rank("handwoven cotton", cands).data
    assert "gap" in out["exposure_gap_metric"]
