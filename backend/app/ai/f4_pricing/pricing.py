"""F4 — Fair Cost-Aware Multimodal Dynamic Pricing.

**Mode: REAL** when ``data/models/f4_price.txt`` exists (LightGBM inference +
native tree SHAP for the explanation), **FALLBACK** to a deterministic
cost-plus-market formula otherwise.  Either way the hard guarantee from
spec §6.I / §30 holds by construction::

    P_floor        = base_cost / (1 - m_min)
    P_recommended  = max( P_floor , clip( model_or_formula , P_floor , P_market_max ) )

so the recommended price is **never** below the sustainable floor.  There is a
unit test (`tests/test_pricing_floor.py`) asserting exactly this.
"""
from __future__ import annotations

import numpy as np

from app.ai.base import FALLBACK, REAL, AiResult, timed
from app.ai.f4_pricing.features import FACTOR_LABELS, FEATURE_ORDER, PriceFeatures
from app.core.config import MODEL_DIR, settings

MODEL_PATH = MODEL_DIR / "f4_price.txt"
_BOOSTER = None
_TRIED_LOAD = False


def _load_booster():
    global _BOOSTER, _TRIED_LOAD
    if _TRIED_LOAD:
        return _BOOSTER
    _TRIED_LOAD = True
    if MODEL_PATH.exists():
        try:
            import lightgbm as lgb

            _BOOSTER = lgb.Booster(model_file=str(MODEL_PATH))
        except Exception:  # pragma: no cover
            _BOOSTER = None
    return _BOOSTER


def sustainable_floor(f: PriceFeatures, min_margin: float | None = None) -> float:
    m = settings.pricing_min_margin if min_margin is None else min_margin
    return f.base_cost_inr / (1.0 - m)


def _formula_price(f: PriceFeatures) -> float:
    """Deterministic fallback — same economic shape the LightGBM target encodes."""
    margin = 0.18 + 0.22 * f.rarity_score + 0.12 * f.quality_score + 0.10 * f.demand_index
    cost_plus = f.base_cost_inr * (1 + margin)
    blended = 0.65 * cost_plus + 0.35 * f.category_median_price_inr * (0.9 + 0.25 * f.seasonality_index)
    return float(blended)


def _model_price_and_factors(f: PriceFeatures):
    booster = _load_booster()
    if booster is None:
        return _formula_price(f), _fallback_factors(f), FALLBACK
    x = np.array([f.vector()], dtype=np.float32)
    pred = float(booster.predict(x)[0])
    contrib = booster.predict(x, pred_contrib=True)[0]  # native tree SHAP
    pairs = sorted(
        zip(FEATURE_ORDER, contrib[:-1]), key=lambda kv: abs(kv[1]), reverse=True
    )
    pos = [FACTOR_LABELS[k] for k, v in pairs if v > 0][:3]
    neg = [FACTOR_LABELS[k] for k, v in pairs if v < 0][:3]
    shap = {FACTOR_LABELS[k]: round(float(v), 1) for k, v in pairs[:6]}
    return pred, {"top_positive_factors": pos, "top_negative_factors": neg, "shap": shap}, REAL


