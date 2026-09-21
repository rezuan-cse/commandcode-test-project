"""Pydantic schemas for items and BOM."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.core.enums import ItemCategory, Segment


class ItemOut(BaseModel):
    """Item master row with derived stock figures."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    category: ItemCategory
    segment: Segment
    uom: str
    qty_on_hand: Decimal
    avg_cost: Decimal
    value_on_hand: Decimal


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
