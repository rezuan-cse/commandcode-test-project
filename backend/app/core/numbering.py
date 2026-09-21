"""Voucher-number generation shared by the auto-posting modules.

Voucher numbers must be unique across all journal entries, and the seeded
history already occupies ``PROD-001`` through ``PROD-003`` and ``SALE-001``
without any matching order rows. Allocation therefore consults the journal
table as well as the order table, so a newly posted run never collides with an
imported voucher.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session


def _max_suffix(db: Session, model: type, column_name: str, prefix: str) -> int:
    """Return the highest numeric suffix in use for a prefix in one table."""
    column = getattr(model, column_name)
    stmt = select(column).where(column.like(f"{prefix}-%"))
    highest = 0
    for (value,) in db.execute(stmt).all():
        if not value:
            continue
        suffix = str(value).rsplit("-", 1)[-1]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return highest


def next_voucher(
    db: Session,
    model: type,
    column_name: str,
    prefix: str,
    also: list[tuple[type, str]] | None = None,
) -> str:
    """Allocate the next sequential voucher number, e.g. ``PROD-004``.

    ``also`` lists additional (model, column) pairs whose values share the same
    numbering namespace, which is how order numbers avoid clashing with the
    journal entries imported from the workbook.
    """
    highest = _max_suffix(db, model, column_name, prefix)
    for extra_model, extra_column in also or []:
        highest = max(highest, _max_suffix(db, extra_model, extra_column, prefix))
    return f"{prefix}-{highest + 1:03d}"