def _fallback_factors(f: PriceFeatures) -> dict:
    signals = {
        "Craft rarity": f.rarity_score,
        "Product quality": f.quality_score,
        "Demand": f.demand_index,
        "Total making cost": f.base_cost_inr / max(f.category_median_price_inr, 1),
        "Market competition": -f.category_median_price_inr / max(f.base_cost_inr, 1) / 3,
    }
    ranked = sorted(signals.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return {
        "top_positive_factors": [k for k, v in ranked if v > 0][:3],
        "top_negative_factors": [k for k, v in ranked if v < 0][:3],
        "shap": {k: round(float(v), 2) for k, v in ranked[:5]},
    }


def predict(f: PriceFeatures, min_margin: float | None = None) -> AiResult:
    with timed() as t:
        floor = sustainable_floor(f, min_margin)
        raw, factors, mode = _model_price_and_factors(f)

        market_max = max(f.category_median_price_inr * 2.1, floor * 1.8)
        recommended = max(floor, float(np.clip(raw, floor, market_max)))

        comp_low = max(floor, round(min(recommended, f.category_median_price_inr) * 0.92))
        comp_high = round(max(recommended, f.category_median_price_inr) * 1.28)
        premium = round(max(comp_high, recommended * 1.16))

        floor_binding = raw < floor
        model_clipped_high = raw > market_max
        confidence = 0.74 if mode == REAL else 0.6
        if f.category_median_price_inr <= 0:
            confidence -= 0.15

        # Explicit, ordered pipeline for the UI (Phase 10): inputs → market est →
        # cost floor → model prediction → hard floor clamp → final price.
        pipeline = [
            {"stage": "inputs", "label": "Your costs + craft signals",
             "value_inr": round(f.base_cost_inr),
             "detail": f"material ₹{round(f.material_cost_inr)} + labour ₹{round(f.labour_cost_inr)} "
                       f"+ packaging ₹{round(f.packaging_cost_inr)} + logistics ₹{round(f.logistics_cost_inr)}"},
            {"stage": "market_estimate", "label": "Estimated market price",
             "value_inr": round(f.category_median_price_inr) if f.category_median_price_inr > 0 else None,
             "detail": "category median (demo/synthetic market data)"},
            {"stage": "cost_floor", "label": "Sustainable cost floor",
             "value_inr": round(floor),
             "detail": f"base cost ÷ (1 − {round((settings.pricing_min_margin if min_margin is None else min_margin) * 100)}% min margin) — a HARD minimum"},
            {"stage": "model_prediction", "label":
             "LightGBM prediction" if mode == REAL else "Cost-plus-market formula",
             "value_inr": round(raw),
             "detail": "tree-SHAP explains the drivers below" if mode == REAL
             else "deterministic fallback (no trained model on disk)"},
            {"stage": "floor_clamp", "label": "Apply hard floor constraint",
             "value_inr": round(recommended),
             "detail": ("model price was BELOW the floor — raised to the floor"
                        if floor_binding else
                        "model price was above the floor — kept as-is"
                        if not model_clipped_high else
                        "model price was above the market cap — trimmed")},
            {"stage": "final", "label": "Recommended price",
             "value_inr": round(recommended),
             "detail": "never below the sustainable floor, by construction"},
        ]

        data = {
            "sustainable_floor_inr": round(floor),
            "competitive_range_inr": [round(comp_low), round(comp_high)],
            "recommended_price_inr": round(recommended),
            "premium_opportunity_inr": premium,
            "confidence": round(float(np.clip(confidence, 0.3, 0.95)), 2),
            "floor_is_binding": floor_binding,
            "model_clipped_to_market_cap": model_clipped_high,
            "raw_model_price_inr": round(raw),
            "market_price_cap_inr": round(market_max),
            "base_cost_inr": round(f.base_cost_inr),
            "min_margin_pct": round((settings.pricing_min_margin if min_margin is None else min_margin) * 100, 1),
            "explanation": factors,
            "pricing_pipeline": pipeline,
            "cost_breakdown": {
                "material": round(f.material_cost_inr),
                "labour": round(f.labour_cost_inr),
                "packaging": round(f.packaging_cost_inr),
                "logistics": round(f.logistics_cost_inr),
            },
            "why_plain": _plain_reason(f, recommended, floor_binding, factors),
            "training_data_note": (
                "Model trained on SYNTHETIC/demo data — it demonstrates the "
                "cost-aware pricing mechanism, not real-world price accuracy."
            ),
        }

    return AiResult(
        data=data,
        feature="F4",
        model="LightGBM price regressor + tree-SHAP" if mode == REAL
        else "Deterministic cost-plus-market formula",
        mode=mode,
        inputs={k: getattr(f, k, None) for k in (
            "material_cost_inr", "labour_hours", "labour_rate_inr_per_hour",
            "packaging_cost_inr", "logistics_cost_inr",
            "category_median_price_inr", "rarity_score", "quality_score", "demand_index",
        )},
        latency_ms=t["ms"],
    )


def _plain_reason(f: PriceFeatures, price: float, floor_binding: bool, factors: dict) -> str:
    if floor_binding:
        return (
            f"The market is selling similar items cheaply, but that price would not "
            f"cover your ₹{round(f.base_cost_inr)} making cost. We recommend ₹{round(price)} "
            f"so your work stays profitable."
        )
    drivers = ", ".join(factors.get("top_positive_factors", [])[:2]) or "your making cost"
    return (
        f"₹{round(price)} is fair for this piece — it covers your ₹{round(f.base_cost_inr)} "
        f"making cost and reflects {drivers.lower()}."
    )
