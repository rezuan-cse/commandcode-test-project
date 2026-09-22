"""Account administration: helping someone who cannot sign in.

The situation being covered is a user who has lost both their authenticator and
their recovery codes. Before these endpoints existed the only way back in was to
edit the database by hand.
"""

from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

from app.core.enums import Role

ADMIN = "admin@rpci.demo"
SALES = "sales@rpci.demo"
DEMO_PASSWORD = "rpci"


def _token(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> str:
    """Sign in and return the access token."""
    body = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    ).json()
    return body["access_token"]


def _headers(client: TestClient, email: str) -> dict[str, str]:
    """Bearer headers for a signed-in user."""
    return {"Authorization": f"Bearer {_token(client, email)}"}


def _user_id(client: TestClient, admin_headers: dict[str, str], email: str) -> int:
    """Look up a user id from the admin listing."""
    users = client.get("/api/access/users", headers=admin_headers).json()
    return next(user["id"] for user in users if user["email"] == email)


def _enrol_two_factor(client: TestClient, headers: dict[str, str]) -> str:
    """Turn on 2FA for the signed-in user, returning the secret."""
    secret = client.post("/api/auth/2fa/setup", headers=headers).json()["secret"]
    client.post(
        "/api/auth/2fa/enable",
        json={"code": pyotp.TOTP(secret).now()},
        headers=headers,
    )
    return secret


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    """Headers for the administrator."""
    return _headers(client, ADMIN)


# --- Unlocking ----------------------------------------------------------


def test_admin_can_clear_a_lost_second_factor(client: TestClient, admin) -> None:
    """The whole point: a locked-out user can be let back in by an administrator."""
    sales = _headers(client, SALES)
    _enrol_two_factor(client, sales)

    # Locked out: a password alone is no longer enough.
    assert client.post("/api/auth/login", json={"email": SALES, "password": DEMO_PASSWORD}).json()[
        "needs_2fa"
    ] is True

    user_id = _user_id(client, admin, SALES)
    response = client.post(f"/api/access/users/{user_id}/reset-two-factor", headers=admin)
    assert response.status_code == 200

    # And the password is enough again.
    body = client.post("/api/auth/login", json={"email": SALES, "password": DEMO_PASSWORD}).json()
    assert body["needs_2fa"] is False
    assert body["access_token"]


def test_resetting_two_factor_voids_the_recovery_codes(client: TestClient, admin, db) -> None:
    """Codes issued for the old secret must not still open the door.

    If they survived, a copy of the old codes would let someone back in without
    the new authenticator the user is about to set up.
    """
    from app.modules.auth import repository

    sales = _headers(client, SALES)
    _enrol_two_factor(client, sales)

    before = len(repository.get_by_email(db, SALES).recovery_codes)
    assert before == 8

    user_id = _user_id(client, admin, SALES)
    client.post(f"/api/access/users/{user_id}/reset-two-factor", headers=admin)

    db.expire_all()
    assert len(repository.get_by_email(db, SALES).recovery_codes) == 0


def test_resetting_two_factor_that_is_not_on_is_refused(client: TestClient, admin) -> None:
    """Nothing to clear, so say so rather than pretending it worked."""
    user_id = _user_id(client, admin, "owner@rpci.demo")
    response = client.post(f"/api/access/users/{user_id}/reset-two-factor", headers=admin)
    assert response.status_code == 400
    assert "does not have two-factor" in response.json()["detail"]


def test_an_administrator_cannot_unlock_their_own_account(client: TestClient, admin, db) -> None:
    """That is what the Security page is for, so the admin screen refuses."""
    admin_id = _user_id(client, admin, ADMIN)
    response = client.post(
        f"/api/access/users/{admin_id}/reset-two-factor", headers=admin
    )
    assert response.status_code == 400
    assert "Security page" in response.json()["detail"]


# --- Passwords ----------------------------------------------------------


def test_admin_can_issue_a_new_password(client: TestClient, admin) -> None:
    """The other lock-out: a forgotten password."""
    user_id = _user_id(client, admin, SALES)

    response = client.post(f"/api/access/users/{user_id}/reset-password", headers=admin)
    assert response.status_code == 200
    issued = response.json()["password"]
    assert len(issued) >= 8
    assert issued != DEMO_PASSWORD

    # The new password works and the old one does not.
    assert client.post("/api/auth/login", json={"email": SALES, "password": issued}).status_code == 200
    assert client.post(
        "/api/auth/login", json={"email": SALES, "password": DEMO_PASSWORD}
    ).status_code == 401


def test_the_issued_password_is_not_stored_readably(client: TestClient, admin, db) -> None:
    """It comes back once and is written only as a hash."""
    from app.modules.auth import repository

    user_id = _user_id(client, admin, SALES)
    issued = client.post(
        f"/api/access/users/{user_id}/reset-password", headers=admin
    ).json()["password"]

    db.expire_all()
    stored = repository.get_by_email(db, SALES).password_hash
    assert stored != issued
    assert stored.startswith("$2b$")


def test_an_administrator_cannot_reset_their_own_password_here(client: TestClient, admin) -> None:
    """The Security page changes your own password, with the current one."""
    admin_id = _user_id(client, admin, ADMIN)
    response = client.post(
        f"/api/access/users/{admin_id}/reset-password", headers=admin
    )
    assert response.status_code == 400
    assert "Security page" in response.json()["detail"]


# --- Enabling and disabling ---------------------------------------------


