"""Pricing history, market prices, demand signals & forecasts (spec §11).

DemandSignal / DemandForecast rows produced for the prototype are flagged
``is_simulated=True`` (spec §7 cold-start honesty rule).
"""
from __future__ import annotations

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_col


class PriceHistory(Base):
    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("product.product_id"), nullable=False, index=True
    )
    price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, default="recommended", nullable=False)
    # recommended | actual_sale | listed
    recorded_at = created_col()


class MarketPrice(Base):
    __tablename__ = "market_price"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    craft_id: Mapped[str | None] = mapped_column(ForeignKey("craft.craft_id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("region.region_id"), nullable=True)
    median_price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    p25_price_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    p75_price_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_note: Mapped[str] = mapped_column(
        String, default="Curated comparable table (demo data)", nullable=False
    )
    observed_at = created_col()


class DemandSignal(Base):
    __tablename__ = "demand_signal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("region.region_id"), nullable=True, index=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    browse_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    order_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    units_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DemandForecast(Base):
    __tablename__ = "demand_forecast"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("region.region_id"), nullable=True)
    forecast_window_start: Mapped[Date] = mapped_column(Date, nullable=False)
    forecast_window_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    predicted_units: Mapped[int] = mapped_column(Integer, nullable=False)
    trend_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_interval_low: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence_interval_high: Mapped[int] = mapped_column(Integer, nullable=False)
    seasonal_index: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    top_regions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    action_recommendation: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    model_meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = created_col()
