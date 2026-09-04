"""F2 — rough product-photo colour read for the cross-modal claim check.

**Mode: PROTOTYPE.**  Quantises the photo onto the same canonical colour
vocabulary the slot extractor uses, so a spoken colour claim can be scored
``VISUALLY_CONSISTENT`` / ``CONTRADICTED`` against real pixels instead of against
nothing.  A CLIP-class visual-entailment scorer is the documented upgrade
(spec §4.H).
"""
from __future__ import annotations

import io

from PIL import Image

# canonical colour name -> representative RGB anchor
_ANCHORS: dict[str, tuple[int, int, int]] = {
    "red": (170, 45, 45),
    "yellow": (222, 190, 60),
    "blue": (45, 75, 150),
    "green": (60, 130, 70),
    "black": (28, 28, 28),
    "white": (242, 242, 242),
    "brown": (120, 80, 50),
    "natural": (203, 182, 150),
}


def extract_dominant_colors(
    image_bytes: bytes, *, top: int = 4, min_share: float = 0.10
) -> list[str]:
    """Return up to ``top`` canonical colour names each covering >= ``min_share``
    of the (downsampled) photo.  Empty list on any decode failure."""
    try:
        im = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((64, 64))
    except Exception:
        return []
    raw = im.tobytes()  # RGBRGB... , 3 bytes per pixel
    if not raw:
        return []
    px = [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 3)]
    counts: dict[str, int] = {}
    for r, g, b in px:
        name = min(
            _ANCHORS,
            key=lambda k: (r - _ANCHORS[k][0]) ** 2
            + (g - _ANCHORS[k][1]) ** 2
            + (b - _ANCHORS[k][2]) ** 2,
        )
        counts[name] = counts.get(name, 0) + 1
    n = len(px)
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    return [name for name, c in ranked[:top] if c / n >= min_share]
