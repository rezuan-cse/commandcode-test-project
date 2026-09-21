"""Pydantic schemas for users and roles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.core.enums import Role


class UserOut(BaseModel):
    """A demo user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool


class RoleAccessRow(BaseModel):
    """One role's access levels across all resources."""

    role: str
    access: dict[str, str]


class RoleMatrixOut(BaseModel):
    """The full role/permission matrix."""

    resources: list[str]
    roles: list[RoleAccessRow]
