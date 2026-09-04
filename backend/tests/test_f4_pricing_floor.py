"""F4 — the recommended price must NEVER fall below the sustainable floor (spec §30)."""
from __future__ import annotations

import random

import pytest

from app.ai.f4_pricing.features import PriceFeatures
from app.ai.f4_pricing.pricing import predict, sustainable_floor


def test_floor_formula_matches_spec():
    f = PriceFeatures(100, 5, 50, 20, 10, category_median_price_inr=500)
    # base = 100 + 250 + 20 + 10 = 380 ; floor = 380 / (1 - 0.18)
    assert round(sustainable_floor(f, 0.18)) == round(380 / 0.82)


def test_recommended_never_below_floor_randomised():
    rng = random.Random(0)
    for _ in range(400):
        f = PriceFeatures(
            material_cost_inr=rng.uniform(20, 1200),
            labour_hours=rng.uniform(0.5, 50),
            labour_rate_inr_per_hour=rng.uniform(30, 150),
            packaging_cost_inr=rng.uniform(0, 200),
            logistics_cost_inr=rng.uniform(0, 200),
            category_median_price_inr=rng.uniform(10, 400),  # deliberately low market
            rarity_score=rng.random(), quality_score=rng.random(), demand_index=rng.random(),
        )
        out = predict(f).data
        assert out["recommended_price_inr"] >= out["sustainable_floor_inr"]
        assert out["competitive_range_inr"][0] >= out["sustainable_floor_inr"]


def test_low_market_makes_floor_binding():
    f = PriceFeatures(400, 10, 80, 50, 60, category_median_price_inr=150)
    out = predict(f).data
    assert out["floor_is_binding"] is True
    assert out["recommended_price_inr"] == out["sustainable_floor_inr"]


@pytest.mark.parametrize("margin", [0.1, 0.15, 0.2, 0.3])
def test_custom_margin_respected(margin):
    f = PriceFeatures(200, 8, 60, 30, 20, category_median_price_inr=900)
    out = predict(f, min_margin=margin).data
    base = f.base_cost_inr
    assert out["sustainable_floor_inr"] == round(base / (1 - margin))


# ── Phase 10 edge cases — the floor guarantee must hold at the extremes ──
def _ok(out):
    assert out["recommended_price_inr"] >= out["sustainable_floor_inr"]
    assert out["competitive_range_inr"][0] >= out["sustainable_floor_inr"]
    assert out["pricing_pipeline"][-1]["stage"] == "final"
    assert out["pricing_pipeline"][2]["stage"] == "cost_floor"
    assert "SYNTHETIC" in out["training_data_note"] or "synthetic" in out["training_data_note"]


def test_extremely_low_cost():
    f = PriceFeatures(1, 0.1, 5, 0, 0, category_median_price_inr=800)
    _ok(predict(f).data)


def test_extremely_high_cost():
    f = PriceFeatures(50000, 200, 500, 2000, 3000, category_median_price_inr=1200)
    out = predict(f).data
    _ok(out)
    assert out["floor_is_binding"] is True  # nobody in the market pays this


def test_unusually_low_predicted_market_price():
    f = PriceFeatures(600, 12, 90, 40, 40, category_median_price_inr=5)
    out = predict(f).data
    _ok(out)
    assert out["floor_is_binding"] is True
    assert out["recommended_price_inr"] == out["sustainable_floor_inr"]


def test_unusually_high_predicted_market_price():
    f = PriceFeatures(200, 6, 60, 20, 20, category_median_price_inr=100000)
    out = predict(f).data
    _ok(out)
    # a runaway market number is capped, not blindly followed
    assert out["recommended_price_inr"] <= out["market_price_cap_inr"]


def test_zero_market_median_does_not_crash():
    f = PriceFeatures(300, 8, 70, 30, 30, category_median_price_inr=0)
    _ok(predict(f).data)
