"""Geography + craft-knowledge-graph entities (spec §5, §11).

These tables *are* the Craft Knowledge Graph (F3).  At prototype scale we model
the graph relationally and traverse it with recursive CTEs / ORM joins rather
than standing up Neo4j (spec §13 "PostgreSQL recursive CTEs for MVP").
"""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_col


class Region(Base):
    __tablename__ = "region"

    region_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False, index=True)
    odop_cluster_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # F7 underserved-region boost input: 0 (well served) .. 1 (highly underserved)
    underserved_index: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at = created_col()

    clusters: Mapped[list["Cluster"]] = relationship(back_populates="region")
    crafts: Mapped[list["Craft"]] = relationship(back_populates="region")


class Cluster(Base):
    __tablename__ = "cluster"

    cluster_id: Mapped[str] = mapped_column(String, primary_key=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("region.region_id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    total_capacity_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_col()

    region: Mapped[Region] = relationship(back_populates="clusters")
    artisans: Mapped[list["Artisan"]] = relationship(back_populates="cluster")


# ── Craft ⇄ Technique / Material association tables ────────────────────────
from sqlalchemy import Column, Table  # noqa: E402

craft_technique = Table(
    "craft_technique",
    Base.metadata,
    Column("craft_id", ForeignKey("craft.craft_id"), primary_key=True),
    Column("technique_id", ForeignKey("technique.technique_id"), primary_key=True),
)

craft_material = Table(
    "craft_material",
    Base.metadata,
    Column("craft_id", ForeignKey("craft.craft_id"), primary_key=True),
    Column("material_id", ForeignKey("material.material_id"), primary_key=True),
)


class Technique(Base):
    __tablename__ = "technique"

    technique_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # visual signature keywords used by F2's cross-modal heuristic
    visual_keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_col()

    crafts: Mapped[list["Craft"]] = relationship(
        secondary=craft_technique, back_populates="techniques"
    )


class Material(Base):
    __tablename__ = "material"

    material_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    # rough per-unit cost prior (INR) — F4 fallback input
    cost_prior_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at = created_col()

    crafts: Mapped[list["Craft"]] = relationship(
        secondary=craft_material, back_populates="materials"
    )


class Craft(Base):
    __tablename__ = "craft"

    craft_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    region_id: Mapped[str] = mapped_column(ForeignKey("region.region_id"), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # F4 rarity_score input: 0 (ubiquitous) .. 1 (very rare craft/technique combo)
    rarity_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    gi_status: Mapped[str] = mapped_column(String, default="unregistered", nullable=False)
    gi_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    odop_cluster: Mapped[str | None] = mapped_column(String, nullable=True)
    heritage_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_col()

    region: Mapped[Region] = relationship(back_populates="crafts")
    techniques: Mapped[list[Technique]] = relationship(
        secondary=craft_technique, back_populates="crafts"
    )
    materials: Mapped[list[Material]] = relationship(
        secondary=craft_material, back_populates="crafts"
    )
    products: Mapped[list["Product"]] = relationship(back_populates="craft")


class CraftRelation(Base):
    """Typed edge between two crafts (``related``, ``derived_from``, ``shares_region``)
    — powers the "related crafts" section of the Digital Craft Passport."""

    __tablename__ = "craft_relation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    src_craft_id: Mapped[str] = mapped_column(ForeignKey("craft.craft_id"), nullable=False, index=True)
    dst_craft_id: Mapped[str] = mapped_column(ForeignKey("craft.craft_id"), nullable=False, index=True)
    relation: Mapped[str] = mapped_column(String, default="related", nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
