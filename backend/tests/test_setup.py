"""First-run setup: the account that has to exist before anything else.

A hosted deployment seeds no demo accounts, so a fresh database has no users and
nobody can sign in. These cover the door that was missing: it opens only while the
system is empty, creates one administrator, signs them in, and then shuts for good.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.modules.setup import service as setup_service
from app.modules.users_roles.models import User


def _count_users(db) -> int:
    from sqlalchemy import func, select

    return db.execute(select(func.count()).select_from(User)).scalar_one()


def _create(client: TestClient, **overrides):
    payload = {
        "full_name": "Resinova Admin",
        "email": "owner@resinovabd.com",
        "password": "a-long-password",
    }
    payload.update(overrides)
    return client.post("/api/setup/admin", json=payload)


def test_a_fresh_database_needs_setup(db, client: TestClient) -> None:
    """With no accounts at all, the interface must offer to create one."""
    from app.core.db import clear_all_data

    clear_all_data(db)
    db.commit()

    state = client.get("/api/setup/state")
    assert state.status_code == 200
    assert state.json()["needs_setup"] is True
    assert client.get("/api/meta").json()["needs_setup"] is True


def test_creating_the_first_administrator_signs_them_in(db, client: TestClient) -> None:
    """One call creates the account and hands back a usable session."""
    from app.core.db import clear_all_data

    clear_all_data(db)
    db.commit()

    response = _create(client)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["access_token"]
    assert body["user"]["email"] == "owner@resinovabd.com"
    assert body["user"]["role"] == "Admin"
    assert body["user"]["permissions"]["administration"] == "full"

    # The token works on a real endpoint.
    me = client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "owner@resinovabd.com"

    # And the door is now shut.
    assert client.get("/api/setup/state").json()["needs_setup"] is False


def test_setup_is_refused_once_any_account_exists(db, client: TestClient) -> None:
    """The seeded demo accounts are enough to close it."""
    assert _count_users(db) > 0

    response = _create(client, email="second@resinovabd.com")
    assert response.status_code == 409
    assert "already has an administrator" in response.json()["detail"]


def test_setup_cannot_be_used_twice(db, client: TestClient) -> None:
    """The second call is refused even with a different address."""
    from app.core.db import clear_all_data

    clear_all_data(db)
    db.commit()

    assert _create(client).status_code == 201
    second = _create(client, email="another@resinovabd.com")
    assert second.status_code == 409
    assert _count_users(db) == 1


def test_a_short_password_is_refused(db, client: TestClient) -> None:
    from app.core.db import clear_all_data

    clear_all_data(db)
    db.commit()

    response = _create(client, password="short")
    assert response.status_code == 422
    assert _count_users(db) == 0


def test_a_blank_name_is_refused(db, client: TestClient) -> None:
    from app.core.db import clear_all_data

    clear_all_data(db)
    db.commit()

    response = _create(client, full_name="")
    assert response.status_code == 422


def test_the_address_is_normalised(db, client: TestClient) -> None:
    """A typed-in address signs in whether or not it was capitalised."""
    from app.core.db import clear_all_data

    clear_all_data(db)
    db.commit()

    assert _create(client, email="  Owner@ResinovaBD.com ").status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": "owner@resinovabd.com", "password": "a-long-password"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]


def test_needs_setup_is_false_on_a_normal_deployment(db) -> None:
    """The demo-seeded database used by every other test is not a first run."""
    assert setup_service.needs_setup(db) is False
