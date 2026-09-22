"""Role/permission matrix enforcement.

Permissions are enforced here, on the server, so a restricted user gets a 403
even if they somehow reach a UI element. The demo exposes a role switcher that
sends the ``X-Demo-Role`` header, letting a reviewer prove the enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import Depends

from app.core.enums import Role
from app.core.exceptions import PermissionDeniedError
from app.modules.auth.dependencies import get_current_user
from app.modules.users_roles.models import User


class Access(str, Enum):
    """Level of access a role has to a resource."""

    NONE = "none"
    VIEW = "view"
    FULL = "full"


RESOURCES = [
    "accounts",
    "journal_entries",
    "items_bom",
    "production",
    "sales_purchase",
    "reports",
]

# How each resource is named to a person. The identifiers above are internal
# keys; a message saying the caller lacks access to "sales_purchase" means
# nothing to the person reading it.
RESOURCE_LABELS: dict[str, str] = {
    "accounts": "Chart of Accounts",
    "journal_entries": "Journal Entries",
    "items_bom": "Inventory & BOM",
    "production": "Production Entry",
    "sales_purchase": "Purchase and Sales Entry",
    "reports": "Reports",
}


def resource_label(resource: str) -> str:
    """Return the human name for a resource key."""
    return RESOURCE_LABELS.get(resource, resource)


def denial_message(role: Role, resource: str, *, write: bool) -> str:
    """Explain a refusal in terms of what the role can and cannot do.

    A role that can view a screen but not change it gets a different message
    from one that cannot see it at all, because the remedy is different: the
    first should be shown a read-only screen, the second should not be offered
    the screen at all.
    """
    label = resource_label(resource)
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
        "production": Access.VIEW,
        "sales_purchase": Access.VIEW,
        "reports": Access.FULL,
    },
    Role.STORE_PRODUCTION: {
        "accounts": Access.NONE,
        "journal_entries": Access.NONE,
        "items_bom": Access.FULL,
        "production": Access.FULL,
        "sales_purchase": Access.NONE,
        "reports": Access.VIEW,
    },
    Role.SALES_STAFF: {
        "accounts": Access.NONE,
        "journal_entries": Access.NONE,
        "items_bom": Access.VIEW,
        "production": Access.NONE,
        "sales_purchase": Access.FULL,
        "reports": Access.VIEW,
    },
    Role.OWNER_VIEWER: {
        "accounts": Access.VIEW,
        "journal_entries": Access.VIEW,
        "items_bom": Access.VIEW,
        "production": Access.VIEW,
        "sales_purchase": Access.VIEW,
        "reports": Access.FULL,
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

    def __call__(self, user: User = Depends(get_current_user)) -> Principal:
        """Check the signed-in user's role and return the principal."""
        if not is_allowed(user.role, self.resource, write=self.write):
            raise PermissionDeniedError(
                denial_message(user.role, self.resource, write=self.write)
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
