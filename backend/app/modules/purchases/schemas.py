"""Pydantic schemas for purchase entry."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.production.schemas import JournalLinePreview


class PurchaseLineIn(BaseModel):
    """One item being received."""

    item_code: str
    qty: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseRequest(BaseModel):
    """Payload for previewing or posting a purchase."""

    supplier: str = Field(min_length=1)
    purchase_date: date
    is_credit: bool = True
    lines: list[PurchaseLineIn] = Field(min_length=1)
    posted_by: str = "store"
    simulate_failure: bool = False


class PurchaseLinePreview(BaseModel):
    """A received line with its value and resulting average cost."""

    item_code: str
    item_name: str
    qty: Decimal
    unit_cost: Decimal
    line_value: Decimal
    on_hand_before: Decimal
    avg_cost_before: Decimal
    avg_cost_after: Decimal


class PurchasePreview(BaseModel):
    """The value build-up and journal preview for a purchase."""

    supplier: str
    lines: list[PurchaseLinePreview]
    total_value: Decimal
    journal_lines: list[JournalLinePreview]
    balanced: bool
    can_post: bool
    warnings: list[str]


class PurchaseOut(BaseModel):
    """A posted purchase."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    purchase_date: date
    supplier: str
    total_value: Decimal
    journal_entry_id: int | None
    posted_by: str


class PurchasePostResult(BaseModel):
    """Result of posting a purchase."""

    order: PurchaseOut
    preview: PurchasePreview
    message: str
