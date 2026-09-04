"""F1 — enhancement safety gate (Phase 4).

These assert *invariants* rather than exact scores: the gate must never ship an
enhanced photo that is worse, that regresses an already-good dimension, or that
distorts the product's real colour.
"""
from __future__ import annotations

import io

import numpy as np
from PIL import Image

from app.ai.f1_studio.analyzer import (
    ACCEPT_AT,
    COLOUR_SHIFT_MAX,
    MIN_READINESS_GAIN,
    analyze,
)


def _jpg(arr: np.ndarray, quality: int = 92) -> bytes:
    b = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), "RGB").save(b, "JPEG", quality=quality)
    return b.getvalue()


def _product_on_bg(w=1200, h=900, bg=245, fg=(120, 90, 70), noise=18,
                   prod_frac=0.55) -> np.ndarray:
    """A textured rectangular 'product' centred on a plain light background."""
    rng = np.random.default_rng(7)
    img = np.full((h, w, 3), bg, np.float32)
    pw, ph = int(w * prod_frac), int(h * prod_frac)
    x0, y0 = (w - pw) // 2, (h - ph) // 2
    patch = np.array(fg, np.float32) + rng.normal(0, noise, (ph, pw, 3))
    # high-frequency detail so it reads as "in focus"
    patch[::3, :, :] += 22
    patch[:, ::3, :] -= 18
    img[y0:y0 + ph, x0:x0 + pw] = patch
    img += rng.normal(0, 2.5, img.shape)
    return np.clip(img, 0, 255)


def _analyze(arr):
    return analyze(_jpg(arr)).data


# ── gate invariants (the point of Phase 4) ──────────────────────────────
def test_output_shape_has_colour_fidelity_and_gate():
    d = _analyze(_product_on_bg())
    assert set(d["component_scores"]) == {
        "sharpness", "exposure", "framing", "background_cleanliness",
        "resolution", "colour_fidelity",
    }
    g = d["enhancement_gate"]
    assert g["verdict"] in ("USE_ENHANCED", "ACCEPT_ORIGINAL", "REQUEST_RETAKE")
    assert 0 <= d["readiness_score"] <= 100
    assert d["decision"] in ("accept", "auto_enhance", "retake")


def test_applied_enhancement_never_worse_and_never_colour_distorting():
    for shade in (60, 90, 120, 150, 180):
        d = _analyze(_product_on_bg(fg=(shade, shade - 10, shade - 18)))
        g = d["enhancement_gate"]
        if g["applied"]:
            assert g["readiness_delta"] >= MIN_READINESS_GAIN, g
            assert g["regressed_dimensions"] == [], g
            assert g["colour_shift_deltaE"] <= COLOUR_SHIFT_MAX, g
            assert d["before_after"]["after"]["readiness_score"] >= \
                d["before_after"]["before"]["readiness_score"]


def test_already_good_photo_is_accepted_without_enhancement():
    # bright, sharp, well-framed, neutral background
    d = _analyze(_product_on_bg(bg=250, fg=(150, 140, 130), noise=22))
    if d["readiness_score"] >= ACCEPT_AT:
        assert d["decision"] == "accept"
        assert d["enhancement_gate"]["verdict"] == "ACCEPT_ORIGINAL"
        assert d["enhancement_gate"]["applied"] is False


def test_dark_photo_flags_exposure_and_either_lifts_or_keeps_original():
    d = _analyze(_product_on_bg(bg=70, fg=(28, 22, 18), noise=6))
    assert d["component_scores"]["exposure"] < 70
    g = d["enhancement_gate"]
    if g["applied"]:
        assert "shadow_lift" in g["steps"] or "clahe" in g["steps"]
        assert g["colour_shift_deltaE"] <= COLOUR_SHIFT_MAX
    else:
        assert g["reasons"]  # must explain why it declined


def test_blurry_photo_scores_low_sharpness():
    import cv2

    base = _product_on_bg()
    blur = cv2.GaussianBlur(base.astype(np.uint8), (0, 0), 6)
    d = _analyze(blur)
    assert d["component_scores"]["sharpness"] < 55
    # A blur cannot be safely "sharpened" by this pipeline — it must not pretend.
    assert "unsharp" not in d["enhancement_gate"]["steps"]


def test_overexposed_photo_is_not_accepted_as_perfect():
    d = _analyze(_product_on_bg(bg=255, fg=(252, 250, 248), noise=2))
    assert d["readiness_score"] < ACCEPT_AT
    assert d["component_scores"]["exposure"] < 75 or \
        d["component_scores"]["colour_fidelity"] < 75


def test_bad_segmentation_does_not_do_background_edits_and_is_cautious():
    rng = np.random.default_rng(1)
    noise = rng.integers(0, 255, (900, 1200, 3))
    d = _analyze(noise)
    g = d["enhancement_gate"]
    assert g["segmentation_confidence"] <= 0.6
    assert "studio_background" not in g["steps"]
    # never a confident "accept" when we can't even find the product
    assert d["decision"] in ("retake", "auto_enhance") or d["readiness_score"] < ACCEPT_AT


def test_strong_colour_cast_is_penalised_and_gate_protects_colour():
    base = _product_on_bg(bg=235, fg=(110, 95, 80))
    tinted = base.copy()
    tinted[..., 2] = np.clip(tinted[..., 2] * 1.7, 0, 255)  # heavy blue cast (RGB->B)
    d = _analyze(tinted)
    assert d["component_scores"]["colour_fidelity"] < 78
    g = d["enhancement_gate"]
    # whatever it decides, an *applied* enhancement is colour-safe by construction
    if g["applied"]:
        assert g["colour_shift_deltaE"] <= COLOUR_SHIFT_MAX
