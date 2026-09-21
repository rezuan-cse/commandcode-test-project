"""Read-only queries backing the reports. Reports are always derived live."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AccountType, JournalSource
from app.modules.accounts.models import Account
from app.modules.journal_entries.models import JournalEntry, JournalLine
from app.modules.opening_balances.models import OpeningBalance


@dataclass
class AccountMovement:
    """Opening and period totals accumulated for one account."""

    opening_debit: Decimal = Decimal("0")
    opening_credit: Decimal = Decimal("0")
    period_debit: Decimal = Decimal("0")
    period_credit: Decimal = Decimal("0")


@dataclass
class Movements:
    """Movement totals keyed by account code."""

    by_account: dict[str, AccountMovement] = field(default_factory=dict)

    def get(self, code: str) -> AccountMovement:
        """Fetch (or create) the movement bucket for an account."""
        if code not in self.by_account:
            self.by_account[code] = AccountMovement()
        return self.by_account[code]


def all_accounts(db: Session) -> list[Account]:
    """Return every account ordered by code."""
    return list(db.execute(select(Account).order_by(Account.code)).scalars().all())


def opening_balances(db: Session) -> list[OpeningBalance]:
    """Return all opening balance rows."""
    return list(db.execute(select(OpeningBalance)).scalars().all())


def period_lines(
    db: Session, date_from: date | None = None, date_to: date | None = None
) -> list[tuple[JournalLine, date, JournalSource]]:
    """Return journal lines in a date range, with their entry date and source."""
    stmt = (
        select(JournalLine, JournalEntry.entry_date, JournalEntry.source)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
        .order_by(JournalEntry.entry_date, JournalEntry.id)
    )
    if date_from is not None:
        stmt = stmt.where(JournalEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(JournalEntry.entry_date <= date_to)
    return list(db.execute(stmt).all())


def period_lines_by_segment(
    db: Session, date_from: date | None, date_to: date | None
) -> list[tuple[JournalLine, AccountType]]:
    """Return journal lines joined to their account type, for P&L work."""
    stmt = (
        select(JournalLine, Account.account_type)
        .join(Account, Account.code == JournalLine.account_code)
        .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
    )
    if date_from is not None:
        stmt = stmt.where(JournalEntry.entry_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(JournalEntry.entry_date <= date_to)
    return [(line, acc_type) for line, acc_type in db.execute(stmt).all()]
