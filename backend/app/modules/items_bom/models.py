"""Item master and BOM models."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_col
from app.core.enums import ItemCategory, Segment


class Item(Base):
    """A stock item. Quantity and average cost are derived from the ledger."""

    __tablename__ = "items"

    code: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[ItemCategory] = mapped_column(
        enum_col(ItemCategory), nullable=False
    )
    segment: Mapped[Segment] = mapped_column(enum_col(Segment), nullable=False)
    uom: Mapped[str] = mapped_column(String(16), nullable=False)
    # The quantity at which the item wants reordering. Nullable on purpose: most
    # items will not have one, and a made-up default would put every item on the
    # low-stock list on the day the field was introduced. Blank means "not watched",
    # which is a different statement from "reorder at zero".
    reorder_level: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class BomComponent(Base):
    """One parent -> component relationship with a per-unit quantity."""

    __tablename__ = "bom_components"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_code: Mapped[str] = mapped_column(
        ForeignKey("items.code"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(
        ForeignKey("items.code"), nullable=False, index=True
    )
    qty_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    stage: Mapped[int] = mapped_column(default=1, nullable=False)
