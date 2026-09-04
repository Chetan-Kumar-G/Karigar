"""F2 — claim-consistency: the cataloger reports consistency, never authenticity."""
from __future__ import annotations

from app.ai.f2_catalog.claims import (
    CLAIM_STATES, build_claims, summarize,
)
from app.ai.f2_catalog.vision import extract_dominant_colors
from app.schemas.models import CatalogClaimsBlock


# ── pure claim builder ───────────────────────────────────────────────────
def _attrs(**kw):
    base = {"material": None, "technique": None, "colors": [], "region_claimed": None,
            "effort_days": None, "dimensions_mentioned": None}
    base.update(kw)
    return base


def test_every_claim_has_a_canonical_status_and_bounded_confidence():
    claims = build_claims(
        _attrs(material="cotton", technique="hand block print",
               colors=["yellow", "red"], region_claimed="Madhubani", effort_days=4),
        grounding={}, visual={}, resolved={}, craft=None, visual_context={},
    )
    assert claims
    for c in claims:
        assert c["status"] in CLAIM_STATES
        assert 0.0 <= c["confidence"] <= 1.0
        assert c["evidence"]


def test_handmade_claim_is_always_present_and_unknown():
    claims = build_claims(_attrs(material="silk"), {}, {}, {}, None, {})
    hm = [c for c in claims if c["attribute"] == "handmade"]
    assert len(hm) == 1
    assert hm[0]["status"] == "UNKNOWN"
    assert hm[0]["checkable"] is False


def test_no_claim_ever_asserts_authenticity_or_genuineness():
    claims = build_claims(
        _attrs(material="cotton", technique="hand block print", colors=["yellow"],
               region_claimed="Kutch"),
        {}, {}, {}, None, {"detected_colors": ["yellow"]},
    )
    joined = " ".join(f"{c['claim']} {c['evidence']}" for c in claims).lower()
    # no claim positively asserts authenticity / genuineness / certification
    assert "is authentic" not in joined
    assert "is genuine" not in joined
    assert "gi-certified" not in joined
    assert "guaranteed" not in joined
    for c in claims:
        assert c["status"] != "AUTHENTIC"  # not a real status
    # the summary must carry the honest framing + disclaimer
    s = summarize(claims)
    assert "consistent" in s["headline"].lower()
    assert "not proof" in s["disclaimer"].lower()


def test_material_composition_is_unknown_without_kg_or_docs():
    claims = build_claims(_attrs(material="polyester"), {}, {}, {}, None, {})
    mat = next(c for c in claims if c["attribute"] == "material")
    assert mat["status"] == "UNKNOWN"


def test_colour_in_photo_is_visually_consistent():
    claims = build_claims(
        _attrs(colors=["yellow"]), {}, {}, {}, None,
        {"detected_colors": ["yellow", "brown"]},
    )
    col = next(c for c in claims if c["attribute"] == "color")
    assert col["status"] == "VISUALLY_CONSISTENT"


def test_chromatic_colour_absent_from_photo_is_contradicted():
    claims = build_claims(
        _attrs(colors=["green"]), {}, {}, {}, None,
        {"detected_colors": ["yellow", "red"]},
    )
    col = next(c for c in claims if c["attribute"] == "color")
    assert col["status"] == "CONTRADICTED"


def test_colour_without_photo_is_unknown_not_contradicted():
    claims = build_claims(_attrs(colors=["green"]), {}, {}, {}, None, {})
    col = next(c for c in claims if c["attribute"] == "color")
    assert col["status"] == "UNKNOWN"


def test_region_gi_origin_needs_human_review():
    claims = build_claims(_attrs(region_claimed="Madhubani"), {}, {}, {}, None, {})
    reg = next(c for c in claims if c["attribute"] == "region")
    assert reg["status"] == "NEEDS_HUMAN_REVIEW"


def test_visual_contradiction_on_technique_is_escalated():
    claims = build_claims(
        _attrs(technique="handloom weaving"), {},
        visual={"technique": {"label": "contradiction", "score": 0.2}},
        resolved={}, craft=None, visual_context={},
    )
    tech = next(c for c in claims if c["attribute"] == "technique")
    assert tech["status"] == "NEEDS_HUMAN_REVIEW"


def test_summary_overall_reflects_worst_signal():
    contradicted = [{"claim": "x", "attribute": "color", "status": "CONTRADICTED",
                     "confidence": 0.5, "evidence": "e", "checkable": True}]
    assert summarize(contradicted)["overall"] == "contradicted"
    review = [{"claim": "x", "attribute": "region", "status": "NEEDS_HUMAN_REVIEW",
               "confidence": 0.1, "evidence": "e", "checkable": True}]
    assert summarize(review)["overall"] == "needs_human_review"


def test_claims_block_passes_pydantic_contract():
    claims = build_claims(
        _attrs(material="cotton", technique="hand block print", colors=["yellow"],
               region_claimed="Madhubani", effort_days=4),
        {}, {}, {}, None, {"detected_colors": ["yellow"]},
    )
    block = CatalogClaimsBlock(claims=claims, verification_summary=summarize(claims))
    assert len(block.claims) == len(claims)


# ── colour extractor ─────────────────────────────────────────────────────
def test_dominant_colours_on_a_solid_red_image():
    from PIL import Image
    import io

    buf = io.BytesIO()
    Image.new("RGB", (80, 80), (180, 40, 40)).save(buf, format="PNG")
    assert "red" in extract_dominant_colors(buf.getvalue())


def test_dominant_colours_returns_empty_on_garbage_bytes():
    assert extract_dominant_colors(b"not an image") == []


# ── endpoint contract ────────────────────────────────────────────────────
def test_catalog_endpoint_returns_validated_claim_block(client):
    r = client.post("/api/catalog/generate", data={"language_hint": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert "claims" in body and isinstance(body["claims"], list) and body["claims"]
    assert body["verification_summary"]["headline"].startswith("AI checks whether")
    # server-side contract holds on the wire
    CatalogClaimsBlock(claims=body["claims"],
                       verification_summary=body["verification_summary"])
    for c in body["claims"]:
        assert c["status"] in CLAIM_STATES
    # the demo transcript claims "handmade" + "Madhubani" — both must be honest
    hm = next(c for c in body["claims"] if c["attribute"] == "handmade")
    assert hm["status"] == "UNKNOWN"
