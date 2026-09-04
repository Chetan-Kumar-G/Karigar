"""Shared plumbing for the F1–F7 AI services.

Every feature exposes a small, stable interface (spec §29) so a prototype
implementation can be swapped for a production model without the API layer
noticing.  Every invocation records an :class:`~app.models.marketplace.AiRun`
row carrying the technical-metadata object the judge screen renders (spec §45).
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.marketplace import AiRun

log = get_logger("ai")

# Honesty labels used consistently across the codebase and surfaced to judges.
REAL = "REAL"
PROTOTYPE = "PROTOTYPE"
SIMULATED_DATA = "SIMULATED_DATA"
FALLBACK = "FALLBACK"


@dataclass
class AiResult:
    """Uniform envelope: the payload plus the metadata block for the debug screen."""

    data: dict[str, Any]
    feature: str
    model: str
    mode: str = REAL
    version: str = "prototype-v1"
    inputs: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0

    def metadata(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "model": self.model,
            "mode": self.mode,
            "version": self.version,
            "inputs": list(self.inputs.keys()),
            "latency_ms": round(self.latency_ms, 1),
        }

    def persist(self, db: Session, subject_id: str | None = None) -> None:
        db.add(
            AiRun(
                feature=self.feature,
                model=self.model,
                version=self.version,
                mode=self.mode,
                subject_id=subject_id,
                inputs=self.inputs,
                output=_json_safe(self.data),
                latency_ms=self.latency_ms,
            )
        )


class _Timer:
    """Elapsed-time probe. ``t.ms`` / ``t["ms"]`` both work and are valid even
    when read from inside the ``with`` block (e.g. an early ``return``)."""

    __slots__ = ("_start",)

    def __init__(self) -> None:
        self._start = time.perf_counter()

    @property
    def ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0

    def __getitem__(self, _key: str) -> float:
        return self.ms


@contextmanager
def timed():
    yield _Timer()


def _json_safe(obj: Any) -> Any:
    """Trim large / non-serialisable values before they hit the DB."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items() if not _is_bulky(k, v)}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj][:50]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _is_bulky(key: str, value: Any) -> bool:
    return key in {"embedding", "mask", "raw_pixels"} or (
        isinstance(value, str) and len(value) > 4000
    )
