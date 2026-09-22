"""Authentication: password sign-in, the TOTP second factor, and recovery.

These exercise the real HTTP endpoints rather than calling the service directly,
because the security properties being checked are about what the API exposes and
what it refuses.
"""

from __future__ import annotations

import pyotp
import pytest
from fastapi.testclient import TestClient

ADMIN = "admin@rpci.demo"
# The password the seeder gives every demo account.
DEMO_PASSWORD = "rpci"


def _totp(secret: str) -> str:
    """A currently valid code for a secret."""
    return pyotp.TOTP(secret).now()


def _enable_two_factor(client: TestClient, headers: dict[str, str]) -> tuple[str, list[str]]:
    """Enrol 2FA for the signed-in user, returning (secret, recovery codes)."""
    setup = client.post("/api/auth/2fa/setup", headers=headers).json()
    secret = setup["secret"]
    enabled = client.post(
        "/api/auth/2fa/enable", json={"code": _totp(secret)}, headers=headers
    ).json()
    return secret, enabled["recovery_codes"]


@pytest.fixture
def admin_headers(client: TestClient, login) -> dict[str, str]:
    """Sign in as the administrator and return bearer headers."""
    _, body = login(ADMIN)
    return {"Authorization": f"Bearer {body['access_token']}"}


# --- Password sign-in ---------------------------------------------------


def test_correct_password_issues_a_session(login) -> None:
    """A good password returns a token and the user."""
    status, body = login(ADMIN)
    assert status == 200
    assert body["needs_2fa"] is False
    assert body["access_token"]
    assert body["user"]["role"] == "Admin"


def test_wrong_password_is_refused(login) -> None:
    """A bad password is a 401 with no token."""
    status, body = login(ADMIN, "not-the-password")
    assert status == 401
    assert "access_token" not in body or body.get("access_token") is None


def test_unknown_email_is_refused_the_same_way(client: TestClient, login) -> None:
    """An unknown account is indistinguishable from a wrong password.

    The wording matters: if the two differed, the endpoint would let someone
    discover which email addresses have accounts.
    """
    status, body = login("nobody@rpci.demo")
    assert status == 401
    assert body["detail"] == "Email or password is incorrect"


def test_the_password_is_hashed_in_the_database(client: TestClient, login, db) -> None:
    """The stored value is a bcrypt hash, never the password itself."""
    from app.modules.auth import repository

    user = repository.get_by_email(db, ADMIN)
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash != DEMO_PASSWORD
    assert user.password_hash.startswith("$2b$")


def test_no_endpoint_returns_credential_material(client: TestClient, admin_headers) -> None:
    """Neither the hash nor the TOTP secret can leak through the API."""
    body = client.get("/api/auth/me", headers=admin_headers).text
    assert "password_hash" not in body
    assert "totp_secret" not in body


def test_a_disabled_account_cannot_sign_in(client: TestClient, login, db) -> None:
    """Clearing is_active takes effect immediately."""
    from app.modules.auth import repository

    user = repository.get_by_email(db, "sales@rpci.demo")
    user.is_active = False
    db.commit()

    status, body = login("sales@rpci.demo")
    assert status == 401
    assert "disabled" in body["detail"].lower()


# --- Two-factor ---------------------------------------------------------


