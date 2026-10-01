"""Creating, changing and removing user accounts, and per-user access grants.

Accounts are managed by an administrator; the access a person then has is their
role's default plus any exception recorded against them, and the server enforces
the result on every request.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.enums import Role
from app.modules.users_roles.models import User, UserPermission

ADMIN = Role.ADMIN
STORE = Role.STORE_PRODUCTION


def _create(client: TestClient, headers: dict, **overrides) -> dict:
    """Add an account and return the response body."""
    payload = {
        "email": "new.person@example.com",
        "full_name": "New Person",
        "role": "Sales Staff",
        **overrides,
    }
    response = client.post("/api/access/users", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


# --- Creating -------------------------------------------------------------


def test_an_admin_can_create_an_account(client: TestClient, auth_headers) -> None:
    """A generated password is returned once, and the dates are recorded."""
    body = _create(client, auth_headers(ADMIN))

    assert body["user"]["email"] == "new.person@example.com"
    assert body["user"]["role"] == "Sales Staff"
    assert body["user"]["is_active"] is True
    assert body["password"], "a password should be generated"
    assert body["user"]["created_at"] and body["user"]["updated_at"]


def test_the_new_account_can_sign_in(client: TestClient, auth_headers) -> None:
    """The generated password actually works."""
    body = _create(client, auth_headers(ADMIN), email="signin@example.com")

    response = client.post(
        "/api/auth/login",
        json={"email": "signin@example.com", "password": body["password"]},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "signin@example.com"


def test_a_chosen_password_is_not_echoed_back(client: TestClient, auth_headers) -> None:
    """A password the administrator typed stays theirs to remember."""
    body = _create(
        client, auth_headers(ADMIN), email="chosen@example.com", password="hunter2-secret"
    )
    assert body["password"] is None

    ok = client.post(
        "/api/auth/login",
        json={"email": "chosen@example.com", "password": "hunter2-secret"},
    )
    assert ok.status_code == 200


def test_a_duplicate_address_is_refused(client: TestClient, auth_headers) -> None:
    """Two accounts cannot share an address."""
    headers = auth_headers(ADMIN)
    _create(client, headers, email="taken@example.com")

    response = client.post(
        "/api/access/users",
        json={"email": "taken@example.com", "full_name": "Other", "role": "Admin"},
        headers=headers,
    )
    assert response.status_code == 409


def test_only_an_administrator_can_manage_accounts(
    client: TestClient, auth_headers
) -> None:
    """Adding and removing accounts is not available to any other role."""
    for role in [Role.ACCOUNTANT, STORE, Role.SALES_STAFF, Role.OWNER_VIEWER]:
        response = client.post(
            "/api/access/users",
            json={"email": "x@example.com", "full_name": "X", "role": "Sales Staff"},
            headers=auth_headers(role),
        )
        assert response.status_code == 403, role.value


# --- Changing -------------------------------------------------------------


def test_an_admin_can_change_name_and_role(client: TestClient, auth_headers) -> None:
    """Details and role can both be corrected."""
    headers = auth_headers(ADMIN)
    user_id = _create(client, headers, email="change@example.com")["user"]["id"]

    response = client.patch(
        f"/api/access/users/{user_id}",
        json={"full_name": "Renamed Person", "role": "Accountant"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Renamed Person"
    assert response.json()["role"] == "Accountant"


def test_changing_your_own_role_is_refused(client: TestClient, auth_headers, db) -> None:
    """Demoting yourself would lock you out of the screen you are standing on."""
    admin = db.execute(select(User).where(User.role == ADMIN)).scalars().first()

    response = client.patch(
        f"/api/access/users/{admin.id}",
        json={"role": "Sales Staff"},
        headers=auth_headers(ADMIN),
    )
    assert response.status_code == 400
    assert "own role" in response.json()["detail"]


def test_the_last_administrator_cannot_be_demoted(
    client: TestClient, auth_headers, db
) -> None:
    """There must always be somebody who can administer the system."""
    headers = auth_headers(ADMIN)
    other = _create(client, headers, email="second.admin@example.com", role="Admin")
    admin = db.execute(select(User).where(User.role == ADMIN)).scalars().first()

    # With two administrators, demoting one is fine ...
    ok = client.patch(
        f"/api/access/users/{other['user']['id']}",
        json={"role": "Accountant"},
        headers=headers,
    )
    assert ok.status_code == 200

    # ... but the one that is left cannot be moved, nor removed.
    assert (
        client.patch(
            f"/api/access/users/{admin.id}", json={"role": "Accountant"}, headers=headers
        ).status_code
        == 400
    )
    assert (
        client.delete(f"/api/access/users/{admin.id}", headers=headers).status_code == 400
    )


# --- Removing -------------------------------------------------------------


def test_an_admin_can_delete_an_account(client: TestClient, auth_headers, db) -> None:
    """A removed account cannot sign in again."""
    headers = auth_headers(ADMIN)
    body = _create(client, headers, email="remove@example.com")
    user_id = body["user"]["id"]

    response = client.delete(f"/api/access/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert db.get(User, user_id) is None

    denied = client.post(
        "/api/auth/login",
        json={"email": "remove@example.com", "password": body["password"]},
    )
    assert denied.status_code == 401


def test_you_cannot_delete_your_own_account(
    client: TestClient, auth_headers, db
) -> None:
    """Otherwise an administrator could remove themselves by mistake."""
    admin = db.execute(select(User).where(User.role == ADMIN)).scalars().first()

    response = client.delete(f"/api/access/users/{admin.id}", headers=auth_headers(ADMIN))
    assert response.status_code == 400
    assert "own account" in response.json()["detail"]


# --- Per-user access ------------------------------------------------------


def _store_user_id(db) -> int:
    return db.execute(select(User).where(User.role == STORE)).scalars().first().id


def test_granting_an_area_opens_it_for_that_person(
    client: TestClient, auth_headers, db
) -> None:
    """A grant on top of the role is honoured by the server, not just the menu."""
    store = auth_headers(STORE)
    assert client.get("/api/reports/trial-balance?as_of=2026-10-31", headers=store).status_code == 403

    store_id = _store_user_id(db)
    granted = client.put(
        f"/api/access/users/{store_id}/permissions",
        json={"access": {"reports": "view"}},
        headers=auth_headers(ADMIN),
    )
    assert granted.status_code == 200

    # The same token now reads the report, and /me reports the new level.
    assert client.get("/api/reports/trial-balance?as_of=2026-10-31", headers=store).status_code == 200
    me = client.get("/api/auth/me", headers=store).json()
    assert me["permissions"]["reports"] == "view"


def test_denying_an_area_closes_it_for_that_person(
    client: TestClient, auth_headers, db
) -> None:
    """A denial takes away something the role would otherwise allow."""
    store = auth_headers(STORE)
    assert client.get("/api/items", headers=store).status_code == 200

    store_id = _store_user_id(db)
    client.put(
        f"/api/access/users/{store_id}/permissions",
        json={"access": {"items_bom": "none"}},
        headers=auth_headers(ADMIN),
    )

    assert client.get("/api/items", headers=store).status_code == 403


def test_access_can_be_put_back_to_the_role_default(
    client: TestClient, auth_headers, db
) -> None:
    """Setting the role's own level removes the exception rather than storing it."""
    admin = auth_headers(ADMIN)
    store_id = _store_user_id(db)

    client.put(
        f"/api/access/users/{store_id}/permissions",
        json={"access": {"reports": "view"}},
        headers=admin,
    )
    assert db.execute(select(UserPermission).where(UserPermission.user_id == store_id)).scalars().all()

    # "none" is what the Store role already gives reports, so the row goes.
    client.put(
        f"/api/access/users/{store_id}/permissions",
        json={"access": {"reports": "none"}},
        headers=admin,
    )
    assert db.execute(select(UserPermission).where(UserPermission.user_id == store_id)).scalars().all() == []


