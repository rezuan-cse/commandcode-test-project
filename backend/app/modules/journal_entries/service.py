"""Business logic for journal entries. Enforces double-entry balance."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.enums import JournalSource, Segment
from app.core.exceptions import DuplicateError, NotFoundError, UnbalancedEntryError
from app.core.money import money, ZERO
from app.modules.journal_entries import repository
from app.modules.journal_entries.models import JournalEntry, JournalLine
from app.modules.journal_entries.schemas import JournalEntryCreate, JournalLineIn


def total_debits(lines: list[JournalLineIn]) -> Decimal:
    """Sum the debit side of a proposed entry."""
    return money(sum((money(line.debit) for line in lines), ZERO))


def total_credits(lines: list[JournalLineIn]) -> Decimal:
    """Sum the credit side of a proposed entry."""
    return money(sum((money(line.credit) for line in lines), ZERO))


def assert_balanced(lines: list[JournalLineIn]) -> None:
    """Raise :class:`UnbalancedEntryError` unless debits equal credits."""
    debits, credits = total_debits(lines), total_credits(lines)
    if debits != credits:
        raise UnbalancedEntryError(
            f"Entry is unbalanced: debits {debits} != credits {credits}"
        )


def build_entry(
    *,
    voucher_no: str,
    entry_date: date,
    lines: list[JournalLineIn],
    source: JournalSource = JournalSource.MANUAL,
    narration: str | None = None,
    reference: str | None = None,
    posted_by: str = "system",
) -> JournalEntry:
    """Construct (but do not persist) a validated, balanced journal entry.

    Shared by manual entry and by the production/sales/purchase auto-posters.
    """
    assert_balanced(lines)
    entry = JournalEntry(
        voucher_no=voucher_no,
        entry_date=entry_date,
        narration=narration,
        source=source,
        reference=reference,
        posted_by=posted_by,
    )
    entry.lines = [
        JournalLine(
            account_code=line.account_code,
            segment=line.segment,
            debit=money(line.debit),
            credit=money(line.credit),
            narration=line.narration,
        )
        for line in lines
    ]
    return entry


def post_manual_entry(db: Session, payload: JournalEntryCreate) -> JournalEntry:
    """Validate, persist, and commit a manual journal entry."""
    if repository.get_by_voucher(db, payload.voucher_no) is not None:
        raise DuplicateError(f"Voucher {payload.voucher_no} already exists")
    entry = build_entry(
        voucher_no=payload.voucher_no,
        entry_date=payload.entry_date,
        lines=payload.lines,
        source=JournalSource.MANUAL,
        narration=payload.narration,
        reference=payload.reference,
        posted_by=payload.posted_by,
    )
    repository.add_entry(db, entry)
    db.commit()
    return entry


def list_entries(
    db: Session, *, date_from: date | None = None, date_to: date | None = None, limit: int = 200
) -> list[JournalEntry]:
    """List journal entries."""
    return repository.list_entries(db, date_from=date_from, date_to=date_to, limit=limit)


def get_entry(db: Session, entry_id: int) -> JournalEntry:
    """Fetch one entry or raise :class:`NotFoundError`."""
    entry = repository.get_entry(db, entry_id)
    if entry is None:
        raise NotFoundError(f"Journal entry {entry_id} not found")
    return entry


def lines_for_segment(
    account_code: str, segment: Segment, debit: Decimal, credit: Decimal, narration: str | None = None
) -> JournalLineIn:
    """Small helper so auto-posters can construct lines tersely."""
    return JournalLineIn(
        account_code=account_code,
        segment=segment,
        debit=money(debit),
        credit=money(credit),
        narration=narration,
    )
