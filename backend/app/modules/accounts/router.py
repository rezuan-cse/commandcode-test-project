"""Thin HTTP routes for the Chart of Accounts. Delegates to ``service.py``."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import AccountType, Segment
from app.modules.accounts import service
from app.modules.accounts.schemas import AccountCreate, AccountOut, AccountUpdate
from app.modules.users_roles.service import require

router = APIRouter(prefix="/accounts", tags=["accounts"])

CAN_READ = Depends(require("accounts", write=False))
CAN_WRITE = Depends(require("accounts", write=True))


@router.get("", response_model=list[AccountOut], dependencies=[CAN_READ])
def list_accounts(
    segment: Segment | None = Query(default=None),
    account_type: AccountType | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AccountOut]:
    """List chart-of-accounts entries."""
    return service.list_accounts(db, segment=segment, account_type=account_type, search=search)


@router.get("/{code}", response_model=AccountOut, dependencies=[CAN_READ])
def get_account(code: str, db: Session = Depends(get_db)) -> AccountOut:
    """Fetch one account by code."""
    return service.get_account(db, code)


@router.post("", response_model=AccountOut, status_code=201, dependencies=[CAN_WRITE])
def create_account(payload: AccountCreate, db: Session = Depends(get_db)) -> AccountOut:
    """Create a new account."""
    return service.create_account(db, payload)


@router.patch("/{code}", response_model=AccountOut, dependencies=[CAN_WRITE])
def update_account(
    code: str, payload: AccountUpdate, db: Session = Depends(get_db)
) -> AccountOut:
    """Update an account."""
    return service.update_account(db, code, payload)
