"""Business logic for opening balances."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.core.money import money, ZERO
from app.modules.opening_balances import repository
from app.modules.opening_balances.models import OpeningBalance
from app.modules.opening_balances.schemas import OpeningBalanceOut, OpeningBalanceSummary


def summarise(rows: list[OpeningBalance], as_of: date | None = None) -> OpeningBalanceSummary:
    """Compute batch totals and prove debits equal credits."""
    debits = money(sum((money(r.debit) for r in rows), ZERO))
    credits = money(sum((money(r.credit) for r in rows), ZERO))
    effective_date = as_of or (rows[0].as_of_date if rows else date.today())
    return OpeningBalanceSummary(
        as_of_date=effective_date,
        total_debit=debits,
        total_credit=credits,
        difference=money(debits - credits),
        balanced=debits == credits,
        locked=all(r.locked for r in rows) if rows else False,
        rows=[OpeningBalanceOut.model_validate(r) for r in rows],
    )


def get_summary(db: Session, as_of: date | None = None) -> OpeningBalanceSummary:
    """Return the opening-balance batch with totals."""
    rows = repository.list_for_date(db, as_of)
    return summarise(rows, as_of)
