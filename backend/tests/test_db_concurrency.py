"""Concurrent-write hardening for SQLite (spec §26 db-failure handling).

FastAPI runs sync routes in a threadpool, so two near-simultaneous requests
(e.g. a user double-tapping Inventory's +/-) can open overlapping SQLite write
transactions. Without a generous busy-timeout the second one raises
"database is locked", surfaced as a bare 500 even though the first request's
write already committed. `busy_timeout` (session.py) should absorb this."""
from __future__ import annotations

import threading

from sqlalchemy import select

from app.models import Artisan, Inventory, Product


def test_concurrent_inventory_writes_never_bare_500(client, db):
    artisan = db.scalars(select(Artisan)).first()
    product = db.scalars(
        select(Product).where(Product.artisan_id == artisan.artisan_id)
    ).first()
    if not db.get(Inventory, product.product_id):
        db.add(Inventory(product_id=product.product_id, available_units=5))
        db.commit()

    login = client.post("/api/auth/otp/request",
                         json={"phone": artisan.phone, "role": "artisan"})
    assert login.status_code == 200
    tok = client.post("/api/auth/otp/verify",
                       json={"phone": artisan.phone, "otp": "123456", "role": "artisan"}
                       ).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    results: list[int] = []
    errors: list[str] = []

    def _write(units: int) -> None:
        try:
            r = client.post(f"/api/product/{product.product_id}/inventory",
                            data={"available_units": str(units)}, headers=headers)
            results.append(r.status_code)
        except Exception as exc:  # pragma: no cover - would itself be the bug
            errors.append(str(exc))

    threads = [threading.Thread(target=_write, args=(u,)) for u in range(1, 13)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=25)

    assert not errors, errors
    assert len(results) == 12
    # every request either succeeded, or got the *friendly, retryable* 503 —
    # never an unhandled bare 500 (which is what "database is locked" used to
    # surface as before the busy-timeout fix).
    assert all(code in (200, 503) for code in results), results
