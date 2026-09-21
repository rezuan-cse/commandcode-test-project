"""Journal entry and journal line models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_col
from app.core.enums import JournalSource, Segment


class JournalEntry(Base):
    """A balanced double-entry voucher."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    voucher_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    narration: Mapped[str | None] = mapped_column(String(400), nullable=True)
    source: Mapped[JournalSource] = mapped_column(
        enum_col(JournalSource), default=JournalSource.MANUAL, nullable=False
    )
    reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    posted_by: Mapped[str] = mapped_column(String(80), default="system", nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )


class JournalLine(Base):
    """One debit or credit line belonging to a journal entry."""

    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_code: Mapped[str] = mapped_column(
        ForeignKey("accounts.code"), nullable=False, index=True
    )
    segment: Mapped[Segment] = mapped_column(enum_col(Segment), nullable=False)
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0"), nullable=False)
    narration: Mapped[str | None] = mapped_column(String(400), nullable=True)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
