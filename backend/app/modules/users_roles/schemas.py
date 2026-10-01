"""Pydantic schemas for users and roles."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from app.core.clock import LocalDateTime
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
    last_login_at: LocalDateTime | None = None
    created_at: LocalDateTime | None = None
    updated_at: LocalDateTime | None = None
    # Access level per resource, so the interface can hide what this person may
    # not use. Always the effective level: the role's, plus any grant an
    # administrator has recorded against them.
    permissions: dict[str, str] = {}


class UserCreate(BaseModel):
    """Add an account. Leave the password out to have one generated."""

    email: str = Field(min_length=3, max_length=160)
    full_name: str = Field(min_length=1, max_length=160)
    role: Role
    password: str | None = Field(default=None, min_length=8, max_length=200)


class UserUpdate(BaseModel):
    """Change an account. Only the fields given are altered."""

    email: str | None = Field(default=None, min_length=3, max_length=160)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: Role | None = None


class UserCreatedOut(BaseModel):
    """The new account, plus its password when one was generated."""

    user: UserOut
    password: str | None = None
    message: str


class UserPermissionsOut(BaseModel):
    """What one person may do: the role's default and their own exceptions."""

    user_id: int
    role: Role
    resources: list[str]
    role_defaults: dict[str, str]
    overrides: dict[str, str]
    effective: dict[str, str]


class PermissionsUpdate(BaseModel):
    """Set a person's access. Anything not listed is reset to their role default."""

    access: dict[str, str]


class RoleAccessRow(BaseModel):
    """One role's access levels across all resources."""

    role: str
    access: dict[str, str]


class RoleMatrixOut(BaseModel):
    """The full role/permission matrix."""

    resources: list[str]
    roles: list[RoleAccessRow]


class ResetPasswordRequest(BaseModel):
    """Issue a new password. Leave it out to have one generated."""

    new_password: str | None = Field(default=None, min_length=8, max_length=200)


class PasswordIssuedOut(BaseModel):
    """A generated password, shown once so the administrator can pass it on."""

    password: str
    message: str


class SetActiveRequest(BaseModel):
    """Enable or disable an account."""

    is_active: bool


class AdminActionOut(BaseModel):
    """The result of an administrative action."""

    message: str


class AuditEntryOut(BaseModel):
    """One recorded administrative action."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_email: str
    action: str
    target_email: str
    detail: str | None
    created_at: LocalDateTime
