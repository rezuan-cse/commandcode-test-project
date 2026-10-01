"""Pydantic schemas for items and BOM."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ItemCategory, Segment


class ItemOut(BaseModel):
    """Item master row with derived stock figures."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    category: ItemCategory
    segment: Segment
    uom: str
    reorder_level: Decimal | None = None
    is_active: bool
    qty_on_hand: Decimal
    avg_cost: Decimal
    value_on_hand: Decimal


class ItemIn(BaseModel):
    """Payload for adding an item to the master."""

    code: str = Field(min_length=1, max_length=24)
    name: str = Field(min_length=1, max_length=160)
    category: ItemCategory
    segment: Segment
    uom: str = Field(min_length=1, max_length=16)
    reorder_level: Decimal | None = Field(default=None, ge=0)
    is_active: bool = True


class ItemUpdate(BaseModel):
    """Payload for changing an item.

    The code is deliberately absent: it is the key every other record points at,
    so it is fixed once the item exists. Everything else can be corrected.
    """

    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: ItemCategory | None = None
    segment: Segment | None = None
    uom: str | None = Field(default=None, min_length=1, max_length=16)
    reorder_level: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class BomComponentOut(BaseModel):
    """One BOM edge."""

    model_config = ConfigDict(from_attributes=True)

    parent_code: str
    component_code: str
    component_name: str
    qty_per_unit: Decimal
    stage: int
    uom: str


class BomExplosionLine(BaseModel):
    """A flattened material requirement for a target production quantity."""

    item_code: str
    item_name: str
    category: ItemCategory
    uom: str
    qty_per_unit: Decimal
    qty_required: Decimal
    avg_cost: Decimal
    est_cost: Decimal
    level: int


class BomExplosionOut(BaseModel):
    """The full exploded requirement for producing ``qty`` of ``parent_code``."""

    parent_code: str
    parent_name: str
    qty: Decimal
    lines: list[BomExplosionLine]
    total_estimated_cost: Decimal
