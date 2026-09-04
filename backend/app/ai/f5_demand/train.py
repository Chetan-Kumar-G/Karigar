"""Train F5 demand forecasters (LightGBM quantile regression).

Writes ``data/models/f5_q{10,50,90}.txt``.  Trained on a synthetic daily-demand
generator (trend + weekly + annual seasonality + festival spikes + noise) — the
prototype's demand history is openly **SIMULATED_DATA** (spec §7 cold-start rule);
the *model code* is real and identical to what production would run on live data.
"""
from __future__ import annotations

import numpy as np

from app.core.config import MODEL_DIR
from app.core.logging import get_logger

log = get_logger("f5.train")
RNG = np.random.default_rng(5090)
FEATURES = ["month", "dow", "lag_7", "lag_30", "roll_14", "roll_30", "festival", "trend"]


def _series(days: int, base: float, trend: float, seas_amp: float) -> np.ndarray:
    t = np.arange(days)
    weekly = 1 + 0.18 * np.sin(2 * np.pi * t / 7)
    annual = 1 + seas_amp * np.sin(2 * np.pi * (t % 365) / 365 - 1.0)
    festival = np.where((t % 365 > 250) & (t % 365 < 300), 1.55, 1.0)  # Oct–Nov peak
    level = base * (1 + trend * t / days)
    noise = RNG.normal(1, 0.12, days)
    return np.maximum(1, level * weekly * annual * festival * noise)


def _make_dataset():
    rows_X, rows_y = [], []
    for _ in range(60):  # 60 synthetic category/region series
        days = 540
        s = _series(days, RNG.uniform(4, 40), RNG.uniform(-0.2, 0.8), RNG.uniform(0.15, 0.5))
        for i in range(40, days):
            month = (i % 365) // 30 + 1
            dow = i % 7
            festival = 1.0 if 250 < i % 365 < 300 else 0.0
            trend = (s[i - 1] - s[i - 30]) / 30.0
            rows_X.append([month, dow, s[i - 7], s[i - 30],
                           s[i - 14:i].mean(), s[i - 30:i].mean(), festival, trend])
            rows_y.append(s[i])
    return np.array(rows_X, np.float32), np.array(rows_y, np.float32)


def train() -> list[str]:
    import lightgbm as lgb

    X, y = _make_dataset()
    cut = int(0.85 * len(y))
    paths = []
    for q, tag in [(0.1, "q10"), (0.5, "q50"), (0.9, "q90")]:
        dtrain = lgb.Dataset(X[:cut], label=y[:cut])
        params = dict(objective="quantile", alpha=q, num_leaves=31, learning_rate=0.05,
                      min_data_in_leaf=30, feature_fraction=0.9, verbose=-1)
        booster = lgb.train(params, dtrain, num_boost_round=300)
        p = MODEL_DIR / f"f5_{tag}.txt"
        booster.save_model(str(p))
        paths.append(str(p))
    pred = lgb.Booster(model_file=paths[1]).predict(X[cut:])
    log.info("F5 quantile models trained - holdout MAE %.2f units - saved %s",
             float(np.mean(np.abs(pred - y[cut:]))), MODEL_DIR)
    return paths


if __name__ == "__main__":  # pragma: no cover
    train()
