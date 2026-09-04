"""F5 — Demand & Market Opportunity Intelligence.

**Mode: REAL model, SIMULATED_DATA history.**  LightGBM quantile regressors
(0.1 / 0.5 / 0.9) roll a daily forecast forward over the window; the point
forecast is the 0.5 sum, the confidence interval the 0.1 / 0.9 sums.  A
deterministic seasonal-naive + trend formula is the fallback when the model
files are absent.

The **prediction → action translation layer** (spec §7.C) converts the forecast
delta into a concrete unit/deadline instruction, scaled to the artisan's own
monthly capacity so the advice is actionable, not a raw chart.
"""
from __future__ import annotations

import datetime as dt

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import REAL, SIMULATED_DATA, AiResult, timed
from app.core.config import MODEL_DIR
from app.models.market import DemandSignal

_TAGS = ["q10", "q50", "q90"]
_BOOSTERS: dict[str, object] = {}
_TRIED = False


def _load():
    global _TRIED
    if _TRIED:
        return _BOOSTERS
    _TRIED = True
    try:
        import lightgbm as lgb

        for tag in _TAGS:
            p = MODEL_DIR / f"f5_{tag}.txt"
            if p.exists():
                _BOOSTERS[tag] = lgb.Booster(model_file=str(p))
    except Exception:
        pass
    return _BOOSTERS


def _history(db: Session, category: str, region_id: str | None) -> np.ndarray:
    q = select(DemandSignal).where(DemandSignal.category == category)
    if region_id:
        q = q.where(DemandSignal.region_id == region_id)
    rows = sorted(db.scalars(q).all(), key=lambda r: r.date)
    if not rows:
        return np.array([])
    return np.array([max(1, r.units_sold or r.order_count or 1) for r in rows], dtype=float)


def _roll_forward(series: np.ndarray, horizon: int, boosters) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    s = list(series[-60:]) if len(series) >= 60 else list(series)
    while len(s) < 40:
        s.insert(0, s[0] if s else 5.0)
    lo, mid, hi = [], [], []
    start_day = len(series)
    for k in range(horizon):
        i = start_day + k
        month = (i % 365) // 30 + 1
        dow = i % 7
        festival = 1.0 if 250 < i % 365 < 300 else 0.0
        trend = (s[-1] - s[-30]) / 30.0 if len(s) >= 30 else 0.0
        feat = np.array([[month, dow, s[-7], s[-30] if len(s) >= 30 else s[0],
                          np.mean(s[-14:]), np.mean(s[-30:]) if len(s) >= 30 else np.mean(s),
                          festival, trend]], dtype=np.float32)
        if boosters:
            p10 = float(boosters["q10"].predict(feat)[0])
            p50 = float(boosters["q50"].predict(feat)[0])
            p90 = float(boosters["q90"].predict(feat)[0])
        else:  # seasonal-naive + trend fallback
            seasonal = s[-7] if len(s) >= 7 else np.mean(s)
            p50 = max(1.0, seasonal * (1 + 0.02) * (1.4 if festival else 1.0))
            p10, p90 = p50 * 0.8, p50 * 1.25
        p10, p50, p90 = sorted((p10, p50, p90))
        lo.append(p10); mid.append(p50); hi.append(p90)
        s.append(p50)
    return np.array(lo), np.array(mid), np.array(hi)


def forecast(
    db: Session,
    category: str,
    *,
    region_id: str | None = None,
    window_days: int = 30,
    artisan_monthly_capacity: int = 400,
    recent_production: int | None = None,
) -> AiResult:
    with timed() as t:
        boosters = _load()
        series = _history(db, category, region_id)
        have_history = series.size >= 30

        lo, mid, hi = _roll_forward(
            series if series.size else np.array([6.0] * 40), window_days, boosters
        )
        pred = int(round(mid.sum()))
        ci_low, ci_high = int(round(lo.sum())), int(round(hi.sum()))

        if series.size >= 60:
            prior = series[-2 * window_days:-window_days].sum() if series.size >= 2 * window_days \
                else series[:window_days].sum()
            trend_pct = round(100 * (mid.sum() - prior) / max(prior, 1), 1)
        else:
            trend_pct = round(float(np.clip((mid[-1] - mid[0]) / max(mid[0], 1) * 100, -40, 60)), 1)

        # ── prediction → action translation ──────────────────────────────
        baseline = recent_production if recent_production is not None else int(
            series[-window_days:].sum()) if series.size >= window_days else pred
        gap = max(0, pred - baseline)
        capacity_room = max(0, artisan_monthly_capacity - baseline)
        recommended_units = int(min(gap, capacity_room, artisan_monthly_capacity * 0.4))
        recommended_units = int(round(recommended_units / 5) * 5)
        window_start = dt.date.today()
        deadline = window_start + dt.timedelta(days=max(7, window_days - 10))

        if recommended_units > 0:
            act_en = (f"Prepare {recommended_units} additional units before "
                      f"{deadline.strftime('%d %B')}.")
            act_hi = (f"{deadline.strftime('%d %B')} से पहले {recommended_units} अतिरिक्त "
                      f"इकाइयाँ तैयार करें।")
        else:
            act_en = "Demand is steady. Keep your current production rate."
            act_hi = "माँग स्थिर है। अपनी वर्तमान उत्पादन दर बनाए रखें।"

        seasonal_idx = round(float(1.4 if 250 < window_start.timetuple().tm_yday < 300 else
                                   1.0 + 0.2 * np.sin(2 * np.pi * window_start.timetuple().tm_yday / 365)), 2)

        data = {
            "category": category,
            "region_id": region_id,
            "forecast_window_days": window_days,
            "predicted_demand_units": pred,
            "trend_pct": trend_pct,
            "confidence_interval": [ci_low, ci_high],
            "seasonal_index": seasonal_idx,
            "history_points": int(series.size),
            "data_basis": "live_history" if have_history else "cold_start_prior",
            "is_simulated": True,
            "simulated_note": "Demo forecast based on sample historical data (spec §7). "
                              "Not live national-marketplace data.",
            "daily_curve": {"p50": [round(x, 1) for x in mid.tolist()],
                            "p10": [round(x, 1) for x in lo.tolist()],
                            "p90": [round(x, 1) for x in hi.tolist()]},
            "action_recommendation": {
                "text_en": act_en, "text_hi": act_hi,
                "recommended_additional_units": recommended_units,
                "deadline": deadline.isoformat(),
            },
            "model_meta": {
                "point_model": "LightGBM quantile (alpha=0.5)" if boosters else "seasonal-naive+trend",
                "interval_model": "LightGBM quantile (alpha=0.1/0.9)" if boosters else "±20/25% band",
            },
        }
    return AiResult(
        data=data, feature="F5",
        model="LightGBM quantile regression (real model, simulated history)" if boosters
        else "Seasonal-naive + trend (fallback)",
        mode=SIMULATED_DATA if boosters else REAL,
        inputs={"category": category, "region_id": region_id or "", "window_days": window_days,
                "artisan_monthly_capacity": artisan_monthly_capacity},
        latency_ms=t["ms"],
    )
