"""Configurable settings store.

Anything the client has not yet confirmed (VAT rates, payroll structure) lives
here rather than in code, per the build spec's hard requirement that
configuration is never hardcoded.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Setting(Base):
    """A single configuration key with a JSON-encoded value."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(String(400), nullable=True)
    confirmed_by_client: Mapped[bool] = mapped_column(default=False, nullable=False)
