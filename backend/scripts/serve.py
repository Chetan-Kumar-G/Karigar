"""Dev server that binds every interface so a phone on the same Wi-Fi can reach it.

    python -m scripts.serve            # 0.0.0.0:8000, prints the LAN URL
    python -m scripts.serve --port 9000

It prints the exact `flutter run --dart-define=...` line to paste on the laptop,
or the address to type into the app's "Change server address" field on a phone.
"""
from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packets sent; just picks the egress iface
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true")
    args = ap.parse_args()

    ip = _lan_ip()
    bar = "=" * 64
    print(f"\n{bar}")
    print("  Kārigar backend — local network")
    print(f"{bar}")
    print(f"  Emulator (default) : http://10.0.2.2:{args.port}/api")
    print(f"  This machine       : http://localhost:{args.port}/api")
    print(f"  Phone on same Wi-Fi: http://{ip}:{args.port}/api")
    print(f"  Health check       : http://{ip}:{args.port}/health")
    try:
        from app.ai.f2_catalog.asr import asr_status

        _a = asr_status()
        print(f"  F2 live voice      : {'REAL via ' + _a['active_backend'] if _a['real_asr_available'] else 'demo fallback (no ASR engine)'}")
    except Exception:
        pass
    print()
    print("  Physical device — either:")
    print(f"    flutter run --dart-define=API_BASE_URL=http://{ip}:{args.port}/api")
    print(f"    or type  {ip}:{args.port}  into the app's 'Change server address'")
    print(f"{bar}\n")

    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
