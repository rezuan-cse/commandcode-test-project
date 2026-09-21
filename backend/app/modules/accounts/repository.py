"""All database queries for the Chart of Accounts live here."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AccountType, Segment
from app.modules.accounts.models import Account


def list_accounts(
    db: Session,
    *,
    segment: Segment | None = None,
    account_type: AccountType | None = None,
    search: str | None = None,
) -> list[Account]:
    """Return accounts, optionally filtered by segment, type, or name/code search."""
    stmt = select(Account).order_by(Account.code)
    if segment is not None:
        stmt = stmt.where(Account.segment == segment)
    if account_type is not None:
        stmt = stmt.where(Account.account_type == account_type)
    if search:
        needle = f"%{search.lower()}%"
        stmt = stmt.where(
            Account.name_en.ilike(needle) | Account.code.ilike(needle)
        )
    return list(db.execute(stmt).scalars().all())


def get_account(db: Session, code: str) -> Account | None:
    """Fetch a single account by code."""
    return db.get(Account, code)


def add_account(db: Session, account: Account) -> Account:
    """Persist a new account."""
    db.add(account)
    db.flush()
    return account
