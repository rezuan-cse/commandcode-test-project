"""Pydantic schemas for production entry."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SuggestedComponent(BaseModel):
    """A BOM-suggested component for a production run."""

    component_code: str
    component_name: str
    uom: str
    qty_per_unit: Decimal
    qty_consumed: Decimal
    unit_cost: Decimal
    line_cost: Decimal
    on_hand: Decimal
    sufficient: bool


class ProductionLineIn(BaseModel):
    """A component the user has confirmed for consumption."""

    component_code: str
    qty_consumed: Decimal = Field(gt=0)


class ProductionRequest(BaseModel):
    """Payload for previewing or posting a production run."""

    output_item_code: str
    qty_produced: Decimal = Field(gt=0)
    production_date: date
    labor_cost: Decimal = Decimal("0")
    overhead_cost: Decimal = Decimal("0")
    posted_by: str = "store"
    lines: list[ProductionLineIn] | None = None
    simulate_failure: bool = False


class JournalLinePreview(BaseModel):
    """A journal line the posting will create, shown before committing."""

    account_code: str
    account_name: str
    segment: str
    debit: Decimal
    credit: Decimal
    narration: str | None = None


class ProductionPreview(BaseModel):
    """The full cost build-up and journal preview for a production run."""

    output_item_code: str
    output_item_name: str
    qty_produced: Decimal
    components: list[SuggestedComponent]
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    journal_lines: list[JournalLinePreview]
    balanced: bool
    can_post: bool
    warnings: list[str]


class ProductionRunOut(BaseModel):
    """A posted production order."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    production_date: date
    output_item_code: str
    qty_produced: Decimal
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    journal_entry_id: int | None
    posted_by: str


class ProductionPostResult(BaseModel):
    """Result of posting a production run."""

    order: ProductionRunOut
    preview: ProductionPreview
    message: str
