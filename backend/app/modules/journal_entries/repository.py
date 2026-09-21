"""All database queries for journal entries live here."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.journal_entries.models import JournalEntry


def list_entries(
    db: Session,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 200,
) -> list[JournalEntry]:
    """List journal entries, newest first, with their lines eagerly loaded."""
    stmt = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .order_by(JournalEntry.entry_date.desc(), JournalEntry.id.desc())
        .limit(limit)
    )
    if date_from is not None:
        stmt = stmt.where(JournalEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(JournalEntry.entry_date <= date_to)
    return list(db.execute(stmt).scalars().all())


def get_entry(db: Session, entry_id: int) -> JournalEntry | None:
    """Fetch one entry with lines."""
    return db.get(JournalEntry, entry_id)


def get_by_voucher(db: Session, voucher_no: str) -> JournalEntry | None:
    """Look up an entry by its unique voucher number."""
    stmt = select(JournalEntry).where(JournalEntry.voucher_no == voucher_no)
    return db.execute(stmt).scalar_one_or_none()


def add_entry(db: Session, entry: JournalEntry) -> JournalEntry:
    """Persist a new entry (and its lines)."""
    db.add(entry)
    db.flush()
    return entry
