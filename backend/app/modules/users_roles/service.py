"""Role/permission matrix enforcement.

Permissions are enforced here, on the server, so a restricted user gets a 403
even if they somehow reach a UI element. The demo exposes a role switcher that
sends the ``X-Demo-Role`` header, letting a reviewer prove the enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.enums import Role
from app.core.exceptions import PermissionDeniedError
from app.modules.auth.dependencies import get_current_user
from app.modules.users_roles.models import User, UserPermission


class Access(str, Enum):
    """Level of access a role has to a resource."""

    NONE = "none"
    VIEW = "view"
    FULL = "full"


RESOURCES = [
    "accounts",
    "journal_entries",
    "items_bom",
    "parties",
    "production",
    "sales_purchase",
    "payroll",
    "reports",
    "administration",
]

# How each resource is named to a person. The identifiers above are internal
# keys; a message saying the caller lacks access to "sales_purchase" means
# nothing to the person reading it.
RESOURCE_LABELS: dict[str, str] = {
    "accounts": "Chart of Accounts",
    "journal_entries": "Journal Entries",
    "items_bom": "Inventory & BOM",
    "parties": "Customers & Suppliers",
    "production": "Production Entry",
    "sales_purchase": "Purchase and Sales Entry",
    "payroll": "Payroll",
    "reports": "Reports",
    "administration": "Administration",
}


def resource_label(resource: str) -> str:
    """Return the human name for a resource key."""
    return RESOURCE_LABELS.get(resource, resource)


def denial_message(
    role: Role, resource: str, *, write: bool, level: Access | None = None
) -> str:
    """Explain a refusal in terms of what the role can and cannot do.

    A role that can view a screen but not change it gets a different message
    from one that cannot see it at all, because the remedy is different: the
    first should be shown a read-only screen, the second should not be offered
    the screen at all.

    ``level`` is the level the person actually has, which a per-user grant may
    have changed from the role's default.
    """
    label = resource_label(resource)
    if level is None:
        level = access_for(role, resource)

    if level == Access.NONE:
        return (
            f"The {label} screen is not available to the {role.value} role. "
            f"An administrator can grant access if it is needed."
        )
    if write and level == Access.VIEW:
        return (
            f"The {role.value} role can view the {label} screen but cannot make "
            f"changes on it."
        )
    return f"The {role.value} role does not have access to {label}."

# Transcribed directly from the build spec, section 4.
MATRIX: dict[Role, dict[str, Access]] = {
    Role.ADMIN: {r: Access.FULL for r in RESOURCES},
    Role.ACCOUNTANT: {
        "accounts": Access.VIEW,
        "journal_entries": Access.FULL,
        "items_bom": Access.VIEW,
        "parties": Access.FULL,
        "production": Access.VIEW,
        "sales_purchase": Access.VIEW,
        "payroll": Access.FULL,
        "reports": Access.FULL,
        "administration": Access.NONE,
    },
    Role.STORE_PRODUCTION: {
        "accounts": Access.NONE,
        "journal_entries": Access.NONE,
        "items_bom": Access.FULL,
        "parties": Access.FULL,
        "production": Access.FULL,
        "sales_purchase": Access.NONE,
        "payroll": Access.NONE,
        "reports": Access.NONE,
        "administration": Access.NONE,
    },
    Role.SALES_STAFF: {
        "accounts": Access.NONE,
        "journal_entries": Access.NONE,
        "items_bom": Access.VIEW,
        "parties": Access.FULL,
        "production": Access.NONE,
        "sales_purchase": Access.FULL,
        "payroll": Access.NONE,
        "reports": Access.NONE,
        "administration": Access.NONE,
    },
    Role.OWNER_VIEWER: {
        "accounts": Access.VIEW,
        "journal_entries": Access.VIEW,
        "items_bom": Access.VIEW,
        "parties": Access.VIEW,
        "production": Access.VIEW,
        "sales_purchase": Access.VIEW,
        "payroll": Access.VIEW,
        "reports": Access.FULL,
        "administration": Access.VIEW,
    },
}

# Endpoints that carry no role restriction in the demo.
READ_ONLY_METHODS = {"GET", "HEAD", "OPTIONS"}


def access_for(role: Role, resource: str) -> Access:
    """Return a role's access level for a resource."""
    return MATRIX.get(role, {}).get(resource, Access.NONE)


def is_allowed(role: Role, resource: str, *, write: bool) -> bool:
    """True when the role may read (or write) the resource."""
    level = access_for(role, resource)
    if write:
        return level == Access.FULL
    return level in {Access.VIEW, Access.FULL}


