"""Role-based access control, enforced at the API layer.

Mirrors the permission table in the build specification: a restricted role must
receive 403 from the server even if it reaches a screen in the browser.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app.core.enums import Role
from app.main import app
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


@pytest.fixture
def client(db) -> TestClient:
    """A test client sharing the seeded database session.

    The application lifespan does not run when TestClient is used without a
    context manager, so the configurable settings defaults are seeded here.
    """
    from app.modules.settings import service as settings_service

    settings_service.seed_defaults(db)
    db.commit()
    return TestClient(app)


@pytest.mark.parametrize(
    "role,path,expected",
    [
        ("Admin", "/api/accounts", 200),
        ("Accountant", "/api/accounts", 200),
        ("Owner/Viewer", "/api/accounts", 200),
        ("Store/Production Staff", "/api/accounts", 403),
        ("Sales Staff", "/api/accounts", 403),
    ],
)
def test_chart_of_accounts_endpoint_respects_role(
    client: TestClient, role: str, path: str, expected: int
) -> None:
    """The accounts endpoint returns 403 for roles without access."""
    response = client.get(path, headers={"X-Demo-Role": role})
    assert response.status_code == expected


@pytest.mark.parametrize(
    "role,expected",
    [
        ("Admin", 200),
        ("Store/Production Staff", 200),
        ("Accountant", 403),
        ("Sales Staff", 403),
        ("Owner/Viewer", 403),
    ],
)
def test_production_posting_respects_role(client: TestClient, role: str, expected: int) -> None:
    """Only Admin and store staff may post a production run."""
    payload = {
        "output_item_code": "WIP001",
        "qty_produced": "1",
        "production_date": "2026-10-15",
        "lines": [{"component_code": "RMC-003", "qty_consumed": "1"}],
    }
    response = client.post(
        "/api/production/preview", json=payload, headers={"X-Demo-Role": role}
    )
    assert response.status_code == expected


def test_access_matrix_endpoint_lists_every_role(client: TestClient) -> None:
    """The matrix endpoint describes all five roles."""
    response = client.get("/api/access/matrix")
    assert response.status_code == 200
    body = response.json()
    assert len(body["roles"]) == len(Role)
    assert "accounts" in body["resources"]


@pytest.mark.parametrize(
    "role,expected",
    [
        ("Admin", 200),
        ("Accountant", 403),
        ("Store/Production Staff", 403),
        ("Sales Staff", 403),
        ("Owner/Viewer", 403),
    ],
)
def test_only_admin_may_change_configuration(
    client: TestClient, role: str, expected: int
) -> None:
    """Configuration sits outside the resource matrix and is Admin-only."""
    response = client.patch(
        "/api/settings/vat.standard_rate_pct",
        json={"value": "15"},
        headers={"X-Demo-Role": role},
    )
    assert response.status_code == expected


def test_every_role_may_read_configuration(client: TestClient) -> None:
    """Reading the settings list is open to any signed-in role."""
    for role in Role:
        response = client.get("/api/settings", headers={"X-Demo-Role": role.value})
        assert response.status_code == 200, role.value


def test_access_levels_are_reported_correctly() -> None:
    """Full, view, and none are distinguished rather than collapsed to a boolean."""
    assert access_for(Role.ADMIN, "accounts") == Access.FULL
    assert access_for(Role.ACCOUNTANT, "accounts") == Access.VIEW
    assert access_for(Role.SALES_STAFF, "accounts") == Access.NONE
