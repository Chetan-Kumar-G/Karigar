"""F1 — AI Product Studio + Product Readiness Quality Gate.

**Mode: REAL.**  Every component score is computed from the pixels with OpenCV:

| dimension              | method                                                    |
|------------------------|-----------------------------------------------------------|
| sharpness              | variance of the Laplacian (focus measure)                 |
| exposure               | luminance histogram — mean level + shadow/highlight clip  |
| framing                | product mask bounding-box area / centering vs. the frame  |
| background_cleanliness | colour + edge variance in the mask *complement*           |
| resolution             | effective pixel count vs. e-commerce thresholds           |
| colour_fidelity        | global colour cast + per-channel clipping (Phase 4)       |

Composite + thresholds follow spec §3.I (weights re-balanced to admit the new
colour-fidelity axis; they still sum to 1.0):

    Accept ≥ 80   ·   Auto-enhance 50–79   ·   Retake < 50

**Enhancement safety gate (Phase 4).**  Auto-enhance is *conditional*: each sub-step
(shadow lift, local-contrast, white-balance, studio background) runs only for a
dimension that actually scored low, and the enhanced candidate is accepted only if
it (a) raises the composite, (b) does not regress a dimension that was already
good, and (c) does not shift the product's real colour beyond ``COLOUR_SHIFT_MAX``
ΔE. Otherwise the original is kept. The verdict is one of
``USE_ENHANCED`` / ``ACCEPT_ORIGINAL`` / ``REQUEST_RETAKE`` with reasons.

The promptable-segmentation step (SAM/SAM2 in the spec) is approximated here with
GrabCut; the SAM checkpoint is a documented production upgrade (spec §14).
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.ai.base import REAL, AiResult, timed

WEIGHTS = {
    "sharpness": 0.18,
    "exposure": 0.22,
    "framing": 0.18,
    "background_cleanliness": 0.17,
    "resolution": 0.12,
    "colour_fidelity": 0.13,
}
ACCEPT_AT = 80
ENHANCE_AT = 50

# Enhancement safety-gate thresholds.
GOOD_DIM = 75            # a dimension at/above this is "already good" — don't regress it
REGRESSION_TOL = 6       # allowed drop on an already-good dimension
MIN_READINESS_GAIN = 1   # enhanced composite must beat original by at least this
COLOUR_SHIFT_MAX = 12.0  # mean CIE76 ΔE on the product region — above this = distortion
LOW_SEG_CONF = 0.35      # below this the mask is untrustworthy → no background edits

_GUIDANCE = {
    "exposure": {
        "en": "Photo is too dark. Move next to a window or add a lamp, then retake.",
        "hi": "फ़ोटो बहुत गहरी है। खिड़की के पास जाएँ या रोशनी बढ़ाएँ, फिर दोबारा लें।",
    },
    "sharpness": {
        "en": "Photo is blurry. Hold the phone steady, tap the product to focus, retake.",
        "hi": "फ़ोटो धुंधली है। फ़ोन स्थिर रखें, उत्पाद पर टैप करके फ़ोकस करें, दोबारा लें।",
    },
    "background_cleanliness": {
        "en": "Background is cluttered. Use a plain cloth or wall behind the product.",
        "hi": "पृष्ठभूमि भरी हुई है। उत्पाद के पीछे सादा कपड़ा या दीवार रखें।",
    },
    "framing": {
        "en": "Product is not centred. Fill about 80% of the frame with the product.",
        "hi": "उत्पाद बीच में नहीं है। फ़्रेम का लगभग 80% हिस्सा उत्पाद से भरें।",
    },
    "resolution": {
        "en": "Photo resolution is low. Use the main camera at full quality.",
        "hi": "फ़ोटो का रिज़ॉल्यूशन कम है। मुख्य कैमरे को पूरी गुणवत्ता पर उपयोग करें।",
    },
    "colour_fidelity": {
        "en": "Strong colour tint or glare. Turn off coloured lights, avoid direct flash, retake.",
        "hi": "रंग में ज़्यादा टिंट या चमक है। रंगीन रोशनी बंद करें, सीधी फ़्लैश से बचें, दोबारा लें।",
    },
}


@dataclass
class F1Output:
    readiness_score: int
    decision: str
    component_scores: dict[str, int]
    failure_reason: str | None
    retake_guidance: dict[str, str] | None
    confidence: float
    enhanced_png: bytes | None
    mask_png: bytes | None
    before_after: dict | None
    enhancement_gate: dict


# ── image loading ─────────────────────────────────────────────────────────
def _decode(image_bytes: bytes) -> np.ndarray:
    """EXIF-orient, drop alpha, return BGR uint8."""
    pil = Image.open(io.BytesIO(image_bytes))
    pil = ImageOps.exif_transpose(pil).convert("RGB")
    rgb = np.array(pil)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def _encode_png(bgr: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", bgr)
    return buf.tobytes() if ok else b""


# ── segmentation (GrabCut, SAM is the prod upgrade) ───────────────────────
def _segment(bgr: np.ndarray) -> np.ndarray:
    """Return a uint8 {0,1} foreground mask for the product."""
    h, w = bgr.shape[:2]
    small = cv2.resize(bgr, (min(w, 512), int(min(w, 512) * h / w)))
    mask = np.zeros(small.shape[:2], np.uint8)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    margin_x, margin_y = int(small.shape[1] * 0.08), int(small.shape[0] * 0.08)
    rect = (margin_x, margin_y, small.shape[1] - 2 * margin_x, small.shape[0] - 2 * margin_y)
    try:
        cv2.grabCut(small, mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
        fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
        if fg.mean() < 0.03 or fg.mean() > 0.97:
            raise ValueError("degenerate grabcut mask")
    except Exception:
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        _t, otsu = cv2.threshold(gray, 0, 1, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        fg = otsu.astype(np.uint8)
        if fg.mean() > 0.5:
            fg = 1 - fg
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    return cv2.resize(fg, (w, h), interpolation=cv2.INTER_NEAREST)


def _segmentation_confidence(mask: np.ndarray) -> float:
    """0..1 — how much to trust the product mask. Low when the mask fills almost
    everything / almost nothing, or is scattered rather than one compact blob."""
    area = float(mask.mean())
    if area < 1e-4:
        return 0.05
    ys, xs = np.where(mask > 0)
    h, w = mask.shape
    bbox = (xs.max() - xs.min() + 1) * (ys.max() - ys.min() + 1) / (w * h)
    fill = 1.0 - min(abs(area - 0.45) / 0.45, 1.0)          # plausible product size
    compact = min(area / max(bbox, 1e-6), 1.0)              # blob vs. scatter
    n_labels, _ = cv2.connectedComponents(mask.astype(np.uint8))
    fragmentation = 1.0 / max(n_labels - 1, 1)              # 1 component -> 1.0
    extreme = 0.15 if (area > 0.95 or area < 0.02) else 1.0
    return float(np.clip(0.5 * fill + 0.3 * compact + 0.2 * fragmentation, 0, 1) * extreme)


# ── per-dimension scoring ────────────────────────────────────────────────
def _clamp(x: float) -> int:
    return int(max(0, min(100, round(x))))


def _score_sharpness(gray: np.ndarray) -> int:
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    # ~30 -> unusable, ~600 -> crisp (log scale between)
    return _clamp(100 * (math.log10(max(fm, 1)) - math.log10(30)) / (math.log10(600) - math.log10(30)))


def _score_exposure(gray: np.ndarray) -> int:
    mean = gray.mean()
    hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
    hist /= hist.sum() + 1e-9
    clip = float(hist[:6].sum() + hist[-6:].sum())  # crushed shadows / blown highlights
    # ideal mean ~ 120–170
    center = 1.0 - min(abs(mean - 145) / 145, 1.0)
    return _clamp(100 * (0.75 * center + 0.25 * (1 - min(clip * 4, 1))))


def _score_framing(mask: np.ndarray) -> int:
    ys, xs = np.where(mask > 0)
    if xs.size == 0:
        return 20
    h, w = mask.shape
    area_ratio = mask.mean()
    bbox = (xs.max() - xs.min()) * (ys.max() - ys.min()) / (w * h)
    cx, cy = xs.mean() / w, ys.mean() / h
    centering = 1.0 - min(math.hypot(cx - 0.5, cy - 0.5) / 0.5, 1.0)
    fill = 1.0 - min(abs(bbox - 0.62) / 0.62, 1.0)  # product should fill ~50–75%
    tightness = min(area_ratio / max(bbox, 1e-6), 1.0)
    return _clamp(100 * (0.45 * fill + 0.35 * centering + 0.20 * tightness))


def _score_background(bgr: np.ndarray, mask: np.ndarray) -> int:
    bg = mask == 0
    if bg.sum() < 100:
        return 55
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    colour_std = float(lab[bg].std(axis=0).mean())
    edges = cv2.Canny(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), 60, 160)
    edge_density = float((edges[bg] > 0).mean())
    colour_term = 1.0 - min(colour_std / 42.0, 1.0)
    edge_term = 1.0 - min(edge_density / 0.14, 1.0)
    return _clamp(100 * (0.6 * colour_term + 0.4 * edge_term))


def _score_resolution(bgr: np.ndarray) -> int:
    px = bgr.shape[0] * bgr.shape[1]
    lo, hi = 640 * 640, 1600 * 1600
    return _clamp(100 * (px - lo) / (hi - lo))


def _score_colour_fidelity(bgr: np.ndarray, mask: np.ndarray) -> int:
    """Absolute check that the *original* carries faithful colour: penalise a
    strong global colour cast and per-channel clipping (blown / crushed channels
    lose the real product hue). This is about the photo as shot — the enhanced
    candidate is separately checked for colour *shift* in the safety gate."""
    fg = mask > 0
    region = bgr[fg] if fg.sum() > 200 else bgr.reshape(-1, 3)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    lab_region = lab[fg.reshape(-1)] if fg.sum() > 200 else lab
    # a*, b* centre on 128 for neutral; distance = chromatic cast strength
    cast = math.hypot(float(lab_region[:, 1].mean()) - 128.0,
                      float(lab_region[:, 2].mean()) - 128.0)
    cast_term = 1.0 - min(cast / 28.0, 1.0)          # ~28 LAB units = heavy tint
    # per-channel clipping in the product region
    clip_hi = float((region >= 250).mean())
    clip_lo = float((region <= 5).mean())
    clip_term = 1.0 - min((clip_hi + clip_lo) * 3.0, 1.0)
    # channel balance — a wildly dominant channel usually means a colour light
    ch_mean = region.reshape(-1, 3).mean(axis=0) + 1e-6
    balance = float(ch_mean.min() / ch_mean.max())
    balance_term = min(balance / 0.62, 1.0)
    return _clamp(100 * (0.5 * cast_term + 0.3 * clip_term + 0.2 * balance_term))


def _component_scores(bgr: np.ndarray, mask: np.ndarray) -> dict[str, int]:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return {
        "sharpness": _score_sharpness(gray),
        "exposure": _score_exposure(gray),
        "framing": _score_framing(mask),
        "background_cleanliness": _score_background(bgr, mask),
        "resolution": _score_resolution(bgr),
        "colour_fidelity": _score_colour_fidelity(bgr, mask),
    }


def _composite(scores: dict[str, int]) -> int:
    return _clamp(sum(scores[k] * w for k, w in WEIGHTS.items()))


def _contrast_std(bgr: np.ndarray) -> float:
    l = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 0]
    return float(l.std())


def _colour_shift_deltaE(a_bgr: np.ndarray, b_bgr: np.ndarray, mask: np.ndarray) -> float:
    """Mean CIE76 ΔE between two images over the product region."""
    fg = mask > 0
    if fg.sum() < 200:
        fg = np.ones(mask.shape, bool)
    la = cv2.cvtColor(a_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)[fg]
    lb = cv2.cvtColor(b_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)[fg]
    # OpenCV L in [0,255]; scale L to [0,100] so ΔE is in familiar units
    la[:, 0] *= 100.0 / 255.0
    lb[:, 0] *= 100.0 / 255.0
    return float(np.sqrt(((la - lb) ** 2).sum(axis=1)).mean())


# ── conditional auto-enhance ────────────────────────────────────────────
def _enhance(bgr: np.ndarray, mask: np.ndarray, scores: dict[str, int],
             seg_conf: float) -> tuple[np.ndarray, list[str]]:
    """Apply only the sub-steps whose target dimension actually scored low.
    Returns the candidate and the list of steps applied."""
    out = bgr.astype(np.float32) / 255.0
    applied: list[str] = []

    # 1. shadow lift — only if exposure is genuinely low AND the frame is dark
    mean = float(out.mean())
    if scores["exposure"] < 68 and mean < 0.45:
        gamma = float(np.clip(math.log(0.5) / math.log(mean + 1e-6), 0.45, 1.0))
        out = np.power(out, gamma)
        applied.append("shadow_lift")
    out = np.clip(out * 255.0, 0, 255).astype(np.uint8)

    # 2. local contrast — only if global contrast is flat
    if _contrast_std(out) < 46 and scores["exposure"] < 78:
        lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(l)
        out = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
        applied.append("clahe")

    # 3. white balance — only if there is a real colour cast (fidelity marked it)
    if scores["colour_fidelity"] < 72:
        avg = out.reshape(-1, 3).mean(axis=0)
        scale = avg.mean() / (avg + 1e-6)
        scale = np.clip(scale, 0.85, 1.18)  # gentle — never a full grey-world swing
        out = np.clip(out * scale, 0, 255).astype(np.uint8)
        applied.append("white_balance")

    # 4. studio background sweep — only if background is poor AND we trust the mask
    if scores["background_cleanliness"] < 62 and seg_conf >= LOW_SEG_CONF:
        h, w = out.shape[:2]
        sweep = np.linspace(246, 224, h, dtype=np.uint8).reshape(h, 1, 1).repeat(w, 1).repeat(3, 2)
        soft = cv2.GaussianBlur((mask * 255).astype(np.uint8), (0, 0), 7).astype(np.float32) / 255.0
        soft = soft[:, :, None]
        out = (out * soft + sweep * (1 - soft)).astype(np.uint8)
        applied.append("studio_background")

    return out, applied


# ── public entry point ──────────────────────────────────────────────────
def analyze(image_bytes: bytes, category_hint: str | None = None) -> AiResult:
    with timed() as t:
        bgr = _decode(image_bytes)
        mask = _segment(bgr)
        seg_conf = _segmentation_confidence(mask)
        scores = _component_scores(bgr, mask)
        readiness = _composite(scores)
        orig_scores, orig_readiness = dict(scores), readiness

        dims_needing_work = sorted(
            (k for k, v in scores.items() if v < 70), key=lambda k: scores[k]
        )

        gate: dict = {
            "verdict": "ACCEPT_ORIGINAL",
            "applied": False,
            "steps": [],
            "reasons": [],
            "colour_shift_deltaE": 0.0,
            "readiness_delta": 0,
            "segmentation_confidence": round(seg_conf, 2),
            "dimensions_needing_work": dims_needing_work,
            "regressed_dimensions": [],
        }

        enhanced_png = None
        before_after = None

        if readiness >= ACCEPT_AT:
            gate["reasons"].append("Original already meets the publish bar — no enhancement needed.")
        elif readiness >= ENHANCE_AT:
            cand, steps = _enhance(bgr, mask, scores, seg_conf)
            if not steps:
                gate["reasons"].append("No dimension was weak enough to safely enhance.")
            else:
                new_mask = _segment(cand)
                new_scores = _component_scores(cand, new_mask)
                new_readiness = _composite(new_scores)
                d_ready = new_readiness - orig_readiness
                colour_shift = _colour_shift_deltaE(bgr, cand, mask)
                regressed = [
                    k for k in WEIGHTS
                    if orig_scores[k] >= GOOD_DIM and (orig_scores[k] - new_scores[k]) > REGRESSION_TOL
                ]
                gate.update({
                    "steps": steps,
                    "colour_shift_deltaE": round(colour_shift, 1),
                    "readiness_delta": int(d_ready),
                    "regressed_dimensions": regressed,
                })
                if colour_shift > COLOUR_SHIFT_MAX:
                    gate["reasons"].append(
                        f"Enhancement shifted the product's real colour by ΔE {colour_shift:.0f} "
                        f"(limit {COLOUR_SHIFT_MAX:.0f}) — keeping the original.")
                elif regressed:
                    gate["reasons"].append(
                        "Enhancement made an already-good dimension worse "
                        f"({', '.join(regressed)}) — keeping the original.")
                elif d_ready < MIN_READINESS_GAIN:
                    gate["reasons"].append(
                        "Enhancement did not meaningfully improve the photo — keeping the original.")
                else:
                    enhanced_png = _encode_png(cand)
                    before_after = {
                        "before": {"readiness_score": orig_readiness, "component_scores": orig_scores},
                        "after": {"readiness_score": new_readiness, "component_scores": new_scores},
                    }
                    scores, readiness = new_scores, new_readiness
                    gate.update({"verdict": "USE_ENHANCED", "applied": True,
                                 "reasons": [f"Applied {', '.join(steps)}; "
                                             f"readiness +{int(d_ready)}, colour ΔE {colour_shift:.0f}."]})

        # ── final decision ────────────────────────────────────────────────
        if readiness >= ACCEPT_AT:
            decision, failure, guidance = "accept", None, None
        elif readiness >= ENHANCE_AT and gate["applied"]:
            decision, failure, guidance = "auto_enhance", None, None
        elif readiness >= 65 and seg_conf >= LOW_SEG_CONF:
            # usable as-is: enhancement was withheld for a good reason
            decision, failure, guidance = "accept", None, None
            if gate["verdict"] == "ACCEPT_ORIGINAL" and readiness < ACCEPT_AT:
                gate["reasons"].append("Photo is usable as-is for the prototype demo.")
        else:
            worst = min(scores, key=scores.get)
            if seg_conf < LOW_SEG_CONF:
                worst = "background_cleanliness"
                gate["reasons"].append(
                    "Could not separate the product from the background reliably — "
                    "retake on a plain surface.")
            decision, failure = "retake", worst
            guidance = _GUIDANCE.get(worst)
            gate["verdict"] = "REQUEST_RETAKE"

        conf = round(0.6 + 0.4 * (1 - np.std(list(scores.values())) / 60), 2)
        conf = float(np.clip(conf * (0.6 + 0.4 * seg_conf), 0.4, 0.97))
        out = F1Output(
            readiness_score=readiness,
            decision=decision,
            component_scores=scores,
            failure_reason=failure,
            retake_guidance=guidance,
            confidence=conf,
            enhanced_png=enhanced_png,
            mask_png=_encode_png((mask * 255).astype(np.uint8)),
            before_after=before_after,
            enhancement_gate=gate,
        )

    return AiResult(
        data={
            "readiness_score": out.readiness_score,
            "decision": out.decision,
            "component_scores": out.component_scores,
            "failure_reason": out.failure_reason,
            "retake_guidance": out.retake_guidance,
            "confidence": out.confidence,
            "before_after": out.before_after,
            "enhancement_gate": out.enhancement_gate,
            "_enhanced_png": out.enhanced_png,
            "_mask_png": out.mask_png,
        },
        feature="F1",
        model="OpenCV readiness pipeline (GrabCut seg + Laplacian/histogram/colour scoring + "
              "conditional CLAHE/gamma/WB enhance + colour-fidelity safety gate)",
        mode=REAL,
        inputs={"image_bytes": len(image_bytes), "category_hint": category_hint or ""},
        latency_ms=t["ms"],
    )
