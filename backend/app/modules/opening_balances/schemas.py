"""Pydantic schemas for opening balances."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.enums import Segment


class OpeningBalanceOut(BaseModel):
    """An opening balance row as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_code: str
    segment: Segment
    debit: Decimal
    credit: Decimal
    as_of_date: date
    locked: bool


class OpeningBalanceSummary(BaseModel):
    """Batch totals, used to prove the opening trial balance nets to zero."""

    as_of_date: date
    total_debit: Decimal
    total_credit: Decimal
    difference: Decimal
    balanced: bool
    locked: bool
    rows: list[OpeningBalanceOut]
