"""Purchase order models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.core.mixins import ReversibleMixin


class PurchaseOrder(ReversibleMixin, Base):
    """A posted purchase: inventory increased at cost, payable or cash credited."""

    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier: Mapped[str] = mapped_column(String(160), nullable=False)
    is_credit: Mapped[bool] = mapped_column(default=True, nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id"), nullable=True
    )
    posted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    lines: Mapped[list["PurchaseLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", lazy="selectin"
    )


class PurchaseLine(Base):
    """One item received."""

    __tablename__ = "purchase_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_code: Mapped[str] = mapped_column(ForeignKey("items.code"), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    line_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)

    order: Mapped[PurchaseOrder] = relationship(back_populates="lines")