def test_two_factor_can_be_enrolled(client: TestClient, admin_headers) -> None:
    """Setup returns a scannable secret and a QR image."""
    response = client.post("/api/auth/2fa/setup", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert len(body["secret"]) >= 16
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert body["qr_png_data_uri"].startswith("data:image/png;base64,")


def test_a_wrong_code_does_not_enable_two_factor(client: TestClient, admin_headers) -> None:
    """Enrolment must prove the authenticator actually works."""
    client.post("/api/auth/2fa/setup", headers=admin_headers)
    response = client.post(
        "/api/auth/2fa/enable", json={"code": "000000"}, headers=admin_headers
    )
    assert response.status_code == 401
    assert client.get("/api/auth/me", headers=admin_headers).json()["is_2fa_enabled"] is False


def test_password_alone_does_not_grant_a_session_once_enabled(
    client: TestClient, admin_headers, login
) -> None:
    """The critical property: after enrolment a password is not enough."""
    _enable_two_factor(client, admin_headers)

    status, body = login(ADMIN)
    assert status == 200
    assert body["needs_2fa"] is True
    assert body["access_token"] is None
    assert body["challenge_token"]


def test_a_valid_authenticator_code_completes_sign_in(
    client: TestClient, admin_headers, login
) -> None:
    """The second step issues a real session."""
    secret, _ = _enable_two_factor(client, admin_headers)
    _, step_one = login(ADMIN)

    response = client.post(
        "/api/auth/login/totp",
        json={"challenge_token": step_one["challenge_token"], "code": _totp(secret)},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_a_bad_code_does_not_complete_sign_in(
    client: TestClient, admin_headers, login
) -> None:
    """A wrong code at the second step is refused."""
    _enable_two_factor(client, admin_headers)
    _, step_one = login(ADMIN)

    response = client.post(
        "/api/auth/login/totp",
        json={"challenge_token": step_one["challenge_token"], "code": "000000"},
    )
    assert response.status_code == 401


def test_a_challenge_token_is_not_a_session(client: TestClient, admin_headers, login) -> None:
    """The half-authenticated token cannot be used to reach protected routes.

    Without the purpose check on the token this would pass, and a password would
    be enough after all.
    """
    _enable_two_factor(client, admin_headers)
    _, step_one = login(ADMIN)

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {step_one['challenge_token']}"},
    )
    assert response.status_code == 401


def test_a_recovery_code_works_once_and_only_once(
    client: TestClient, admin_headers, login
) -> None:
    """Recovery codes exist so a lost phone is not a lost account."""
    _, codes = _enable_two_factor(client, admin_headers)
    code = codes[0]

    _, first = login(ADMIN)
    ok = client.post(
        "/api/auth/login/totp",
        json={"challenge_token": first["challenge_token"], "code": code},
    )
    assert ok.status_code == 200

    _, second = login(ADMIN)
    reused = client.post(
        "/api/auth/login/totp",
        json={"challenge_token": second["challenge_token"], "code": code},
    )
    assert reused.status_code == 401


def test_disabling_two_factor_requires_the_password(
    client: TestClient, admin_headers
) -> None:
    """A live session alone must not be enough to weaken the account."""
    _enable_two_factor(client, admin_headers)

    wrong = client.post(
        "/api/auth/2fa/disable", json={"password": "nope"}, headers=admin_headers
    )
    assert wrong.status_code == 401
    assert client.get("/api/auth/me", headers=admin_headers).json()["is_2fa_enabled"] is True

    right = client.post(
        "/api/auth/2fa/disable",
        json={"password": DEMO_PASSWORD},
        headers=admin_headers,
    )
    assert right.status_code == 200
    assert client.get("/api/auth/me", headers=admin_headers).json()["is_2fa_enabled"] is False


# --- Password change ----------------------------------------------------


def test_changing_the_password_replaces_the_old_one(
    client: TestClient, admin_headers, login
) -> None:
    """The new password works and the old one stops working."""
    changed = client.post(
        "/api/auth/password",
        json={"current_password": DEMO_PASSWORD, "new_password": "a-longer-secret"},
        headers=admin_headers,
    )
    assert changed.status_code == 200

    assert login(ADMIN, "a-longer-secret")[0] == 200
    assert login(ADMIN, DEMO_PASSWORD)[0] == 401


def test_changing_the_password_needs_the_current_one(
    client: TestClient, admin_headers, login
) -> None:
    """A session cannot be used to take over the account."""
    response = client.post(
        "/api/auth/password",
        json={"current_password": "wrong", "new_password": "a-longer-secret"},
        headers=admin_headers,
    )
    assert response.status_code == 401
    assert login(ADMIN, DEMO_PASSWORD)[0] == 200
