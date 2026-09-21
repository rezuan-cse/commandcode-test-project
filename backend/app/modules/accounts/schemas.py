"""Pydantic schemas for the Chart of Accounts module."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AccountType, NormalBalance, Segment


class AccountBase(BaseModel):
    """Fields shared by create and read schemas."""

    code: str = Field(min_length=1, max_length=16)
    name_en: str = Field(min_length=1, max_length=160)
    name_bn: str | None = None
    account_type: AccountType
    segment: Segment
    normal_balance: NormalBalance


class AccountCreate(AccountBase):
    """Payload for creating an account."""


class AccountUpdate(BaseModel):
    """Payload for partially updating an account."""

    name_en: str | None = None
    name_bn: str | None = None
    account_type: AccountType | None = None
    segment: Segment | None = None
    normal_balance: NormalBalance | None = None
    is_active: bool | None = None


class AccountOut(AccountBase):
    """Account as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    is_active: bool
