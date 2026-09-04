"""F2 ASR stage — pluggable, degrades gracefully (spec §4, §5, §14).

Resolution order (first that succeeds wins):
  1. ``faster-whisper`` if installed and ``SIH_ASR_BACKEND`` allows  → **REAL**
  2. OpenAI-compatible ``/audio/transcriptions`` if ``SIH_LLM_API_KEY`` set → **REAL**
  3. caller-supplied typed transcript (the spec's "typed fallback")        → **FALLBACK** (still the user's own words)
  4. deterministic demo transcript keyed by language                       → **FALLBACK / demo**

Honesty contract (Phase 5): when audio *was* supplied but no real engine could
transcribe it, the result is still usable for the demo flow **but is explicitly
marked** ``is_demo_fallback=True`` with engine ``"demo-fallback"`` — the UI must
not present it as the user's own speech.

IndicWav2Vec / IndicTrans2 are the documented production upgrade (spec §14) —
faster-whisper needs CTranslate2, which currently has no CPython 3.14 wheel, so
on a 3.14 host use the API backend (set ``SIH_LLM_API_KEY``) or run under
Python 3.12 / Docker where ``pip install faster-whisper`` works.
"""
from __future__ import annotations

import mimetypes
import os
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("f2.asr")

# Domain vocabulary fed to Whisper as an initial prompt so craft terms are
# transcribed correctly ("Madhubani", "dupatta", "Dhokra", "repoussé", ...).
_ASR_HINT = (
    "Artisan describes a handmade craft product: material, technique, colours, "
    "region and days taken. Vocabulary: handloom, handwoven, cotton, silk, "
    "block print, Madhubani, Mithila, Pattachitra, Kutch, mirror work, embroidery, "
    "Dhokra, brass, repoussé, Thanjavur art plate, Channapatna, lacquerware, "
    "bamboo, cane, terracotta, blue pottery, Pashmina, dupatta, saree, natural dye, GI."
)

# One cached model per (name) so we don't reload the checkpoint on every request.
_MODEL_CACHE: dict = {}

# Formats an OpenAI-compatible /audio/transcriptions endpoint accepts.
_ASR_API_EXTS = {".m4a", ".mp3", ".mp4", ".mpeg", ".mpga", ".wav", ".webm", ".ogg", ".flac"}


def _audio_ext(filename: str | None) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if ext in _ASR_API_EXTS else ".m4a"  # the app records m4a on Android

_DEMO = {
    "mai": {
        "text": "Ee cotton ke dupatta hamra haath se block print kयel gel achhi. "
                "Madhubani ke design achhi, peela aur laal rang. Chaar din laagal banawe mे.",
        "roman": "Yeh cotton ka dupatta maine haath se block print kiya hai. "
                 "Madhubani ka design hai, peela aur laal rang. Chaar din lage banane mein.",
        "language": "mai",
    },
    "hi": {
        "text": "यह सूती दुपट्टा मैंने हाथ से ब्लॉक प्रिंट किया है। मधुबनी का पारंपरिक डिज़ाइन है, "
                "पीला और लाल रंग। इसे बनाने में चार दिन लगे। प्राकृतिक रंगों का उपयोग किया है।",
        "roman": "Yeh suti dupatta maine haath se block print kiya hai. Madhubani ka "
                 "paramparik design hai, peela aur laal rang. Banane mein chaar din lage.",
        "language": "hi",
    },
    "as": {
        "text": "Moi ei bah'r pora basket khon hat'edi bua. Assam'r sthaniya kala. "
                "Duta din lage eta bonabo. Prakritik beth byawohar korisu.",
        "roman": "Maine yeh baans ki tokri haath se bunee hai. Assam ki sthaniya kala hai. "
                 "Do din lagte hain ek banane mein. Prakritik cane istemal kiya hai.",
        "language": "as",
    },
}


@dataclass
class Transcript:
    text: str
    romanized: str
    language: str
    confidence: float
    mode: str            # REAL | FALLBACK
    engine: str
    is_demo_fallback: bool = False   # True → NOT the user's own speech


@lru_cache(maxsize=1)
def _whisper_installed() -> bool:
    try:
        import faster_whisper  # noqa: F401
        return True
    except Exception:
        return False


