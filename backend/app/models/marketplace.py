"""Listing, Exposure, Interaction + AiRun audit log (spec §11, §45)."""
from __future__ import annotations

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_col, updated_col


class Listing(Base):
    __tablename__ = "listing"

    listing_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("product.product_id"), nullable=False, unique=True, index=True
    )
    current_price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    sustainable_floor_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    competitive_low_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    competitive_high_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    premium_opportunity_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=4.4, nullable=False)
    rating_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    exposure_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    impressions_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at = created_col()
    updated_at = updated_col()

    product: Mapped["Product"] = relationship(back_populates="listing")


class Exposure(Base):
    __tablename__ = "exposure"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listing.listing_id"), nullable=False, index=True)
    date: Mapped[Date] = mapped_column(Date, nullable=False, index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_seller_boost_applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Interaction(Base):
    __tablename__ = "interaction"

    interaction_id: Mapped[str] = mapped_column(String, primary_key=True)
    buyer_session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    listing_id: Mapped[str] = mapped_column(ForeignKey("listing.listing_id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # view | click | order
    query: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at = created_col()


class AiRun(Base):
    """Judge-facing technical metadata (spec §45): one row per AI invocation."""

    __tablename__ = "ai_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feature: Mapped[str] = mapped_column(String, nullable=False, index=True)  # F1..F7
    model: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[str] = mapped_column(String, default="prototype-v1", nullable=False)
    mode: Mapped[str] = mapped_column(String, default="REAL", nullable=False)
    # REAL | PROTOTYPE | SIMULATED_DATA | FALLBACK
    subject_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at = created_col()
