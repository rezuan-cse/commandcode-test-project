"""Pydantic schemas for sales entry."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.production.schemas import JournalLinePreview


class SaleLineIn(BaseModel):
    """One item being sold."""

    item_code: str
    qty: Decimal = Field(gt=0)
    sale_price: Decimal = Field(ge=0)


class SaleRequest(BaseModel):
    """Payload for previewing or posting a sale."""

    customer: str = Field(min_length=1)
    sale_date: date
    is_credit: bool = True
    lines: list[SaleLineIn] = Field(min_length=1)
    posted_by: str = "sales"
    simulate_failure: bool = False


class SaleLinePreview(BaseModel):
    """A priced sale line with its cost and margin."""

    item_code: str
    item_name: str
    qty: Decimal
    sale_price: Decimal
    unit_cost: Decimal
    line_revenue: Decimal
    line_cogs: Decimal
    line_margin: Decimal
    on_hand: Decimal
    sufficient: bool


class SalePreview(BaseModel):
    """The revenue/COGS build-up and journal preview for a sale."""

    customer: str
    lines: list[SaleLinePreview]
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    journal_lines: list[JournalLinePreview]
    balanced: bool
    can_post: bool
    warnings: list[str]


class SaleOut(BaseModel):
    """A posted sale."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    sale_date: date
    customer: str
    revenue: Decimal
    cogs: Decimal
    journal_entry_id: int | None
    posted_by: str


class SalePostResult(BaseModel):
    """Result of posting a sale."""

    order: SaleOut
    preview: SalePreview
    message: str
