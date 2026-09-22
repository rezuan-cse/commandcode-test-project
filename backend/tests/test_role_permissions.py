"""Role-based access control, enforced at the API layer.

Mirrors the permission table in the build specification: a restricted role must
receive 403 from the server even if it reaches a screen in the browser.

The identity behind these checks is a signed token, not a header the caller
chooses, so each request is made as a real signed-in user.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.enums import Role
from app.modules.users_roles.service import Access, access_for, is_allowed

# Resource-level expectations, read side.
EXPECTED_READ = {
    Role.ADMIN: {"accounts": True, "journal_entries": True, "items_bom": True,
                 "production": True, "sales_purchase": True, "reports": True},
    Role.ACCOUNTANT: {"accounts": True, "journal_entries": True, "items_bom": True,
                      "production": True, "sales_purchase": True, "reports": True},
    Role.STORE_PRODUCTION: {"accounts": False, "journal_entries": False, "items_bom": True,
                            "production": True, "sales_purchase": False, "reports": True},
    Role.SALES_STAFF: {"accounts": False, "journal_entries": False, "items_bom": True,
                       "production": False, "sales_purchase": True, "reports": True},
    Role.OWNER_VIEWER: {"accounts": True, "journal_entries": True, "items_bom": True,
                        "production": True, "sales_purchase": True, "reports": True},
}

# Resources that expose a write operation. Reports are read-only by design —
# every report is derived live — so they are excluded from the write matrix.
WRITABLE_RESOURCES = ["accounts", "journal_entries", "items_bom", "production", "sales_purchase"]

# Resources each role may write to.
EXPECTED_WRITE = {
    Role.ADMIN: {"accounts", "journal_entries", "items_bom", "production", "sales_purchase"},
    Role.ACCOUNTANT: {"journal_entries"},
    Role.STORE_PRODUCTION: {"items_bom", "production"},
    Role.SALES_STAFF: {"sales_purchase"},
    Role.OWNER_VIEWER: set(),
}

# Which seeded account holds which role.
DEMO_EMAIL = {
    Role.ADMIN: "admin@rpci.demo",
    Role.ACCOUNTANT: "accountant@rpci.demo",
    Role.STORE_PRODUCTION: "store@rpci.demo",
    Role.SALES_STAFF: "sales@rpci.demo",
    Role.OWNER_VIEWER: "owner@rpci.demo",
}


@pytest.mark.parametrize("role", list(Role))
def test_read_matrix_matches_specification(role: Role) -> None:
    """Every read permission matches the agreed table."""
    for resource, allowed in EXPECTED_READ[role].items():
        assert is_allowed(role, resource, write=False) is allowed, (
            f"{role.value} read {resource}"
        )


@pytest.mark.parametrize("role", list(Role))
def test_write_matrix_matches_specification(role: Role) -> None:
    """Every write permission matches the agreed table."""
    for resource in WRITABLE_RESOURCES:
        expected = resource in EXPECTED_WRITE[role]
        assert is_allowed(role, resource, write=True) is expected, (
            f"{role.value} write {resource}"
        )


@pytest.mark.parametrize(
    "role,expected",
    [
        (Role.ADMIN, 200),
        (Role.ACCOUNTANT, 200),
        (Role.OWNER_VIEWER, 200),
        (Role.STORE_PRODUCTION, 403),
        (Role.SALES_STAFF, 403),
    ],
)
def test_chart_of_accounts_endpoint_respects_role(
    client: TestClient, auth_headers, role: Role, expected: int
) -> None:
    """The accounts endpoint returns 403 for roles without access."""
    response = client.get("/api/accounts", headers=auth_headers(role))
    assert response.status_code == expected


@pytest.mark.parametrize(
    "role,expected",
    [
        (Role.ADMIN, 200),
        (Role.STORE_PRODUCTION, 200),
        (Role.ACCOUNTANT, 403),
        (Role.SALES_STAFF, 403),
        (Role.OWNER_VIEWER, 403),
    ],
)
def test_production_posting_respects_role(
    client: TestClient, auth_headers, role: Role, expected: int
) -> None:
    """Only Admin and store staff may post a production run."""
    payload = {
        "output_item_code": "WIP001",
        "qty_produced": "1",
        "production_date": "2026-10-15",
        "lines": [{"component_code": "RMC-003", "qty_consumed": "1"}],
    }
    response = client.post(
        "/api/production/preview", json=payload, headers=auth_headers(role)
    )
    assert response.status_code == expected


def test_an_unauthenticated_request_is_refused(client: TestClient) -> None:
    """No token at all means 401, not a default role."""
    assert client.get("/api/accounts").status_code == 401


def test_the_old_role_header_cannot_impersonate(
    client: TestClient, auth_headers
) -> None:
    """A caller cannot promote themselves by setting the old demo header.

    This is the hole that real authentication closes: the header used to select
    the acting role, so anyone could set X-Demo-Role: Admin and be an
    administrator.
    """
    response = client.get("/api/accounts", headers={"X-Demo-Role": "Admin"})
    assert response.status_code == 401

    # And a genuine low-privilege token cannot be upgraded by the header either.
    store = auth_headers(Role.STORE_PRODUCTION)
    response = client.get("/api/accounts", headers={**store, "X-Demo-Role": "Admin"})
    assert response.status_code == 403


def test_a_token_from_one_role_cannot_perform_another_roles_write(
    client: TestClient, auth_headers
) -> None:
    """The token's role is what counts, and it is checked on every request."""
    store = auth_headers(Role.STORE_PRODUCTION)
    payload = {
        "voucher_no": "PRIV-1",
        "entry_date": "2026-10-15",
        "lines": [
            {"account_code": "1010", "segment": "Shared", "debit": "1"},
            {"account_code": "4010", "segment": "Manufacturing", "credit": "1"},
        ],
    }
    assert client.post("/api/journal-entries", json=payload, headers=store).status_code == 403