def test_the_permission_view_shows_defaults_grants_and_result(
    client: TestClient, auth_headers, db
) -> None:
    """The screen needs all three to explain what a person can do."""
    store_id = _store_user_id(db)
    client.put(
        f"/api/access/users/{store_id}/permissions",
        json={"access": {"reports": "view"}},
        headers=auth_headers(ADMIN),
    )

    body = client.get(
        f"/api/access/users/{store_id}/permissions", headers=auth_headers(ADMIN)
    ).json()
    assert body["role"] == "Store/Production Staff"
    assert body["role_defaults"]["reports"] == "none"
    assert body["overrides"]["reports"] == "view"
    assert body["effective"]["reports"] == "view"


def test_you_cannot_change_your_own_access(client: TestClient, auth_headers, db) -> None:
    """A slip here would lock an administrator out of this very screen."""
    admin = db.execute(select(User).where(User.role == ADMIN)).scalars().first()

    response = client.put(
        f"/api/access/users/{admin.id}/permissions",
        json={"access": {"administration": "none"}},
        headers=auth_headers(ADMIN),
    )
    assert response.status_code == 400
    assert "own access" in response.json()["detail"]


def test_an_unknown_area_is_refused(client: TestClient, auth_headers, db) -> None:
    """Only real areas can be granted."""
    store_id = _store_user_id(db)
    response = client.put(
        f"/api/access/users/{store_id}/permissions",
        json={"access": {"not_a_real_area": "view"}},
        headers=auth_headers(ADMIN),
    )
    assert response.status_code == 400


def test_the_owner_may_look_at_administration_but_not_administer(
    client: TestClient, auth_headers
) -> None:
    """The administration area is readable by an owner; the actions are not."""
    owner = auth_headers(Role.OWNER_VIEWER)
    me = client.get("/api/auth/me", headers=owner).json()
    assert me["permissions"]["administration"] == "view"
    # The matrix is readable, account management is not.
    assert client.get("/api/access/matrix", headers=owner).status_code == 200
    assert client.get("/api/access/users", headers=owner).status_code == 403
