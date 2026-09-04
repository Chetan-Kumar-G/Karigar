"""Trust & Verification system — Verified Artisan / Verified Business (spec add-on).

Design constraints that keep the existing prototype safe:

* **All-new tables.** No existing table is altered, so ``Base.metadata.create_all``
  picks these up on boot and every existing F1–F7 demo flow is untouched.
* **AI assists, it does not certify.** AI produces *risk flags* and helps collect
  evidence; a defined-evidence + platform/human review decides verification.
* **No private KYC is exposed publicly.** The public "card" helpers in
  ``app.services.trust`` deliberately return only non-sensitive fields.
"""
from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, created_col, updated_col

# ── trust-status state machine ────────────────────────────────────────────
#   PENDING → VERIFIED → UNDER_REVIEW → SUSPENDED → REINSTATED
#   (any) → REJECTED
TRUST_PENDING = "PENDING"
TRUST_VERIFIED = "VERIFIED"
TRUST_UNDER_REVIEW = "UNDER_REVIEW"
TRUST_SUSPENDED = "SUSPENDED"
TRUST_REINSTATED = "REINSTATED"
TRUST_REJECTED = "REJECTED"

TRUST_STATES = (
    TRUST_PENDING, TRUST_VERIFIED, TRUST_UNDER_REVIEW,
    TRUST_SUSPENDED, TRUST_REINSTATED, TRUST_REJECTED,
)

# allowed transitions (reviewer/platform actions)
TRUST_TRANSITIONS: dict[str, set[str]] = {
    TRUST_PENDING: {TRUST_VERIFIED, TRUST_UNDER_REVIEW, TRUST_REJECTED},
    TRUST_VERIFIED: {TRUST_UNDER_REVIEW, TRUST_SUSPENDED},
    TRUST_UNDER_REVIEW: {TRUST_VERIFIED, TRUST_SUSPENDED, TRUST_REJECTED, TRUST_REINSTATED},
    TRUST_SUSPENDED: {TRUST_REINSTATED, TRUST_REJECTED, TRUST_UNDER_REVIEW},
    TRUST_REINSTATED: {TRUST_VERIFIED, TRUST_UNDER_REVIEW, TRUST_SUSPENDED},
    TRUST_REJECTED: {TRUST_PENDING, TRUST_UNDER_REVIEW},
}

# a status that still grants marketplace / B2B privileges
TRUST_ACTIVE_STATES = {TRUST_VERIFIED, TRUST_REINSTATED}

# ── GI / certification status — deliberately separate from artisan verification ──
GI_NOT_REGISTERED = "not_registered"
GI_ARTISAN_REPORTED = "artisan_reported"
GI_PENDING = "pending_verification"
GI_GOVERNMENT_VERIFIED = "government_verified"
GI_STATES = (GI_NOT_REGISTERED, GI_ARTISAN_REPORTED, GI_PENDING, GI_GOVERNMENT_VERIFIED)


class VerificationProfile(Base):
    """One trust record per artisan or business."""

    __tablename__ = "verification_profile"

    profile_id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String, nullable=False, index=True)  # artisan | business
    subject_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)

    verification_status: Mapped[str] = mapped_column(
        String, default=TRUST_PENDING, nullable=False, index=True
    )

    # explicit, itemised verification (never one vague "certified")
    identity_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    craft_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    product_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    business_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contact_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # GI / certification — its own axis, NOT implied by craft or region
    gi_status: Mapped[str] = mapped_column(String, default=GI_NOT_REGISTERED, nullable=False)
    gi_reference: Mapped[str | None] = mapped_column(String, nullable=True)

    # explainable reliability (0..100) + its component breakdown
    reliability_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reliability_breakdown: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    completed_orders: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_time_pct: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    cancellation_rate_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    quality_complaints: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    b2b_eligible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    verification_date: Mapped[str | None] = mapped_column(String, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "platform-review"
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    joined_at = created_col()
    updated_at = updated_col()

    evidence: Mapped[list["VerificationEvidence"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan",
        order_by="VerificationEvidence.created_at",
    )
    reviews: Mapped[list["VerificationReview"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan",
        order_by="VerificationReview.created_at",
    )


class VerificationEvidence(Base):
    """A single piece of submitted evidence backing one of the verification axes."""

    __tablename__ = "verification_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("verification_profile.profile_id"), nullable=False, index=True
    )
    # phone_otp | gov_kyc | business_registration | product_sample | craft_record |
    # cluster_record | declaration | gi_document
    kind: Mapped[str] = mapped_column(String, nullable=False)
    axis: Mapped[str] = mapped_column(String, default="identity", nullable=False)
    # identity | craft | product | business | contact | gi
    label: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="submitted", nullable=False)
    # submitted | accepted | rejected | more_needed
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_assisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = created_col()

    profile: Mapped[VerificationProfile] = relationship(back_populates="evidence")


class VerificationReview(Base):
    """Immutable log of every reviewer / platform decision on a profile."""

    __tablename__ = "verification_review"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(
        ForeignKey("verification_profile.profile_id"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String, nullable=False)
    # approve | request_more_evidence | reject | place_under_review | suspend | reinstate
    reviewer: Mapped[str] = mapped_column(String, default="platform-review", nullable=False)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str | None] = mapped_column(String, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = created_col()

    profile: Mapped[VerificationProfile] = relationship(back_populates="reviews")


class Complaint(Base):
    """A buyer / business report of an issue with an artisan or order."""

    __tablename__ = "complaint"

    complaint_id: Mapped[str] = mapped_column(String, primary_key=True)
    reported_by: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String, default="artisan", nullable=False)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    order_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    # product_not_as_described | fake_counterfeit | wrong_material | wrong_quantity |
    # poor_quality | not_delivered | repeated_cancellation | misleading_gi_claim | other
    category: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, default="medium", nullable=False)  # low|medium|high
    status: Mapped[str] = mapped_column(String, default="open", nullable=False, index=True)
    # open | investigating | resolved | dismissed
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_flag: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI-produced, advisory only
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = created_col()
    updated_at = updated_col()


class TrustEvent(Base):
    """Audit trail: status changes, AI risk flags, complaints, evidence, reliability."""

    __tablename__ = "trust_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String, default="artisan", nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # status_change | risk_flag | complaint | evidence | reliability | note
    summary: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    actor: Mapped[str] = mapped_column(String, default="system", nullable=False)
    created_at = created_col()


class B2BOrderCommitment(Base):
    """Simulated order-commitment / milestone-payment / delivery state for a B2B order.

    Prototype only — clearly labelled *Simulated*. No real banking / escrow.
    """

    __tablename__ = "b2b_order_commitment"

    order_id: Mapped[str] = mapped_column(
        ForeignKey("b2b_order.order_id"), primary_key=True
    )
    # DRAFT | BUYER_CONFIRMED | ADVANCE_PAID | ARTISANS_ALLOCATED | PRODUCTION_STARTED |
    # PRODUCTION_COMPLETED | READY_FOR_SHIPMENT | SHIPPED | DELIVERED | COMPLETED |
    # CANCELLED_BY_BUYER | CANCELLED_BY_ARTISAN | DISPUTED
    commitment_status: Mapped[str] = mapped_column(String, default="DRAFT", nullable=False)
    # not_started | preparing | consolidating | bulk_shipped | out_for_delivery | delivered
    delivery_status: Mapped[str] = mapped_column(String, default="not_started", nullable=False)
    payment_milestones: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    cancellation_stage: Mapped[str | None] = mapped_column(String, nullable=True)
    artisan_committed_cost_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    advance_retained_inr: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    tracking_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at = created_col()
    updated_at = updated_col()
