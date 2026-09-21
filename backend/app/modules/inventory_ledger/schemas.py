"""Pydantic schemas for the inventory ledger."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.enums import MovementType


class InventoryRowOut(BaseModel):
    """One ledger row as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_date: date
    item_code: str
    movement_type: MovementType
    reference: str | None
    in_qty: Decimal
    in_value: Decimal
    out_qty: Decimal
    out_value: Decimal
    balance_qty: Decimal
    balance_value: Decimal
    avg_cost: Decimal


class ItemPositionOut(BaseModel):
    """An item's current stock position, derived from the ledger."""

    item_code: str
    qty: Decimal
    value: Decimal
    avg_cost: Decimal


class ValuationRowOut(BaseModel):
    """One line of the inventory valuation report."""

    item_code: str
    item_name: str
    uom: str
    qty: Decimal
    avg_cost: Decimal
    value: Decimal


class ValuationOut(BaseModel):
    """Inventory valuation report with a grand total."""

    as_of: date | None
    rows: list[ValuationRowOut]
    total_value: Decimal
