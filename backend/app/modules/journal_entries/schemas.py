"""Pydantic schemas for journal entries."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.enums import JournalSource, Segment


class JournalLineIn(BaseModel):
    """A single debit or credit line supplied by the caller."""

    account_code: str
    segment: Segment
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    narration: str | None = None

    @model_validator(mode="after")
    def exactly_one_side(self) -> "JournalLineIn":
        """A line must be a debit or a credit, never both, never neither."""
        has_debit = self.debit and self.debit > 0
        has_credit = self.credit and self.credit > 0
        if has_debit and has_credit:
            raise ValueError("A line cannot have both debit and credit")
        if not has_debit and not has_credit:
            raise ValueError("A line must have either a debit or a credit")
        return self


class JournalEntryCreate(BaseModel):
    """Payload for posting a manual journal entry."""

    voucher_no: str = Field(min_length=1, max_length=32)
    entry_date: date
    narration: str | None = None
    reference: str | None = None
    posted_by: str = "manual"
    lines: list[JournalLineIn] = Field(min_length=2)


class JournalLineOut(BaseModel):
    """A journal line as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    account_code: str
    segment: Segment
    debit: Decimal
    credit: Decimal
    narration: str | None


class JournalEntryOut(BaseModel):
    """A journal entry with its lines."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    voucher_no: str
    entry_date: date
    narration: str | None
    source: JournalSource
    reference: str | None
    posted_by: str
    posted_at: datetime
    lines: list[JournalLineOut]
