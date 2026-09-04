"""Engine / session factory. Works for both SQLite (default) and Postgres."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("db")

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    # `timeout` is the python sqlite3 driver's own wait-for-lock grace period.
    # FastAPI runs sync routes in a threadpool, so two quick taps (e.g. a user
    # double-tapping +/- in Inventory) can genuinely open two concurrent write
    # transactions; without a generous timeout the second one raises
    # "database is locked" even though the first one already committed —
    # visible as a 500 on a change that, confusingly, still went through.
    _connect_args = {"check_same_thread": False, "timeout": 20}

engine: Engine = create_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - infra glue
    if settings.database_url.startswith("sqlite"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA journal_mode=WAL")
        # authoritative SQLite-side counterpart to connect_args["timeout"] above.
        cur.execute("PRAGMA busy_timeout=20000")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_postgres() -> bool:
    return engine.url.get_backend_name().startswith("postgres")