def test_disabling_an_account_blocks_the_next_request(client: TestClient, admin) -> None:
    """Takes effect immediately, not when the token happens to expire."""
    sales = _headers(client, SALES)
    assert client.get("/api/sales", headers=sales).status_code == 200

    user_id = _user_id(client, admin, SALES)
    assert client.post(
        f"/api/access/users/{user_id}/active", json={"is_active": False}, headers=admin
    ).status_code == 200

    # The token is still signed and unexpired, but the account is off.
    assert client.get("/api/sales", headers=sales).status_code == 401
    assert client.post(
        "/api/auth/login", json={"email": SALES, "password": DEMO_PASSWORD}
    ).status_code == 401


def test_a_disabled_account_can_be_reenabled(client: TestClient, admin) -> None:
    """Turning it back on restores access."""
    user_id = _user_id(client, admin, SALES)
    client.post(f"/api/access/users/{user_id}/active", json={"is_active": False}, headers=admin)
    assert client.post(
        f"/api/access/users/{user_id}/active", json={"is_active": True}, headers=admin
    ).status_code == 200
    assert client.post(
        "/api/auth/login", json={"email": SALES, "password": DEMO_PASSWORD}
    ).status_code == 200


def test_an_administrator_cannot_disable_themselves(client: TestClient, admin) -> None:
    """Locking yourself out of the account you are using is never intended."""
    admin_id = _user_id(client, admin, ADMIN)
    response = client.post(
        f"/api/access/users/{admin_id}/active", json={"is_active": False}, headers=admin
    )
    assert response.status_code == 400
    assert "cannot disable your own account" in response.json()["detail"].lower()


def test_the_system_cannot_be_left_without_an_administrator(
    client: TestClient, admin
) -> None:
    """Reaching zero administrators is impossible, and this is why.

    An administrator can only disable somebody else, and disabling one of two
    administrators leaves one. The only route to zero would be disabling
    yourself, which is refused — so this single check is what guarantees the
    system stays administrable.
    """
    admin_id = _user_id(client, admin, ADMIN)
    response = client.post(
        f"/api/access/users/{admin_id}/active", json={"is_active": False}, headers=admin
    )
    assert response.status_code == 400
    assert "cannot disable your own account" in response.json()["detail"].lower()


def test_one_administrator_may_stand_another_down(client: TestClient, admin, db) -> None:
    """The guard is not so broad that it blocks a legitimate second admin."""
    from app.core.enums import Role as RoleEnum
    from app.modules.auth import repository

    accountant = repository.get_by_email(db, "accountant@rpci.demo")
    accountant.role = RoleEnum.ADMIN
    db.commit()

    response = client.post(
        f"/api/access/users/{accountant.id}/active",
        json={"is_active": False},
        headers=admin,
    )
    assert response.status_code == 200

    # The administrator who performed it is still active, so the system remains
    # administrable.
    db.expire_all()
    assert repository.get_by_email(db, ADMIN).is_active is True


# --- Authorisation ------------------------------------------------------


@pytest.mark.parametrize(
    "role", [Role.ACCOUNTANT, Role.STORE_PRODUCTION, Role.SALES_STAFF, Role.OWNER_VIEWER]
)
def test_these_actions_are_admin_only(client: TestClient, auth_headers, role: Role, admin) -> None:
    """Lowering somebody's account security is not for anyone else."""
    sales_id = _user_id(client, admin, SALES)
    headers = auth_headers(role)

    assert client.post(
        f"/api/access/users/{sales_id}/reset-two-factor", headers=headers
    ).status_code == 403
    assert client.post(
        f"/api/access/users/{sales_id}/reset-password", headers=headers
    ).status_code == 403
    assert client.post(
        f"/api/access/users/{sales_id}/active", json={"is_active": False}, headers=headers
    ).status_code == 403


def test_these_actions_need_a_session(client: TestClient, admin) -> None:
    """Signed out means refused."""
    sales_id = _user_id(client, admin, SALES)
    assert client.post(f"/api/access/users/{sales_id}/reset-two-factor").status_code == 401
    assert client.post(f"/api/access/users/{sales_id}/reset-password").status_code == 401


# --- Audit --------------------------------------------------------------


def test_every_action_is_recorded(client: TestClient, admin) -> None:
    """Who cleared whose second factor, and when, has to be answerable."""
    sales = _headers(client, SALES)
    _enrol_two_factor(client, sales)
    sales_id = _user_id(client, admin, SALES)

    client.post(f"/api/access/users/{sales_id}/reset-two-factor", headers=admin)
    client.post(f"/api/access/users/{sales_id}/reset-password", headers=admin)
    client.post(f"/api/access/users/{sales_id}/active", json={"is_active": False}, headers=admin)

    entries = client.get("/api/access/audit", headers=admin).json()
    actions = {entry["action"] for entry in entries}
    assert {"reset_two_factor", "reset_password", "disable_account"} <= actions
    for entry in entries:
        assert entry["actor_email"] == ADMIN
        assert entry["target_email"] == SALES


def test_the_audit_log_is_admin_only(client: TestClient, auth_headers) -> None:
    """It names accounts and what was done to them."""
    assert client.get("/api/access/audit", headers=auth_headers(Role.ACCOUNTANT)).status_code == 403
    assert (
        client.get("/api/access/audit", headers=auth_headers(Role.OWNER_VIEWER)).status_code
        == 403
    )