def test_access_matrix_endpoint_lists_every_role(
    client: TestClient, auth_headers
) -> None:
    """The matrix endpoint describes all five roles."""
    response = client.get("/api/access/matrix", headers=auth_headers(Role.ADMIN))
    assert response.status_code == 200
    body = response.json()
    assert len(body["roles"]) == len(Role)
    assert "accounts" in body["resources"]


@pytest.mark.parametrize(
    "role,expected",
    [
        (Role.ADMIN, 200),
        (Role.ACCOUNTANT, 403),
        (Role.STORE_PRODUCTION, 403),
        (Role.SALES_STAFF, 403),
        (Role.OWNER_VIEWER, 403),
    ],
)
def test_only_admin_may_change_configuration(
    client: TestClient, auth_headers, role: Role, expected: int
) -> None:
    """Configuration sits outside the resource matrix and is Admin-only."""
    response = client.patch(
        "/api/settings/vat.standard_rate_pct",
        json={"value": "15"},
        headers=auth_headers(role),
    )
    assert response.status_code == expected


def test_user_listing_is_admin_only(client: TestClient, auth_headers) -> None:
    """Listing colleagues' accounts is not available to every role."""
    assert client.get("/api/access/users", headers=auth_headers(Role.ADMIN)).status_code == 200
    assert (
        client.get("/api/access/users", headers=auth_headers(Role.OWNER_VIEWER)).status_code
        == 403
    )


def test_every_role_may_read_configuration(client: TestClient, auth_headers) -> None:
    """Reading the settings list is open to any signed-in role."""
    for role in Role:
        response = client.get("/api/settings", headers=auth_headers(role))
        assert response.status_code == 200, role.value


def test_access_levels_are_reported_correctly() -> None:
    """Full, view, and none are distinguished rather than collapsed to a boolean."""
    assert access_for(Role.ADMIN, "accounts") == Access.FULL
    assert access_for(Role.ACCOUNTANT, "accounts") == Access.VIEW
    assert access_for(Role.SALES_STAFF, "accounts") == Access.NONE
