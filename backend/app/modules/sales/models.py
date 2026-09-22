"""Sales order models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.mixins import ReversibleMixin


class SalesOrder(ReversibleMixin, Base):
    """A posted sale: inventory reduced, revenue and COGS recognised."""

    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    customer: Mapped[str] = mapped_column(String(160), nullable=False)
    is_credit: Mapped[bool] = mapped_column(default=True, nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    cogs: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    posted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    lines: Mapped[list["SalesLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class SalesLine(Base):
    """One item sold. The unit cost is snapshotted so historical COGS never drifts."""

    __tablename__ = "sales_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_code: Mapped[str] = mapped_column(ForeignKey("items.code"), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    line_revenue: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    line_cogs: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    order: Mapped[SalesOrder] = relationship(back_populates="lines")