def asr_status() -> dict:
    """What the F2 voice pipeline can actually do on this server right now."""
    backend = settings.asr_backend.lower()
    whisper_ok = _whisper_installed() and backend in ("auto", "whisper")
    api_ok = bool(settings.llm_api_key) and backend in ("auto", "api")
    if whisper_ok:
        active = "faster-whisper"
    elif api_ok:
        active = "openai-compatible-api"
    else:
        active = "demo-fallback"
    return {
        "real_asr_available": whisper_ok or api_ok,
        "active_backend": active,
        "configured_backend": backend,
        "whisper_installed": _whisper_installed(),
        "whisper_model": settings.whisper_model,
        "whisper_language": settings.whisper_language,
        "api_model": settings.asr_api_model,
        "api_base_url": settings.llm_base_url,
        "api_key_configured": bool(settings.llm_api_key),
        "note": (
            "Real speech-to-text is active." if (whisper_ok or api_ok) else
            "No ASR engine available — recorded audio falls back to a clearly "
            "marked demo transcript. Set SIH_LLM_API_KEY, or install "
            "faster-whisper on Python 3.12 / Docker."
        ),
    }


def transcribe(
    audio_bytes: bytes | None,
    *,
    typed_transcript: str | None = None,
    language_hint: str | None = None,
    audio_filename: str | None = None,
) -> Transcript:
    backend = settings.asr_backend.lower()
    ext = _audio_ext(audio_filename)

    if audio_bytes and backend in ("auto", "whisper"):
        t = _try_whisper(audio_bytes, ext)
        if t:
            return t
    if audio_bytes and backend in ("auto", "api") and settings.llm_api_key:
        t = _try_api(audio_bytes, ext)
        if t:
            return t

    # A typed description is still the artisan's own words — not a demo.
    if typed_transcript and typed_transcript.strip():
        return Transcript(typed_transcript.strip(), typed_transcript.strip(),
                          language_hint or "hi", 0.99, "FALLBACK", "typed-input",
                          is_demo_fallback=False)

    demo = _DEMO.get((language_hint or "hi").lower(), _DEMO["hi"])
    # Distinguish "user recorded audio but we couldn't transcribe it" from
    # "no input at all (SIH demo button)". Both are demo text, both are flagged.
    engine = "demo-fallback" if audio_bytes else "deterministic-demo-transcript"
    if audio_bytes:
        log.info("ASR unavailable for supplied audio (%d bytes) — using marked demo transcript",
                 len(audio_bytes))
    return Transcript(demo["text"], demo["roman"], demo["language"], 0.86,
                      "FALLBACK", engine, is_demo_fallback=True)


def _try_whisper(audio_bytes: bytes, ext: str = ".m4a") -> Transcript | None:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception:
        return None
    path = None
    try:  # pragma: no cover - only runs when the optional dep is present
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as fh:
            fh.write(audio_bytes)
            path = fh.name
        model = _MODEL_CACHE.get(settings.whisper_model)
        if model is None:
            model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
            _MODEL_CACHE[settings.whisper_model] = model
        lang = None if (settings.whisper_language or "auto") == "auto" else settings.whisper_language
        segments, info = model.transcribe(
            path,
            language=lang,
            vad_filter=True,
            beam_size=5,
            temperature=[0.0, 0.2, 0.4],          # retry with more diversity if a chunk fails
            condition_on_previous_text=False,     # short clips: don't drift on earlier text
            initial_prompt=_ASR_HINT,             # bias toward craft vocabulary
        )
        txt = " ".join(s.text.strip() for s in segments).strip()
        if not txt:
            return None
        return Transcript(txt, txt, info.language or "hi",
                          float(getattr(info, "language_probability", 0.8)), "REAL",
                          "faster-whisper", is_demo_fallback=False)
    except Exception as exc:  # pragma: no cover
        log.warning("faster-whisper failed: %s", exc)
        return None
    finally:  # pragma: no cover
        if path:
            try:
                os.unlink(path)
            except OSError:
                pass


def _try_api(audio_bytes: bytes, ext: str = ".m4a") -> Transcript | None:  # pragma: no cover - needs network
    try:
        import httpx

        mime = mimetypes.types_map.get(ext, "application/octet-stream")
        r = httpx.post(
            f"{settings.llm_base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            files={"file": (f"voice{ext}", audio_bytes, mime)},
            data={"model": settings.asr_api_model},
            timeout=90,
        )
        r.raise_for_status()
        txt = r.json().get("text", "").strip()
        return Transcript(txt, txt, "hi", 0.9, "REAL",
                          f"api:{settings.asr_api_model}", is_demo_fallback=False) if txt else None
    except Exception as exc:
        log.warning("ASR API failed: %s", exc)
        return None
