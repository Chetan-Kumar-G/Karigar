"""Train the F4 LightGBM price regressor on synthetic-but-realistic data.

Run once at seed time (``python -m app.ai.f4_pricing.train``) — writes
``data/models/f4_price.txt``.  The synthetic generator encodes the *intended*
economics (a fair price rises with making-cost, craft rarity, quality and
demand, and is pulled — but only partly — toward the category market median),
so the tree ensemble learns a genuine multivariate response surface rather
than a hand-written formula.  If the booster file is missing, inference falls
back to a deterministic formula (see ``pricing.py``) and says so.
"""
from __future__ import annotations

import numpy as np

from app.core.config import MODEL_DIR
from app.core.logging import get_logger

log = get_logger("f4.train")
MODEL_PATH = MODEL_DIR / "f4_price.txt"
N = 9000
RNG = np.random.default_rng(26090)


def _synthesize(n: int = N):
    material = RNG.uniform(60, 900, n)
    hours = RNG.uniform(1.5, 40, n)
    rate = RNG.uniform(45, 110, n)
    packaging = RNG.uniform(15, 120, n)
    logistics = RNG.uniform(20, 160, n)
    labour = hours * rate
    base = material + labour + packaging + logistics

    median = base * RNG.uniform(0.75, 1.9, n)            # market comparable
    seasonality = RNG.uniform(0.85, 1.25, n)
    rarity = RNG.uniform(0.05, 0.95, n)
    quality = RNG.uniform(0.35, 0.98, n)
    demand = RNG.uniform(0.05, 0.95, n)

    # "fair" target: cost-plus, then nudged by market + craft signals
    margin = 0.18 + 0.22 * rarity + 0.12 * quality + 0.10 * demand
    fair = base * (1 + margin)
    fair = 0.65 * fair + 0.35 * median * (0.9 + 0.25 * seasonality)
    fair *= 1 + RNG.normal(0, 0.04, n)
    fair = np.maximum(fair, base * 1.05)

    X = np.column_stack(
        [material, labour, packaging, logistics, base, median,
         seasonality, rarity, quality, demand]
    )
    return X.astype(np.float32), fair.astype(np.float32)


def train() -> str:
    import lightgbm as lgb

    X, y = _synthesize()
    cut = int(0.85 * len(y))
    dtrain = lgb.Dataset(X[:cut], label=y[:cut])
    dval = lgb.Dataset(X[cut:], label=y[cut:], reference=dtrain)
    params = dict(
        objective="regression_l1",
        metric="l1",
        num_leaves=31,
        learning_rate=0.05,
        feature_fraction=0.9,
        bagging_fraction=0.9,
        bagging_freq=1,
        min_data_in_leaf=40,
        verbose=-1,
    )
    booster = lgb.train(
        params, dtrain, num_boost_round=400, valid_sets=[dval],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )
    pred = booster.predict(X[cut:])
    mae = float(np.mean(np.abs(pred - y[cut:])))
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(MODEL_PATH))
    log.info("F4 LightGBM trained — holdout MAE ₹%.1f — saved %s", mae, MODEL_PATH)
    return str(MODEL_PATH)


if __name__ == "__main__":  # pragma: no cover
    train()
