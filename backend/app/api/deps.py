"""FastAPI dependencies: DB session, optional/required identity from JWT."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db

__all__ = ["get_db", "Identity", "current_identity", "optional_identity"]


@dataclass
class Identity:
    subject: str
    role: str          # artisan | buyer | demo
    artisan_id: str | None = None
    buyer_id: str | None = None
    name: str | None = None


def _parse(authorization: str | None) -> Identity | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return Identity(
        subject=payload.get("sub", ""),
        role=payload.get("role", "demo"),
        artisan_id=payload.get("artisan_id"),
        buyer_id=payload.get("buyer_id"),
        name=payload.get("name"),
    )


def optional_identity(authorization: str | None = Header(default=None)) -> Identity | None:
    return _parse(authorization)


def current_identity(authorization: str | None = Header(default=None)) -> Identity:
    ident = _parse(authorization)
    if ident is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    return ident


def get_session(db: Session = Depends(get_db)) -> Session:
    return db
