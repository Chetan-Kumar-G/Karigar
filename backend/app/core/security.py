"""Prototype auth: mock phone-OTP → JWT.

Deliberately simple (spec §3 "do NOT introduce unnecessary authentication
complexity that prevents the demo from running"): any phone number logs in with
the mock OTP (default ``123456``) and receives a signed JWT carrying the
resolved artisan/buyer identity.
"""
from __future__ import annotations

import datetime as dt
from typing import Any

import jwt

from app.core.config import settings


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.jwt_expiry_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
