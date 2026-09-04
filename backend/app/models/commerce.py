"""Buyer, BuyerRequirement, Order, OrderAllocation (spec §8, §11)."""
from __future__ import annotations

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_col, updated_col


class Buyer(Base):
    __tablename__ = "buyer"

    buyer_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, default="B2B", nullable=False)  # B2B|government|retail
    phone: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reliability_weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    contact_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_col()

    requirements: Mapped[list["BuyerRequirement"]] = relationship(
        back_populates="buyer", cascade="all, delete-orphan"
    )


class BuyerRequirement(Base):
    __tablename__ = "buyer_requirement"

    requirement_id: Mapped[str] = mapped_column(String, primary_key=True)
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyer.buyer_id"), nullable=False, index=True)
    craft_id: Mapped[str | None] = mapped_column(ForeignKey("craft.craft_id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    required_material: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_min: Mapped[float] = mapped_column(Float, nullable=False)
    price_max: Mapped[float] = mapped_column(Float, nullable=False)
    deadline: Mapped[Date] = mapped_column(Date, nullable=False)
    fulfillment_min: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    lambda_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = created_col()

    buyer: Mapped[Buyer] = relationship(back_populates="requirements")
    orders: Mapped[list["Order"]] = relationship(back_populates="requirement")


class Order(Base):
    __tablename__ = "b2b_order"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    requirement_id: Mapped[str | None] = mapped_column(
        ForeignKey("buyer_requirement.requirement_id"), nullable=True, index=True
    )
    buyer_id: Mapped[str] = mapped_column(ForeignKey("buyer.buyer_id"), nullable=False, index=True)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    total_allocated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String, default="proposed", nullable=False, index=True)
    # proposed | confirmed | partially_allocated | fully_allocated | cancelled
    total_cost_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_buyer_payment_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    objective_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    solve_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    solver: Mapped[str | None] = mapped_column(String, nullable=True)
    revenue_allocation_method: Mapped[str] = mapped_column(
        String, default="shapley_value", nullable=False
    )
    fulfillment_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    optimization_meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = created_col()
    updated_at = updated_col()

    requirement: Mapped["BuyerRequirement"] = relationship(back_populates="orders")
    allocations: Mapped[list["OrderAllocation"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderAllocation(Base):
    __tablename__ = "order_allocation"

    allocation_id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("b2b_order.order_id"), nullable=False, index=True)
    artisan_id: Mapped[str] = mapped_column(ForeignKey("artisan.artisan_id"), nullable=False, index=True)
    allocated_units: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_inr: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost_inr: Mapped[float] = mapped_column(Float, nullable=False)
    payment_share_inr: Mapped[float] = mapped_column(Float, nullable=False)
    proportional_share_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shapley_marginal: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="proposed", nullable=False)
    # proposed | accepted | declined
    created_at = created_col()
    updated_at = updated_col()

    order: Mapped[Order] = relationship(back_populates="allocations")
