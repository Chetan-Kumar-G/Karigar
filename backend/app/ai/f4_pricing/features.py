"""Shared feature definition for F4 so training and inference never drift."""
from __future__ import annotations

from dataclasses import dataclass

FEATURE_ORDER = [
    "material_cost_inr",
    "labour_cost_inr",
    "packaging_cost_inr",
    "logistics_cost_inr",
    "base_cost_inr",
    "category_median_price_inr",
    "seasonality_index",
    "rarity_score",
    "quality_score",
    "demand_index",
]


@dataclass
class PriceFeatures:
    material_cost_inr: float
    labour_hours: float
    labour_rate_inr_per_hour: float
    packaging_cost_inr: float
    logistics_cost_inr: float
    category_median_price_inr: float
    seasonality_index: float = 1.0
    rarity_score: float = 0.5
    quality_score: float = 0.7
    demand_index: float = 0.5

    @property
    def labour_cost_inr(self) -> float:
        return self.labour_hours * self.labour_rate_inr_per_hour

    @property
    def base_cost_inr(self) -> float:
        return (
            self.material_cost_inr
            + self.labour_cost_inr
            + self.packaging_cost_inr
            + self.logistics_cost_inr
        )

    def vector(self) -> list[float]:
        return [
            self.material_cost_inr,
            self.labour_cost_inr,
            self.packaging_cost_inr,
            self.logistics_cost_inr,
            self.base_cost_inr,
            self.category_median_price_inr,
            self.seasonality_index,
            self.rarity_score,
            self.quality_score,
            self.demand_index,
        ]


# Human-facing labels for the "Why this price?" explanation (spec §12).
FACTOR_LABELS = {
    "material_cost_inr": "Material cost",
    "labour_cost_inr": "Labour",
    "packaging_cost_inr": "Packaging",
    "logistics_cost_inr": "Logistics",
    "base_cost_inr": "Total making cost",
    "category_median_price_inr": "Market competition",
    "seasonality_index": "Season",
    "rarity_score": "Craft rarity",
    "quality_score": "Product quality",
    "demand_index": "Demand",
}
