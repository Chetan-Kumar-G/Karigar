"""F2 — claim-consistency assessment (spec §4.F / §4.H hardening).

The cataloger never asserts that a photo *proves* a product is "authentic",
"genuine", "handmade", a particular fibre, or GI-certified.  This module turns
the deterministic grounding-guard signals and the cross-modal heuristic into an
explicit, backend-validated list of ``claim -> status`` records that only say
whether each artisan claim is **consistent with the evidence available** — the
spoken description, the product photo, and the trusted Craft Knowledge Graph.

Statuses
--------
``SUPPORTED``            corroborated by trusted craft data (the KG), or by the
                        artisan's own words for a low-stakes non-visual attribute
``VISUALLY_CONSISTENT``  the product photo is consistent with the claim
                        (necessary, not sufficient — never proof)
``CONTRADICTED``         the photo or the KG disagrees with the claim
``UNKNOWN``              cannot be established from the evidence we have
``NEEDS_HUMAN_REVIEW``   needs documentation / moderation (origin, GI) or is a
                        contradiction a person must adjudicate
"""
from __future__ import annotations

SUPPORTED = "SUPPORTED"
VISUALLY_CONSISTENT = "VISUALLY_CONSISTENT"
CONTRADICTED = "CONTRADICTED"
UNKNOWN = "UNKNOWN"
NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW"

CLAIM_STATES: tuple[str, ...] = (
    SUPPORTED, VISUALLY_CONSISTENT, CONTRADICTED, UNKNOWN, NEEDS_HUMAN_REVIEW,
)

HEADLINE = (
    "AI checks whether the artisan's claims are consistent with available "
    "visual evidence and trusted craft data."
)
DISCLAIMER = (
    "This is a consistency check, not proof of authenticity, exact material "
    "composition, genuine handmade status, or GI certification."
)

# colours that are usually background / neutral in a product photo — present-or-
# absent is weak evidence, so we never mark these CONTRADICTED.
_NEUTRAL_COLORS = {"white", "black", "natural", "brown"}


def _claim(text: str, attribute: str, status: str, confidence: float,
           evidence: str, *, checkable: bool = True) -> dict:
    assert status in CLAIM_STATES, status
    return {
        "claim": text,
        "attribute": attribute,
        "status": status,
        "confidence": round(max(0.0, min(1.0, float(confidence))), 2),
        "evidence": evidence,
        "checkable": checkable,
    }


