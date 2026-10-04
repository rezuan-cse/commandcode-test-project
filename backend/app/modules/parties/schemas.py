"""Pydantic schemas for customer and supplier records."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PartyKind


class PartyOut(BaseModel):
    """A customer or supplier as the interface sees it."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    kind: PartyKind
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    vat_reg_no: str | None = None
    credit_days: int | None = None
    is_active: bool = True


class PartyIn(BaseModel):
    """Payload for adding a customer or supplier."""

    code: str = Field(min_length=1, max_length=24)
    name: str = Field(min_length=1, max_length=160)
    kind: PartyKind = PartyKind.CUSTOMER
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=240)
    # A business buyer's BIN, printed on the tax invoice. Leave blank for retail.
    vat_reg_no: str | None = Field(default=None, max_length=20)
    credit_days: int | None = Field(default=None, ge=0, le=365)
    is_active: bool = True


class PartyUpdate(BaseModel):
    """Payload for correcting a record.

    The code is deliberately absent: posted transactions point at it, so it is
    fixed once the record exists.
    """

    name: str | None = Field(default=None, min_length=1, max_length=160)
    kind: PartyKind | None = None
    contact_person: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=240)
    vat_reg_no: str | None = Field(default=None, max_length=20)
    credit_days: int | None = Field(default=None, ge=0, le=365)
    is_active: bool | None = None


class PartyImportResult(BaseModel):
    """What adopting the names already on posted transactions produced."""

    created: int
    already_known: int
    codes: list[str]
    linked: int
