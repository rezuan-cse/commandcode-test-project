"""Thin HTTP routes for users and roles.

Reading the permission matrix is open to any signed-in user, since it explains
what each role may do. Listing user accounts is restricted, because it exposes
every colleague's email address and role.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import Role
from app.modules.auth import repository as auth_repository
from app.modules.auth.dependencies import get_current_user
from app.modules.users_roles import service
from app.modules.users_roles.models import User
from app.modules.users_roles.schemas import RoleMatrixOut, UserOut

router = APIRouter(prefix="/access", tags=["users-roles"])

ANY_SIGNED_IN = Depends(get_current_user)
ADMIN_ONLY = Depends(service.require_admin())


@router.get("/matrix", response_model=RoleMatrixOut, dependencies=[ANY_SIGNED_IN])
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


@router.get("/roles", response_model=list[str], dependencies=[ANY_SIGNED_IN])
def list_roles() -> list[str]:
    """List the available roles."""
    return [role.value for role in Role]


@router.get("/users", response_model=list[UserOut], dependencies=[ADMIN_ONLY])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    """List user accounts. Admin only."""
    return auth_repository.list_users(db)