def build_claims(
    attrs: dict,
    grounding: dict,
    visual: dict,
    resolved: dict,
    craft,
    visual_context: dict | None,
) -> list[dict]:
    """Compose the per-claim status list. Pure function — no DB writes."""
    vc = visual_context or {}
    detected = {c.lower() for c in vc.get("detected_colors", []) if c}
    detected_chromatic = detected - _NEUTRAL_COLORS
    claims: list[dict] = []

    # ── technique ────────────────────────────────────────────────────────
    tech = attrs.get("technique")
    if tech:
        g = grounding.get("technique")
        v = visual.get("technique") or {}
        vlabel, vscore = v.get("label"), v.get("score")
        if vlabel == "contradiction":
            claims.append(_claim(
                f"Made using {tech}", "technique", NEEDS_HUMAN_REVIEW, 0.2,
                "The product photo does not visually match the stated technique — "
                "sent to a human reviewer."))
        elif vlabel == "entailment":
            claims.append(_claim(
                f"Looks consistent with {tech}", "technique", VISUALLY_CONSISTENT,
                float(vscore or 0.6),
                "Visual features in the photo are consistent with this technique. "
                "This is not proof the piece was hand-executed."))
        elif g == "confirmed_from_voice":
            claims.append(_claim(
                f"Made using {tech}", "technique", VISUALLY_CONSISTENT, 0.5,
                "Stated by the artisan and not contradicted by the photo, but the "
                "technique cannot be fully verified from an image."))
        else:
            claims.append(_claim(
                f"Made using {tech}", "technique", UNKNOWN, 0.0,
                "Technique could not be confirmed from the description or the photo."))

    # ── material (a type word such as \"cotton\", never a composition %) ──
    mat = attrs.get("material")
    if mat:
        kg_materials = {m.name.lower() for m in craft.materials} if craft else set()
        mres = resolved.get("material") or {}
        kg_hit = mat.lower() in kg_materials or (
            mres.get("id") and (mres.get("score") or 0) >= 0.8 and craft is not None
            and any(mres["id"] == m.material_id for m in craft.materials)
        )
        if kg_hit:
            claims.append(_claim(
                f"Made of {mat}", "material", SUPPORTED, 0.7,
                f'"{mat}" is a documented material for this craft in the craft '
                "knowledge graph. Exact fibre composition still needs a lab or GI check."))
        else:
            claims.append(_claim(
                f"Made of {mat}", "material", UNKNOWN, 0.2,
                "Material type and exact composition cannot be established from a "
                "photograph or the spoken description alone."))

    # ── colours ─────────────────────────────────────────────────────────
    for col in attrs.get("colors", []):
        c = col.lower()
        label = f"{col.title()} colour present"
        if not detected:
            claims.append(_claim(
                label, "color", UNKNOWN, 0.0,
                "No product photo was available for a colour check."))
        elif c in detected or any(c in d or d in c for d in detected):
            claims.append(_claim(
                label, "color", VISUALLY_CONSISTENT, 0.6,
                f'"{col}" is present among the dominant colours of the product photo.'))
        elif c in _NEUTRAL_COLORS:
            claims.append(_claim(
                label, "color", UNKNOWN, 0.1,
                f'"{col}" is a neutral tone that a rough colour read cannot reliably confirm.'))
        else:
            photo_cols = ", ".join(sorted(detected_chromatic)) or "none"
            claims.append(_claim(
                label, "color", CONTRADICTED, 0.55,
                f'"{col}" was described but is not among the photo\'s dominant '
                f"colours (photo: {photo_cols}). Prototype colour read — flagged for review."))

    # ── region / GI origin ──────────────────────────────────────────────
    reg = attrs.get("region_claimed")
    if reg:
        gi = getattr(craft, "gi_status", None) if craft else None
        if gi == "registered":
            claims.append(_claim(
                f"Belongs to the {reg} craft tradition", "region", SUPPORTED, 0.55,
                f"{reg} maps to a GI-registered craft in the knowledge graph. "
                "Whether THIS item comes from a GI-certified unit still needs documentation."))
        else:
            claims.append(_claim(
                f"From {reg} (geographical / GI origin)", "region", NEEDS_HUMAN_REVIEW, 0.1,
                "Geographical origin and GI status cannot be verified from an image; "
                "they require certification or platform documentation."))

    # ── genuine handmade — always emitted, never provable from a photo ──
    claims.append(_claim(
        "Made entirely by hand by the artisan", "handmade", UNKNOWN, 0.0,
        "Genuine handmade status cannot be proven from a photograph. It needs "
        "artisan verification, a process video, or workshop evidence.",
        checkable=False))

    # ── self-reported effort ───────────────────────────────────────────
    if attrs.get("effort_days"):
        claims.append(_claim(
            f"Takes about {attrs['effort_days']} days to make", "effort", UNKNOWN, 0.0,
            "Production time is self-reported and cannot be independently verified.",
            checkable=False))

    return claims


def summarize(claims: list[dict]) -> dict:
    counts = {s: 0 for s in CLAIM_STATES}
    for c in claims:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    if counts[CONTRADICTED]:
        overall = "contradicted"
    elif counts[NEEDS_HUMAN_REVIEW]:
        overall = "needs_human_review"
    elif counts[VISUALLY_CONSISTENT] or counts[SUPPORTED]:
        overall = "consistent_where_checkable"
    else:
        overall = "insufficient_evidence"
    return {
        "headline": HEADLINE,
        "disclaimer": DISCLAIMER,
        "counts": counts,
        "overall": overall,
        "reviewable_claims": [c["claim"] for c in claims
                              if c["status"] in (CONTRADICTED, NEEDS_HUMAN_REVIEW)],
    }
