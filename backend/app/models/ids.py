"""Human-readable prefixed identifiers (matches the spec's ID style, e.g.
``ART-000789``, ``PRD-004521``, ``CP-000123``).
"""
from __future__ import annotations

import secrets

_ALPHABET = "0123456789"


def new_id(prefix: str, width: int = 6) -> str:
    return f"{prefix}-" + "".join(secrets.choice(_ALPHABET) for _ in range(width))
