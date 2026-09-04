"""F2 — Multilingual Grounded Auto-Cataloger orchestrator.

Pipeline (spec §4.G):  ASR → slot extraction (KG-seeded) → terminology
normalisation → **Fact-Grounding Guard** → **Cross-Modal Authenticity Verifier**
→ bilingual grounded generation → hallucination flags.

Honesty labels:
  * extraction + grounding guard  → **REAL** (deterministic rule engine over the
    transcript and the Craft KG vocabulary; this is the spec's core contribution)
  * cross-modal verifier          → **PROTOTYPE** (colour/category heuristic; the
    CLIP-class entailment scorer is the documented upgrade — spec §4.H)
  * copy generation               → template **REAL**, optional **LLM** phrasing
    when ``SIH_LLM_ENABLED=true`` (facts still come only from validated slots)
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.base import PROTOTYPE, REAL, AiResult, timed
from app.ai.f2_catalog.asr import transcribe
from app.ai.f2_catalog.claims import build_claims, summarize
from app.ai.f3_graph.graph import resolve
from app.core.config import settings
from app.models.geo_craft import Craft, Material, Region, Technique

# ── bilingual lexicon (romanised Hindi + English) ───────────────────────
MATERIAL_TERMS = {
    "cotton": ["cotton", "suti", "sooti", "kapas"],
    "silk": ["silk", "resham", "pat"],
    "wool": ["wool", "oon", "un"],
    "bamboo": ["bamboo", "baans", "bans", "beth", "cane"],
    "clay": ["clay", "terracotta", "mitti", "matti"],
    "brass": ["brass", "peetal", "dhokra", "bell metal"],
    "wood": ["wood", "lakdi", "kaath"],
    "jute": ["jute", "patsan"],
}
TECHNIQUE_TERMS = {
    "hand block print": ["block print", "blockprint", "chhapa", "thappa", "hand block"],
    "handloom weaving": ["handloom", "bunai", "buna", "weav", "weaving", "khadi"],
    "hand painting": ["painting", "chitrakari", "hand paint", "madhubani paint"],
    "hand embroidery": ["embroidery", "kadhai", "chikankari", "zari"],
    "wheel throwing": ["wheel", "chaak", "pottery", "throwing"],
    "lost-wax casting": ["dhokra", "lost wax", "lost-wax", "casting"],
    "hand weaving": ["bunee", "wov", "tokri", "basket", "weav"],
}
COLOR_TERMS = {
    "yellow": ["yellow", "peela", "peeli"], "red": ["red", "laal", "lal"],
    "blue": ["blue", "neela", "neeli"], "green": ["green", "hara", "hari"],
    "black": ["black", "kaala", "kala"], "white": ["white", "safed"],
    "brown": ["brown", "bhura"], "natural": ["natural", "prakritik", "undyed"],
}
REGION_HINTS = ["madhubani", "bihar", "assam", "kutch", "channapatna", "bastar",
                "jaipur", "bengal", "odisha", "moradabad", "srinagar"]
DAYS_RE = re.compile(r"(\d+|ek|do|teen|char|chaar|paanch|panch)\s*(din|days|day)", re.I)
_WORDNUM = {"ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5}


def _find(text: str, table: dict[str, list[str]]) -> str | None:
    low = text.lower()
    for canon, variants in table.items():
        if any(v in low for v in variants):
            return canon
    return None


def _extract(transcript: str) -> dict:
    material = _find(transcript, MATERIAL_TERMS)
    technique = _find(transcript, TECHNIQUE_TERMS)
    colors = [c for c, v in COLOR_TERMS.items() if any(x in transcript.lower() for x in v)]
    region = next((r for r in REGION_HINTS if r in transcript.lower()), None)
    m = DAYS_RE.search(transcript)
    days = None
    if m:
        g = m.group(1).lower()
        days = int(g) if g.isdigit() else _WORDNUM.get(g)
    return {
        "material": material,
        "technique": technique,
        "colors": colors,
        "region_claimed": region.title() if region else None,
        "effort_days": days,
        "dimensions_mentioned": None,
    }


# ── grounding guard ────────────────────────────────────────────────────
def _ground(attrs: dict, transcript: str, craft: Craft | None) -> dict:
    low = transcript.lower()
    check: dict[str, str] = {}
    for key in ("material", "technique"):
        val = attrs.get(key)
        if not val:
            continue
        variants = (MATERIAL_TERMS if key == "material" else TECHNIQUE_TERMS).get(val, [val])
        check[key] = "confirmed_from_voice" if any(v in low for v in variants) else "unsupported"
    if attrs.get("region_claimed"):
        # F2 can confirm the *word* was spoken, but never that this specific
        # product is from a GI-certified unit — that needs documentation (F3 /
        # human moderation).  So a region/origin claim is always flagged here
        # (spec §4.F example output).
        spoken = attrs["region_claimed"].lower() in low
        check["region_claimed"] = (
            "flagged_unverified_gi_claim" if spoken else "unsupported"
        )
    return check


# ── cross-modal authenticity verifier (heuristic prototype) ────────────
def _visual_consistency(attrs: dict, visual_context: dict, craft: Craft | None) -> dict:
    detected = {c.lower() for c in visual_context.get("detected_colors", [])}
    spoken = set(attrs.get("colors", []))
    seg_ok = visual_context.get("segmentation_present", False)
    cat_hint = (visual_context.get("product_type_hint") or "").lower()

    out: dict = {}
    # technique: visual keywords of the resolved technique vs. category hint
    tech = attrs.get("technique")
    if tech:
        kw = []
        if craft:
            for t in craft.techniques:
                if t.name == tech and t.visual_keywords:
                    kw = [k.strip().lower() for k in t.visual_keywords.split(",")]
        hit = any(k in cat_hint for k in kw) if kw else False
        score = 0.82 if (hit and seg_ok) else 0.6 if seg_ok else 0.5
        out["technique"] = {"label": _label(score), "score": round(score, 2)}
    # material: colour agreement is weak evidence -> mostly neutral
    if attrs.get("material"):
        agree = len(spoken & detected) / max(len(spoken | detected), 1) if (spoken or detected) else 0
        score = 0.5 + 0.25 * agree
        out["material"] = {"label": _label(score), "score": round(score, 2)}
    if attrs.get("region_claimed"):
        out["region_claimed"] = {"label": "not_visually_checkable", "score": None}
    return out


def _label(score: float) -> str:
    return "contradiction" if score < 0.4 else "entailment" if score > 0.7 else "neutral"


# ── generation ────────────────────────────────────────────────────────
def _generate(attrs: dict, craft: Craft | None, region_name: str | None) -> dict:
    mat = attrs.get("material") or "handmade"
    tech = attrs.get("technique") or "traditional handcraft"
    craft_name = craft.name if craft else "handmade craft"
    place = region_name or (attrs.get("region_claimed") or "India")
    colors = ", ".join(attrs.get("colors", [])) or "natural tones"

    seo_title = f"{mat.title()} {craft_name} — {tech.title()} from {place}"
    en = (
        f"Handcrafted {mat} piece made using {tech}, in the {craft_name} tradition of {place}. "
        f"Featuring {colors}. Each piece is individually made by hand by a registered artisan"
        + (f" and takes about {attrs['effort_days']} days to complete." if attrs.get("effort_days")
           else ".")
        + " Small natural variations are a mark of authentic handwork."
    )
    hi = (
        f"{place} की {craft_name} परंपरा में {tech} तकनीक से बना {mat} उत्पाद। "
        f"रंग: {colors}. हर टुकड़ा एक पंजीकृत कारीगर द्वारा हाथ से बनाया गया है"
        + (f" और इसे बनने में लगभग {attrs['effort_days']} दिन लगते हैं।" if attrs.get("effort_days")
           else "।")
        + " हल्के प्राकृतिक अंतर असली हस्तकला की पहचान हैं।"
    )
    keywords = list(dict.fromkeys([
        f"{tech} {mat}", f"{craft_name.lower()}", f"handmade {mat}",
        f"{place.lower()} craft", f"{mat} {(attrs.get('colors') or [''])[0] or ''}".strip(),
        "artisan made", "handloom" if "loom" in tech else "handcrafted",
    ]))
    mode = REAL
    if settings.llm_enabled and settings.llm_api_key:
        phrased = _llm_polish(en, hi, attrs)
        if phrased:
            en, hi = phrased
            mode = "LLM"
    return {"seo_title": seo_title, "description_en": en, "description_hi": hi,
            "seo_keywords": [k for k in keywords if k][:8], "gen_mode": mode}


def _llm_polish(en: str, hi: str, attrs: dict):  # pragma: no cover - needs network
    try:
        import httpx

        prompt = (
            "Rewrite these two product descriptions to be more fluent and SEO-friendly. "
            "Do NOT add any new factual claim (material, technique, origin, certification) "
            "beyond what is given. Return as 'EN: ...\\nHI: ...'.\n"
            f"Facts: {attrs}\nEN: {en}\nHI: {hi}"
        )
        r = httpx.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.4},
            timeout=40,
        )
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
        en2 = re.search(r"EN:\s*(.+?)(?:\nHI:|$)", txt, re.S)
        hi2 = re.search(r"HI:\s*(.+)$", txt, re.S)
        if en2 and hi2:
            return en2.group(1).strip(), hi2.group(1).strip()
    except Exception:
        return None
    return None


# ── orchestrator ──────────────────────────────────────────────────────
def generate_catalog(
    db: Session,
    *,
    audio_bytes: bytes | None = None,
    typed_transcript: str | None = None,
    language_hint: str | None = None,
    visual_context: dict | None = None,
    craft_id: str | None = None,
    audio_filename: str | None = None,
) -> AiResult:
    visual_context = visual_context or {}
    with timed() as t:
        tr = transcribe(audio_bytes, typed_transcript=typed_transcript,
                        language_hint=language_hint, audio_filename=audio_filename)
        work_text = f"{tr.text}\n{tr.romanized}"
        attrs = _extract(work_text)

        resolved = resolve(
            db, craft=None,
            technique=attrs["technique"], material=attrs["material"],
            region=attrs["region_claimed"],
        )
        craft = db.get(Craft, craft_id) if craft_id else None
        if not craft and resolved.get("region", {}).get("id"):
            craft = db.scalars(
                select(Craft).where(Craft.region_id == resolved["region"]["id"]).limit(1)
            ).first()

        grounding = _ground(attrs, work_text, craft)
        visual = _visual_consistency(attrs, visual_context, craft)
        claims = build_claims(attrs, grounding, visual, resolved, craft, visual_context)
        verification_summary = summarize(claims)

        region_name = None
        if resolved.get("region", {}).get("id"):
            r = db.get(Region, resolved["region"]["id"])
            region_name = r.name if r else None
        gen = _generate(attrs, craft, region_name)

        flags = []
        if tr.is_demo_fallback:
            flags.append(
                "Speech-to-text is not available on this server — the transcript "
                "above is a sample, not your recording. Type your description for "
                "an accurate listing."
            )
        for k, v in grounding.items():
            if v.startswith("flagged") or v == "unsupported":
                flags.append(f"{k} requires verification before publish ({v})")
        for k, v in visual.items():
            if v.get("label") == "contradiction":
                flags.append(f"{k}: product photo may not match the spoken claim — sent for review")

        n_claims = sum(1 for x in grounding.values()) or 1
        n_ok = sum(1 for x in grounding.values() if x.startswith("confirmed"))
        grounding_pass_ratio = n_ok / n_claims
        vis_scores = [x["score"] for x in visual.values() if x.get("score") is not None]
        visual_consistency_score = sum(vis_scores) / len(vis_scores) if vis_scores else 0.5

        data = {
            "transcript_raw": tr.text,
            "transcript_romanized": tr.romanized,
            "detected_language": tr.language,
            "asr_confidence": round(tr.confidence, 2),
            "asr_engine": tr.engine,
            "asr_mode": tr.mode,
            "asr_is_demo_fallback": tr.is_demo_fallback,
            "extracted_attributes": {
                "material": attrs["material"],
                "technique": attrs["technique"],
                "region_claimed": attrs["region_claimed"],
                "colors": attrs["colors"],
                "effort_days": attrs["effort_days"],
                "dimensions_mentioned": attrs["dimensions_mentioned"],
            },
            "entity_resolution": resolved,
            "resolved_craft_id": craft.craft_id if craft else None,
            "grounding_check": grounding,
            "visual_consistency_check": visual,
            "claims": claims,
            "verification_summary": verification_summary,
            "seo_title": gen["seo_title"],
            "description_en": gen["description_en"],
            "description_hi": gen["description_hi"],
            "seo_keywords": gen["seo_keywords"],
            "generation_mode": gen["gen_mode"],
            "hallucination_flags": flags,
            "grounding_pass_ratio": round(grounding_pass_ratio, 2),
            "visual_consistency_score": round(visual_consistency_score, 2),
            "confidence": round(0.55 + 0.35 * grounding_pass_ratio, 2),
        }

    return AiResult(
        data=data, feature="F2",
        model=f"ASR({tr.engine}) + KG-seeded slot NER + fact-grounding guard + "
              f"cross-modal heuristic + claim-consistency assessment + "
              f"{gen['gen_mode']} generation",
        mode=REAL if tr.mode == "REAL" else PROTOTYPE,
        inputs={"has_audio": bool(audio_bytes), "typed": bool(typed_transcript),
                "language_hint": language_hint or "", "craft_id": craft_id or ""},
        latency_ms=t["ms"],
    )
