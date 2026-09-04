"""Artisan, Product, ProductImage, ProductAttribute, Inventory (spec §11)."""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_col, updated_col


class Artisan(Base):
    __tablename__ = "artisan"

    artisan_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    language: Mapped[str] = mapped_column(String, default="hi", nullable=False)
    region_id: Mapped[str] = mapped_column(ForeignKey("region.region_id"), nullable=False, index=True)
    cluster_id: Mapped[str | None] = mapped_column(
        ForeignKey("cluster.cluster_id"), nullable=True, index=True
    )
    onboarded_at = created_col()
    kyc_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    # F6 inputs
    reliability_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    monthly_capacity_units: Mapped[int] = mapped_column(Integer, default=400, nullable=False)
    logistics_cost_per_unit_inr: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    # F7 exposure-fairness inputs
    verified_sales_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avatar_seed: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at = updated_col()

    cluster: Mapped["Cluster"] = relationship(back_populates="artisans")
    region: Mapped["Region"] = relationship()
    products: Mapped[list["Product"]] = relationship(
        back_populates="artisan", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "product"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    artisan_id: Mapped[str] = mapped_column(
        ForeignKey("artisan.artisan_id"), nullable=False, index=True
    )
    craft_id: Mapped[str | None] = mapped_column(
        ForeignKey("craft.craft_id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String, default="Untitled product", nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String, default="draft", nullable=False, index=True)
    # draft | analyzing | catalogued | priced | published | archived
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    seo_title: Mapped[str | None] = mapped_column(String, nullable=True)
    seo_keywords: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dimensions: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # cached embedding for F7 semantic search (JSON array — pgvector in prod)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = created_col()
    updated_at = updated_col()

    artisan: Mapped[Artisan] = relationship(back_populates="products")
    craft: Mapped["Craft"] = relationship(back_populates="products")
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", cascade="all, delete-orphan",
        order_by="ProductImage.created_at",
    )
    attributes: Mapped[list["ProductAttribute"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )
    listing: Mapped["Listing"] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )
    passport: Mapped["CraftPassport"] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )
    inventory: Mapped["Inventory"] = relationship(
        back_populates="product", uselist=False, cascade="all, delete-orphan"
    )


class ProductImage(Base):
    __tablename__ = "product_image"

    image_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("product.product_id"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    enhanced_url: Mapped[str | None] = mapped_column(String, nullable=True)
    mask_url: Mapped[str | None] = mapped_column(String, nullable=True)
    readiness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    component_scores: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = created_col()

    product: Mapped[Product] = relationship(back_populates="images")


class ProductAttribute(Base):
    __tablename__ = "product_attribute"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("product.product_id"), nullable=False, index=True
    )
    attribute_key: Mapped[str] = mapped_column(String, nullable=False)
    attribute_value: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, default="manual", nullable=False)  # voice|visual|manual
    grounding_status: Mapped[str] = mapped_column(String, default="unverified", nullable=False)
    visual_consistency: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at = created_col()

    product: Mapped[Product] = relationship(back_populates="attributes")


class Inventory(Base):
    __tablename__ = "inventory"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("product.product_id"), primary_key=True
    )
    available_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at = updated_col()

    product: Mapped[Product] = relationship(back_populates="inventory")
