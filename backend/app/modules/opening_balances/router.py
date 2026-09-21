"""Thin HTTP routes for opening balances."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.opening_balances import service
from app.modules.opening_balances.schemas import OpeningBalanceSummary

router = APIRouter(prefix="/opening-balances", tags=["opening-balances"])


@router.get("", response_model=OpeningBalanceSummary)
def get_opening_balances(
    as_of: date | None = Query(default=None), db: Session = Depends(get_db)
) -> OpeningBalanceSummary:
    """Return opening balances plus the balance check."""
    return service.get_summary(db, as_of)
