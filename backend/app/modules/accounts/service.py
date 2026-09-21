"""Business logic for the Chart of Accounts. No HTTP and no raw SQL here."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import AccountType, DEBIT_NATURED_TYPES, NormalBalance, Segment
from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.accounts import repository
from app.modules.accounts.models import Account
from app.modules.accounts.schemas import AccountCreate, AccountUpdate


def default_normal_balance(account_type: AccountType) -> NormalBalance:
    """Return the natural balance side for an account type."""
    if account_type in DEBIT_NATURED_TYPES:
        return NormalBalance.DEBIT
    return NormalBalance.CREDIT


def list_accounts(
    db: Session,
    *,
    segment: Segment | None = None,
    account_type: AccountType | None = None,
    search: str | None = None,
) -> list[Account]:
    """List accounts with optional filters."""
    return repository.list_accounts(
        db, segment=segment, account_type=account_type, search=search
    )


def get_account(db: Session, code: str) -> Account:
    """Fetch an account or raise :class:`NotFoundError`."""
    account = repository.get_account(db, code)
    if account is None:
        raise NotFoundError(f"Account {code} not found")
    return account


def create_account(db: Session, payload: AccountCreate) -> Account:
    """Create an account, rejecting duplicate codes."""
    if repository.get_account(db, payload.code) is not None:
        raise DuplicateError(f"Account code {payload.code} already exists")
    account = Account(
        code=payload.code,
        name_en=payload.name_en,
        name_bn=payload.name_bn,
        account_type=payload.account_type,
        segment=payload.segment,
        normal_balance=payload.normal_balance,
    )
    repository.add_account(db, account)
    db.commit()
    return account


def update_account(db: Session, code: str, payload: AccountUpdate) -> Account:
    """Update an existing account's mutable fields."""
    account = get_account(db, code)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    return account
