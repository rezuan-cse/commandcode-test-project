"""Schemas shared across modules."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class ReversalRequest(BaseModel):
    """Why a posted transaction is being undone.

    The reason is required. Reversing a transaction changes the accounts and the
    stock, and the person reading the record months later needs to know why it
    was done — "reversed" on its own is not an explanation.
    """

    reason: str = Field(min_length=3, max_length=400)
    posted_by: str = Field(default="system", max_length=80)
    # Defaults to the transaction's own date, which keeps the original and its
    # reversal together in the same reporting period.
    reversal_date: date | None = None


class ReversalOut(BaseModel):
    """The reversal state every posted transaction carries."""

    is_reversed: bool = False
    reversed_by: str | None = None
    reversal_reason: str | None = None
