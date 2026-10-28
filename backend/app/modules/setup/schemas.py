"""Pydantic schemas for first-run setup."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.auth.schemas import SessionResponse
from app.modules.users_roles.schemas import UserOut

__all__ = [
    "SetupAdminRequest",
    "SetupChecklist",
    "SetupChecklistItem",
    "SetupResult",
    "SetupState",
    "UserOut",
]


class SetupState(BaseModel):
    """Whether the system still needs its first administrator."""

    needs_setup: bool
    # Named so the setup screen can say which company it is setting up. A brand-new
    # deployment already has the company name from the configuration defaults.
    company_name: str


class SetupAdminRequest(BaseModel):
    """The first administrator's details."""

    full_name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=8, max_length=200)


class SetupResult(SessionResponse):
    """A session for the account that was just created.

    Subclassing the normal session response means the interface signs the person in
    straight away instead of bouncing them back to a login form they just filled in.
    """

    message: str


class SetupChecklistItem(BaseModel):
    """One step on the way from an empty system to a first sale."""

    key: str
    label: str
    detail: str
    # Where to go to do it, as a route the interface already serves.
    link: str
    done: bool


class SetupChecklist(BaseModel):
    """The setup steps, and whether the system is ready to trade."""

    items: list[SetupChecklistItem]
    complete: bool
