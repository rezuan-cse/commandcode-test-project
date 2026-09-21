"""Inventory ledger model. Append-only: rows are never edited or deleted."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_col
from app.core.enums import MovementType


class InventoryLedgerRow(Base):
    """One inventory movement with its running balance and average cost."""

    __tablename__ = "inventory_ledger"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    item_code: Mapped[str] = mapped_column(
        ForeignKey("items.code"), nullable=False, index=True
    )
    movement_type: Mapped[MovementType] = mapped_column(
        enum_col(MovementType), nullable=False
    )
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    in_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    in_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    out_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    out_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    balance_qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    balance_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    avg_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal("0"), nullable=False)
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
