"""Verify the F2 live-voice (ASR) pipeline without recording anything.

    python -m scripts.check_asr            # uses the current .env / venv
    python -m scripts.check_asr path/to/real_voice.m4a   # transcribe a real clip

Prints which engine handled it and the text. Exit code 0 if REAL ASR ran.
"""
from __future__ import annotations

import io
import math
import struct
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ai.f2_catalog.asr import asr_status, transcribe  # noqa: E402


def _beep_wav() -> bytes:
    buf = io.BytesIO()
    w = wave.open(buf, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(16000)
    w.writeframes(b"".join(
        struct.pack("<h", int(2500 * math.sin(2 * math.pi * 240 * t / 16000)))
        for t in range(16000)
    ))
    w.close()
    return buf.getvalue()


def main() -> None:
    bar = "=" * 64
    s = asr_status()
    print(f"\n{bar}\n  F2 ASR status\n{bar}")
    for k in ("real_asr_available", "active_backend", "configured_backend",
              "whisper_installed", "whisper_model", "whisper_language",
              "api_key_configured", "api_model"):
        print(f"  {k:22} {s.get(k)}")
    print(f"  note: {s['note']}")

    have_file = len(sys.argv) > 1
    if have_file:
        p = Path(sys.argv[1])
        data, name = p.read_bytes(), p.name
        print(f"\n  Transcribing your file: {name} ({len(data):,} bytes)")
    else:
        data, name = _beep_wav(), "beep.wav"
        print("\n  No file given — running a 1s test tone through the pipeline.")
        print("  A tone has no speech, so the text will be empty even when the")
        print("  engine is fine. Pass a real voice clip for an end-to-end check.")

    t = transcribe(data, language_hint="hi", audio_filename=name)
    print(f"\n{bar}\n  Result\n{bar}")
    print(f"  engine           {t.engine}")
    print(f"  mode             {t.mode}")
    print(f"  is_demo_fallback {t.is_demo_fallback}")
    print(f"  language         {t.language}")
    print(f"  confidence       {t.confidence}")
    print(f"  text             {t.text[:400]!r}")

    if have_file:
        ok = t.mode == "REAL" and not t.is_demo_fallback
        msg = ("REAL speech-to-text transcribed your file."
               if ok else "Your file did NOT go through real ASR — see status above.")
    else:
        ok = s["real_asr_available"]
        msg = ("ASR engine is installed and wired — record a real clip in the app "
               "and it will be transcribed."
               if ok else "No ASR engine available — set SIH_LLM_API_KEY or use .venv312.")
    print(f"\n  {msg}\n")
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
