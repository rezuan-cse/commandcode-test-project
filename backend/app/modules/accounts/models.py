"""Chart of Accounts models."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, enum_col
from app.core.enums import AccountType, NormalBalance, Segment


class Account(Base):
    """A single chart-of-accounts entry, tagged with its reporting segment."""

    __tablename__ = "accounts"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    name_bn: Mapped[str | None] = mapped_column(String(200), nullable=True)
    account_type: Mapped[AccountType] = mapped_column(
        enum_col(AccountType), nullable=False
    )
    segment: Mapped[Segment] = mapped_column(enum_col(Segment), nullable=False)
    normal_balance: Mapped[NormalBalance] = mapped_column(
        enum_col(NormalBalance), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
