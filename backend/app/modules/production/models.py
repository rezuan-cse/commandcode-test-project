"""Production order models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ProductionOrder(Base):
    """A completed production run: components consumed, output produced."""

    __tablename__ = "production_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    production_date: Mapped[date] = mapped_column(Date, nullable=False)
    output_item_code: Mapped[str] = mapped_column(ForeignKey("items.code"), nullable=False)
    qty_produced: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    labor_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    overhead_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=Decimal("0"), nullable=False)
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    posted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    lines: Mapped[list["ProductionLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class ProductionLine(Base):
    """One component consumed by a production order."""

    __tablename__ = "production_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("production_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    component_code: Mapped[str] = mapped_column(ForeignKey("items.code"), nullable=False)
    qty_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    qty_consumed: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    line_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    order: Mapped[ProductionOrder] = relationship(back_populates="lines")
