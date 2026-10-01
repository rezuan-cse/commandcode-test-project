"""Customer and supplier records.

One list rather than two. A trading partner is often both — the same firm that
supplies raw material may also buy finished goods — and a single list is what
makes "what does this customer owe us?" answerable without guessing at the
spelling of a name that was typed on a transaction.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_col
from app.core.enums import PartyKind


class Party(Base):
    """A customer, a supplier, or both."""

    __tablename__ = "parties"

    # The code is the key posted transactions point at, so it is fixed once the
    # record exists. Names change; a code that history already refers to should
    # not.
    code: Mapped[str] = mapped_column(String(24), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[PartyKind] = mapped_column(enum_col(PartyKind), nullable=False)

    contact_person: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    address: Mapped[str | None] = mapped_column(String(240), nullable=True)

    # Days of credit allowed; 0 means payment on delivery. Nullable on purpose:
    # a record adopted from an old transaction carries no agreed terms, and
    # claiming a default nobody agreed to would be worse than saying nothing.
    credit_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # The server default matters for schema upgrades: an existing table can only
    # gain a NOT NULL column if the database knows what to put in existing rows.
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
