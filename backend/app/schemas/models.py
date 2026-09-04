"""Pydantic request/response schemas (spec §21 — validation + typed contracts)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ── auth ──────────────────────────────────────────────────────────────
class OtpRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=15)
    role: str = "artisan"  # artisan | buyer


class OtpVerify(BaseModel):
    phone: str
    otp: str
    role: str = "artisan"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    profile: dict


# ── F2 catalog ────────────────────────────────────────────────────────
class CatalogRequest(BaseModel):
    typed_transcript: str | None = None
    language_hint: str | None = "hi"
    craft_id: str | None = None
    product_id: str | None = None
    visual_context: dict = Field(default_factory=dict)


class ClaimAssessment(BaseModel):
    """One artisan claim + how it holds up against the available evidence.

    ``status`` is deliberately a *consistency* verdict, never an authenticity
    guarantee (spec §4.F hardening)."""

    claim: str
    attribute: str
    status: Literal[
        "SUPPORTED", "VISUALLY_CONSISTENT", "CONTRADICTED",
        "UNKNOWN", "NEEDS_HUMAN_REVIEW",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str
    checkable: bool = True


class CatalogClaimsBlock(BaseModel):
    """Backend-validated shape of the F2 claim block before it reaches Flutter."""

    claims: list[ClaimAssessment]
    verification_summary: dict


# ── F4 pricing ────────────────────────────────────────────────────────
class PriceRequest(BaseModel):
    product_id: str | None = None
    material_cost_inr: float = Field(ge=0)
    labour_hours: float = Field(ge=0)
    labour_rate_inr_per_hour: float = Field(ge=0)
    packaging_cost_inr: float = Field(ge=0, default=0)
    logistics_cost_inr: float = Field(ge=0, default=0)
    category: str | None = None
    category_median_price_inr: float | None = None
    seasonality_index: float = 1.0
    min_margin: float | None = None


# ── F6 buyer match / allocate ────────────────────────────────────────
class ArtisanInput(BaseModel):
    artisan_id: str
    name: str | None = None
    capacity_units: int = Field(gt=0)
    unit_cost_inr: float = Field(gt=0)
    quality_score: float = 0.8
    reliability_score: float = 0.8
    logistics_cost_inr_per_unit: float = 4.0
    craft_match: bool = True


class BuyerMatchRequest(BaseModel):
    requirement_id: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    unit_price_min: float | None = None
    unit_price_max: float | None = None
    required_craft_id: str | None = None
    required_material: str | None = None
    fulfillment_min: float = 1.0
    lambda_weight: float | None = None
    artisans: list[ArtisanInput] | None = None  # omitted → pulled from the KG


class AllocateRequest(BaseModel):
    order_id: str
    accepted_allocation_ids: list[str] | None = None
    declined_allocation_ids: list[str] | None = None


class RequirementCreate(BaseModel):
    buyer_id: str | None = None
    title: str
    craft_id: str | None = None
    required_material: str | None = None
    quantity: int = Field(gt=0)
    price_min: float = Field(gt=0)
    price_max: float = Field(gt=0)
    deadline: date | None = None
    fulfillment_min: float = 1.0
    notes: str | None = None


# ── publish ──────────────────────────────────────────────────────────
class PublishRequest(BaseModel):
    product_id: str
    price_inr: float | None = None
