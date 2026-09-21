"""Opening balance models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_col
from app.core.enums import Segment


class OpeningBalance(Base):
    """One account's opening position as of the cutover date."""

    __tablename__ = "opening_balances"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account_code: Mapped[str] = mapped_column(
        ForeignKey("accounts.code"), nullable=False, index=True
    )
    segment: Mapped[Segment] = mapped_column(enum_col(Segment), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
