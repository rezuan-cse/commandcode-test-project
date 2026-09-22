"""Pydantic schemas for users and roles."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict

from app.core.enums import Role


class UserOut(BaseModel):
    """A user as returned by the API.

    Carries no credential material: the password hash and the TOTP secret are
    deliberately absent, so they cannot leak through any endpoint that returns
    a user.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    is_2fa_enabled: bool = False
    last_login_at: dt.datetime | None = None
    # Access level per resource, so the interface can hide what the role cannot
    # use. Empty for a list of other users, populated for the signed-in one.
    permissions: dict[str, str] = {}


class RoleAccessRow(BaseModel):
    """One role's access levels across all resources."""

    role: str
    access: dict[str, str]


class RoleMatrixOut(BaseModel):
    """The full role/permission matrix."""

    resources: list[str]
    roles: list[RoleAccessRow]
