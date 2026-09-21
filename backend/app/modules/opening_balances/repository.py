"""All database queries for opening balances live here."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.opening_balances.models import OpeningBalance


def list_for_date(db: Session, as_of: date | None = None) -> list[OpeningBalance]:
    """Return opening balances, optionally for a specific cutover date."""
    stmt = select(OpeningBalance).order_by(OpeningBalance.account_code)
    if as_of is not None:
        stmt = stmt.where(OpeningBalance.as_of_date == as_of)
    return list(db.execute(stmt).scalars().all())


def add_all(db: Session, rows: list[OpeningBalance]) -> None:
    """Bulk-insert opening balance rows."""
    db.add_all(rows)
    db.flush()
