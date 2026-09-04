"""Digital Craft Passport + Certification (spec §5.F, §11)."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_col, updated_col


class CraftPassport(Base):
    __tablename__ = "craft_passport"

    passport_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_id: Mapped[str] = mapped_column(
        ForeignKey("product.product_id"), nullable=False, unique=True, index=True
    )
    craft_id: Mapped[str | None] = mapped_column(ForeignKey("craft.craft_id"), nullable=True)
    technique_id: Mapped[str | None] = mapped_column(ForeignKey("technique.technique_id"), nullable=True)
    region_id: Mapped[str | None] = mapped_column(ForeignKey("region.region_id"), nullable=True)
    artisan_id: Mapped[str | None] = mapped_column(ForeignKey("artisan.artisan_id"), nullable=True)
    material_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    gi_status: Mapped[str] = mapped_column(String, default="unregistered", nullable=False)
    gi_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    odop_cluster: Mapped[str | None] = mapped_column(String, nullable=True)

    provenance_confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    # spec §5.I component terms, persisted so the judge screen can show the breakdown
    confidence_breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    visual_authenticity_status: Mapped[str] = mapped_column(
        String, default="neutral", nullable=False
    )  # entailment | neutral | contradiction_under_review

    story_snippet_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_snippet_hi: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_craft_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    created_at = created_col()
    updated_at = updated_col()

    product: Mapped["Product"] = relationship(back_populates="passport")
    certifications: Mapped[list["Certification"]] = relationship(
        back_populates="passport", cascade="all, delete-orphan"
    )


class Certification(Base):
    __tablename__ = "certification"

    certification_id: Mapped[str] = mapped_column(String, primary_key=True)
    passport_id: Mapped[str] = mapped_column(
        ForeignKey("craft_passport.passport_id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)  # GI | ODOP | other
    status: Mapped[str] = mapped_column(String, default="sample_record", nullable=False)
    reference_doc_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # NEVER implies a real government certificate — labelled for judge honesty
    label: Mapped[str] = mapped_column(String, default="Sample Verification Record", nullable=False)
    issued_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_col()

    passport: Mapped[CraftPassport] = relationship(back_populates="certifications")
