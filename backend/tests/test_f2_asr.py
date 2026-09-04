"""F2 ASR resolution + honesty labelling (Phase 5)."""
from __future__ import annotations

from app.ai.f2_catalog import asr as asr_mod
from app.ai.f2_catalog.asr import asr_status, transcribe


def test_typed_transcript_is_users_own_words_not_demo():
    t = transcribe(None, typed_transcript="cotton dupatta, block printed", language_hint="hi")
    assert t.mode == "FALLBACK"
    assert t.engine == "typed-input"
    assert t.is_demo_fallback is False


def test_no_input_uses_demo_and_is_flagged():
    t = transcribe(None, typed_transcript=None, language_hint="hi")
    assert t.is_demo_fallback is True
    assert t.engine == "deterministic-demo-transcript"


def test_audio_without_real_asr_is_marked_demo_fallback(monkeypatch):
    # Force both real backends unavailable.
    monkeypatch.setattr(asr_mod, "_try_whisper", lambda *_a, **_k: None)
    monkeypatch.setattr(asr_mod, "_try_api", lambda *_a, **_k: None)
    t = transcribe(b"\x00" * 2048, typed_transcript=None, language_hint="hi")
    assert t.mode == "FALLBACK"
    assert t.is_demo_fallback is True
    assert t.engine == "demo-fallback"  # distinct from the no-input case


def test_audio_with_typed_fallback_prefers_typed_over_demo(monkeypatch):
    monkeypatch.setattr(asr_mod, "_try_whisper", lambda *_a, **_k: None)
    monkeypatch.setattr(asr_mod, "_try_api", lambda *_a, **_k: None)
    t = transcribe(b"\x00" * 2048, typed_transcript="my own words", language_hint="hi")
    assert t.engine == "typed-input"
    assert t.is_demo_fallback is False


def test_real_whisper_result_is_real_and_not_demo(monkeypatch):
    real = asr_mod.Transcript("actual spoken text", "actual spoken text", "hi",
                              0.91, "REAL", "faster-whisper", is_demo_fallback=False)
    monkeypatch.setattr(asr_mod, "_try_whisper", lambda *_a, **_k: real)
    t = transcribe(b"\x00" * 2048, language_hint="hi")
    assert t.mode == "REAL"
    assert t.is_demo_fallback is False
    assert t.text == "actual spoken text"


def test_audio_filename_is_threaded_to_the_api_backend(monkeypatch):
    seen = {}

    def fake_api(_bytes, ext=".m4a"):
        seen["ext"] = ext
        return asr_mod.Transcript("x", "x", "hi", 0.9, "REAL", "api:whisper-1")

    monkeypatch.setattr(asr_mod.settings, "asr_backend", "api")
    monkeypatch.setattr(asr_mod.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(asr_mod, "_try_whisper", lambda *_a, **_k: None)
    monkeypatch.setattr(asr_mod, "_try_api", fake_api)
    transcribe(b"\x00" * 2048, language_hint="hi", audio_filename="voice_123.webm")
    assert seen["ext"] == ".webm"
    # an unknown extension falls back to a safe default the API accepts
    transcribe(b"\x00" * 2048, language_hint="hi", audio_filename="blob")
    assert seen["ext"] == ".m4a"


def test_asr_status_shape():
    s = asr_status()
    assert set(s) >= {"real_asr_available", "active_backend", "configured_backend"}
    assert isinstance(s["real_asr_available"], bool)


def test_asr_status_endpoint(client):
    r = client.get("/api/catalog/asr-status")
    assert r.status_code == 200
    assert "active_backend" in r.json()


def test_catalog_handles_transcript_with_no_colour_word(client):
    # regression: a typed/spoken description without any colour term used to
    # crash keyword generation with "list index out of range".
    tok = client.post("/api/auth/otp/verify",
                      json={"phone": "9700000001", "otp": "123456"}).json()["access_token"]
    H = {"Authorization": f"Bearer {tok}"}
    pid = client.post("/api/product", data={"title": "Plate", "craft_id": "CRAFT-THANJAVUR",
                                            "category": "wall-decor"}, headers=H).json()["product_id"]
    r = client.post("/api/catalog/generate", data={
        "product_id": pid, "language_hint": "ta",
        "typed_transcript": "brass repousse plate handmade in Thanjavur, took four days",
    })
    assert r.status_code == 200
    j = r.json()
    assert j["description_en"] and j["description_hi"] and j["seo_keywords"]
    assert j["extracted_attributes"]["colors"] == []


def test_catalog_flags_demo_fallback_for_audio(client, monkeypatch):
    monkeypatch.setattr(asr_mod, "_try_whisper", lambda *_a, **_k: None)
    monkeypatch.setattr(asr_mod, "_try_api", lambda *_a, **_k: None)
    r = client.post(
        "/api/catalog/generate",
        files={"voice_note": ("v.m4a", b"\x00" * 4096, "audio/m4a")},
        data={"language_hint": "hi"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["asr_is_demo_fallback"] is True
    assert any("sample" in f.lower() or "not your recording" in f.lower()
               for f in j["hallucination_flags"])