def permissions_for(role: Role) -> dict[str, str]:
    """The role's access level for every resource, for the interface to read.

    The client uses this to hide menus and disable forms. It is not a security
    boundary — the server still checks every request — but it stops the interface
    offering actions that are going to be refused.
    """
    return {resource: access_for(role, resource).value for resource in RESOURCES}


# --- Per-user grants ------------------------------------------------------
#
# The matrix above is the default for a role. An administrator may grant or deny
# an individual more or less than that; everything below layers the exception on
# top, so the effective level is what the server enforces and what the interface
# is told.


def overrides_for(db: Session, user: User) -> dict[str, Access]:
    """The access levels recorded against this person, if any."""
    rows = (
        db.execute(select(UserPermission).where(UserPermission.user_id == user.id))
        .scalars()
        .all()
    )
    result: dict[str, Access] = {}
    for row in rows:
        try:
            result[row.resource] = Access(row.access)
        except ValueError:
            continue  # an unknown level is treated as "no exception"
    return result


def access_for_user(db: Session, user: User, resource: str) -> Access:
    """The level this person actually has: their own grant, else their role's."""
    override = overrides_for(db, user).get(resource)
    return override if override is not None else access_for(user.role, resource)


def permissions_for_user(db: Session, user: User) -> dict[str, str]:
    """Every resource's effective level for this person, for the interface."""
    overrides = overrides_for(db, user)
    return {
        resource: overrides.get(resource, access_for(user.role, resource)).value
        for resource in RESOURCES
    }


def is_allowed_user(db: Session, user: User, resource: str, *, write: bool) -> bool:
    """True when this person may read (or change) the resource."""
    level = access_for_user(db, user, resource)
    if write:
        return level == Access.FULL
    return level in {Access.VIEW, Access.FULL}


def set_overrides(db: Session, user: User, desired: dict[str, Access]) -> None:
    """Replace this person's exceptions with ``desired``.

    A resource set back to what the role already gives has its row removed, so
    "no row" keeps meaning "follow the role" and a later change to the matrix
    reaches the person again.
    """
    rows = {
        row.resource: row
        for row in db.execute(
            select(UserPermission).where(UserPermission.user_id == user.id)
        )
        .scalars()
        .all()
    }
    for resource, level in desired.items():
        if resource not in RESOURCES:
            continue
        row = rows.pop(resource, None)
        if level == access_for(user.role, resource):
            if row is not None:
                db.delete(row)
            continue
        if row is None:
            db.add(
                UserPermission(user_id=user.id, resource=resource, access=level.value)
            )
        else:
            row.access = level.value
    for row in rows.values():
        db.delete(row)
    db.flush()


def to_user_out(db: Session, user: User):
    """Serialise a user with the access that actually applies to them."""
    from app.modules.users_roles.schemas import UserOut

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_2fa_enabled=user.is_2fa_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        permissions=permissions_for_user(db, user),
    )


@dataclass
class Principal:
    """The acting user for a request."""

    user: User
    source: str = "token"

    @property
    def role(self) -> Role:
        """The role the permission matrix is evaluated against."""
        return self.user.role

    @property
    def is_admin(self) -> bool:
        """True for the Admin role."""
        return self.role == Role.ADMIN


def require(resource: str, *, write: bool) -> "RequirePermission":
    """Build a FastAPI dependency enforcing access to ``resource``."""
    return RequirePermission(resource=resource, write=write)


class RequirePermission:
    """Callable dependency that raises 403 when the acting role lacks access.

    The role comes from the signed token, never from the request body or a
    caller-supplied header, so the matrix cannot be side-stepped by the client.
    """

    def __init__(self, *, resource: str, write: bool) -> None:
        self.resource = resource
        self.write = write

    def __call__(
        self,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> Principal:
        """Check what this person may do, and return the principal.

        The role in the signed token is the starting point; any grant recorded
        against the person is applied on top of it.
        """
        level = access_for_user(db, user, self.resource)
        allowed = level == Access.FULL if self.write else level in {Access.VIEW, Access.FULL}
        if not allowed:
            raise PermissionDeniedError(
                denial_message(user.role, self.resource, write=self.write, level=level)
            )
        return Principal(user=user)


class RequireAdmin:
    """Callable dependency that allows only the Admin role.

    Configuration and user management live outside the resource matrix, so they
    are gated on the role itself rather than on a resource.
    """

    def __call__(self, user: User = Depends(get_current_user)) -> Principal:
        """Reject every role except Admin."""
        if user.role != Role.ADMIN:
            raise PermissionDeniedError(
                f"This action is limited to administrators. You are signed in as "
                f"{user.role.value}."
            )
        return Principal(user=user)


def require_admin() -> RequireAdmin:
    """Build the Admin-only dependency."""
    return RequireAdmin()
