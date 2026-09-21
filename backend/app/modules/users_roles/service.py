"""Role/permission matrix enforcement.

Permissions are enforced here, on the server, so a restricted user gets a 403
even if they somehow reach a UI element. The demo exposes a role switcher that
sends the ``X-Demo-Role`` header, letting a reviewer prove the enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fastapi import Header

from app.core.enums import Role
from app.core.exceptions import PermissionDeniedError


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


@dataclass
class Principal:
    """The acting user for a request."""

    role: Role
    source: str

    @property
    def is_admin(self) -> bool:
        """True for the Admin role."""
        return self.role == Role.ADMIN


def resolve_role(x_demo_role: str | None) -> Role:
    """Resolve the acting role from the demo header, defaulting to Admin."""
    if not x_demo_role:
        return Role.ADMIN
    for role in Role:
        if role.value.lower() == x_demo_role.lower() or role.name.lower() == x_demo_role.lower():
            return role
    return Role.ADMIN


def require(resource: str, *, write: bool) -> "RequirePermission":
    """Build a FastAPI dependency enforcing access to ``resource``."""
    return RequirePermission(resource=resource, write=write)


class RequirePermission:
    """Callable dependency that raises 403 when the acting role lacks access."""

    def __init__(self, *, resource: str, write: bool) -> None:
        self.resource = resource
        self.write = write

    def __call__(self, x_demo_role: str | None = Header(default=None)) -> Principal:
        """Check the acting role and return the principal."""
        role = resolve_role(x_demo_role)
        if not is_allowed(role, self.resource, write=self.write):
            needed = "write" if self.write else "read"
            raise PermissionDeniedError(
                f"Role '{role.value}' does not have {needed} access to '{self.resource}'"
            )
        return Principal(role=role, source="header")


class RequireAdmin:
    """Callable dependency that allows only the Admin role.

    Configuration and role management live outside the resource matrix, so they
    are gated on the role itself rather than on a resource.
    """

    def __call__(self, x_demo_role: str | None = Header(default=None)) -> Principal:
        """Reject every role except Admin."""
        role = resolve_role(x_demo_role)
        if role != Role.ADMIN:
            raise PermissionDeniedError(
                f"Role '{role.value}' may not change configuration; Admin only"
            )
        return Principal(role=role, source="header")


def require_admin() -> RequireAdmin:
    """Build the Admin-only dependency."""
    return RequireAdmin()
