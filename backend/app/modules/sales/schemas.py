"""Pydantic schemas for sales entry."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.clock import LocalDateTime
from app.core.schemas import ReversalOut
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
    # The customer as a record. When given, the name recorded is the party's own,
    # so the displayed name and the identity behind it cannot drift apart.
    party_code: str | None = None
    lines: list[SaleLineIn] = Field(min_length=1)
    simulate_failure: bool = False


class SaleLinePreview(BaseModel):
    """A priced sale line with its cost and margin."""

    item_code: str
    item_name: str
    qty: Decimal
    sale_price: Decimal
    unit_cost: Decimal
    line_revenue: Decimal
    vat_amount: Decimal = Decimal("0")
    line_cogs: Decimal
    line_margin: Decimal
    on_hand: Decimal
    sufficient: bool
    below_cost: bool


class SalePreview(BaseModel):
    """The revenue/COGS build-up and journal preview for a sale."""

    customer: str
    lines: list[SaleLinePreview]
    revenue: Decimal
    vat_total: Decimal = Decimal("0")
    grand_total: Decimal = Decimal("0")
    cogs: Decimal
    gross_profit: Decimal
    gross_margin_pct: Decimal
    journal_lines: list[JournalLinePreview]
    balanced: bool
    can_post: bool
    warnings: list[str]


class SaleOut(ReversalOut):
    """A posted sale."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    sale_date: date
    customer: str
    revenue: Decimal
    vat_total: Decimal = Decimal("0")
    cogs: Decimal
    journal_entry_id: int | None
    posted_by: str
    posted_at: LocalDateTime | None = None


class SaleLineOut(BaseModel):
    """One line of a posted sale, for documents that itemise it."""

    model_config = ConfigDict(from_attributes=True)

    item_code: str
    qty: Decimal
    sale_price: Decimal
    line_revenue: Decimal
    vat_amount: Decimal = Decimal("0")


class SaleDetailOut(SaleOut):
    """A posted sale with its lines, for the receipt."""

    lines: list[SaleLineOut]


class SalePostResult(BaseModel):
    """Result of posting a sale."""

    order: SaleOut
    preview: SalePreview
    message: str
