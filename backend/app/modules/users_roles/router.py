"""Thin HTTP routes for users and roles."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import Role
from app.modules.users_roles import service
from app.modules.users_roles.models import User
from app.modules.users_roles.schemas import RoleMatrixOut, UserOut

router = APIRouter(prefix="/access", tags=["users-roles"])


@router.get("/matrix", response_model=RoleMatrixOut)
def get_matrix() -> RoleMatrixOut:
    """Return the full role/permission matrix for display."""
    return RoleMatrixOut(
        resources=service.RESOURCES,
        roles=[
            {
                "role": role.value,
                "access": {
                    resource: service.access_for(role, resource).value
                    for resource in service.RESOURCES
                },
            }
            for role in Role
        ],
    )


@router.get("/roles", response_model=list[str])
def list_roles() -> list[str]:
    """List the available roles."""
    return [role.value for role in Role]


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """List demo users."""
    return list(db.query(User).order_by(User.id).all())
