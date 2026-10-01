"""Thin HTTP routes for users, roles, and account administration.

Reading the permission matrix is open to any signed-in user, since it explains
what each role may do. Everything that touches another person's account is
restricted to administrators and recorded in the audit log.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import Role
from app.modules.auth import repository as auth_repository
from app.modules.auth.dependencies import get_current_user
from app.modules.users_roles import administration, service
from app.modules.users_roles.models import User
from app.modules.users_roles.schemas import (
    AdminActionOut,
    AuditEntryOut,
    PasswordIssuedOut,
    PermissionsUpdate,
    ResetPasswordRequest,
    RoleMatrixOut,
    SetActiveRequest,
    UserCreate,
    UserCreatedOut,
    UserOut,
    UserPermissionsOut,
    UserUpdate,
)

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
def list_users(db: Session = Depends(get_db)) -> list[UserOut]:
    """List user accounts, with the access each one actually has. Admin only."""
    return [
        service.to_user_out(db, user) for user in auth_repository.list_users(db)
    ]


@router.post("/users", response_model=UserCreatedOut, status_code=201, dependencies=[ADMIN_ONLY])
def create_user(
    payload: UserCreate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserCreatedOut:
    """Add an account. Admin only.

    A generated password is returned once, so it can be handed over. One supplied
    by the administrator is not echoed back.
    """
    user, password = administration.create_user(db, actor, payload)
    return UserCreatedOut(
        user=service.to_user_out(db, user),
        password=password,
        message=(
            f"{user.full_name} can now sign in."
            if password is None
            else "Give this password to the user. It is shown once and is not "
            "stored anywhere in readable form."
        ),
    )


@router.patch("/users/{user_id}", response_model=UserOut, dependencies=[ADMIN_ONLY])
def update_user(
    user_id: int,
    payload: UserUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """Change an account's name, email or role. Admin only."""
    user = administration.update_user(db, actor, user_id, payload)
    return service.to_user_out(db, user)


@router.delete("/users/{user_id}", response_model=AdminActionOut, dependencies=[ADMIN_ONLY])
def delete_user(
    user_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminActionOut:
    """Remove an account. Admin only."""
    return AdminActionOut(message=administration.delete_user(db, actor, user_id))


@router.get(
    "/users/{user_id}/permissions",
    response_model=UserPermissionsOut,
    dependencies=[ADMIN_ONLY],
)
def get_user_permissions(
    user_id: int, db: Session = Depends(get_db)
) -> UserPermissionsOut:
    """One person's access: their role's default, their grants, and the result."""
    return UserPermissionsOut(**administration.user_permissions(db, user_id))


@router.put(
    "/users/{user_id}/permissions",
    response_model=AdminActionOut,
    dependencies=[ADMIN_ONLY],
)
def set_user_permissions(
    user_id: int,
    payload: PermissionsUpdate,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminActionOut:
    """Grant or deny one person areas, on top of their role. Admin only."""
    administration.set_user_permissions(db, actor, user_id, payload)
    return AdminActionOut(message="Access updated.")


@router.post(
    "/users/{user_id}/reset-two-factor",
    response_model=AdminActionOut,
    dependencies=[ADMIN_ONLY],
)
def reset_two_factor(
    user_id: int,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminActionOut:
    """Clear a user's second factor so they can sign in with a password again."""
    return AdminActionOut(
        message=administration.reset_two_factor(db, actor, user_id)
    )


@router.post(
    "/users/{user_id}/reset-password",
    response_model=PasswordIssuedOut,
    dependencies=[ADMIN_ONLY],
)
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest | None = None,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PasswordIssuedOut:
    """Issue a new password. It is returned once, to be passed to the user.

    The body is optional: with nothing supplied a password is generated, which is
    the common case and should not require posting an empty object.
    """
    password = administration.reset_password(
        db, actor, user_id, payload.new_password if payload else None
    )
    return PasswordIssuedOut(
        password=password,
        message=(
            "Give this password to the user. It is shown once and is not stored "
            "anywhere in readable form."
        ),
    )


@router.post(
    "/users/{user_id}/active",
    response_model=AdminActionOut,
    dependencies=[ADMIN_ONLY],
)
def set_active(
    user_id: int,
    payload: SetActiveRequest,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AdminActionOut:
    """Enable or disable an account."""
    return AdminActionOut(
        message=administration.set_active(db, actor, user_id, payload.is_active)
    )


@router.get(
    "/audit", response_model=list[AuditEntryOut], dependencies=[ADMIN_ONLY]
)
def list_audit(db: Session = Depends(get_db)) -> list[AuditEntryOut]:
    """Recent administrative actions, newest first."""
    return administration.recent_actions(db)
