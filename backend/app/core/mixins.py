"""Model mixins shared across modules."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class ReversibleMixin:
    """Records that a posted transaction has been undone.

    Reversal rather than edit or delete. Once a transaction has posted it is in
    the books, and changing it afterwards would leave every later stock balance
    and average cost computed from something that is no longer true — which is
    precisely the discrepancy this system exists to remove.

    The original row is kept and marked, so the mistake and its correction both
    remain on the record.
    """

    reversed_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    reversed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reversal_reason: Mapped[str | None] = mapped_column(String(400), nullable=True)

    @declared_attr
    def reversal_journal_entry_id(cls) -> Mapped[int | None]:
        """The entry that reversed this one, so the pair can be followed."""
        return mapped_column(ForeignKey("journal_entries.id"), nullable=True)

    @property
    def is_reversed(self) -> bool:
        """True when this transaction has already been undone."""
        return self.reversed_at is not None
