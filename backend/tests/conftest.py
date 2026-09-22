"""Shared pytest fixtures.

The app is pointed at a throwaway database before any app module is imported.
Each test then gets a freshly created and freshly seeded database, so posting
tests can commit without leaking state into one another.

By default the database is a temporary SQLite file. Set RPCI_TEST_DATABASE_URL
to run the same suite against another engine, which is how the Postgres path is
verified before deployment:

    RPCI_TEST_DATABASE_URL=postgresql+psycopg://rpci:rpci@localhost:55432/rpci \
        .venv/bin/python -m pytest tests -q

Authentication is real, so requests need a token. Two fixtures cover that:
``auth_headers`` mints one directly for a role, which keeps the permission tests
fast and focused, while ``login`` signs in through the actual endpoint so the
genuine flow is exercised too.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_TMP_DIR = Path(tempfile.mkdtemp(prefix="rpci-tests-"))
os.environ["RPCI_DATABASE_URL"] = os.environ.get(
    "RPCI_TEST_DATABASE_URL", f"sqlite:///{_TMP_DIR / 'test.db'}"
)
os.environ["RPCI_AUTO_SEED"] = "false"
# A fixed signing key so tokens minted by tests are always verifiable.
os.environ.setdefault("RPCI_JWT_SECRET", "test-secret-not-for-production")

from app import models_registry  # noqa: E402,F401
from app.core.db import Base, SessionLocal, clear_all_data, engine  # noqa: E402
from app.core.enums import Role  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.loader import seed_if_empty  # noqa: E402

# The password the seeder gives every demo account.
DEMO_PASSWORD = "rpci"


@pytest.fixture
def db():
    """Yield a session backed by a freshly seeded database.

    Rows are deleted rather than tables dropped. Dropping the schema 59 times
    over is slow, and on Postgres it needs an exclusive lock that the pooled
    connections left behind by earlier TestClient calls can hold, which hangs
    the run.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        clear_all_data(session)
        seed_if_empty(session)
        session.commit()
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db) -> TestClient:
    """An unauthenticated test client.

    The application lifespan does not run when TestClient is used without a
    context manager, so the configurable settings defaults are seeded here.
    """
    from app.modules.settings import service as settings_service

    settings_service.seed_defaults(db)
    db.commit()
    return TestClient(app)


@pytest.fixture
def auth_headers(db) -> Callable[[Role], dict[str, str]]:
    """Return a function that yields Authorization headers for a role.

    The token is minted directly rather than earned through the sign-in endpoint.
    bcrypt costs a deliberate fraction of a second per call, and the permission
    tests are about the matrix, not about authentication — which has its own file
    exercising the real endpoints.
    """
    from app.core.security import create_token
    from app.modules.auth import repository

    def _headers(role: Role) -> dict[str, str]:
        for user in repository.list_users(db):
            if user.role == role:
                return {"Authorization": f"Bearer {create_token(user.id, role.value)}"}
        raise AssertionError(f"no seeded user for role {role.value}")

    return _headers


@pytest.fixture
def login(client: TestClient) -> Callable[..., tuple[int, dict]]:
    """Sign in through the real endpoint and return (status, body)."""

    def _login(email: str, password: str = DEMO_PASSWORD) -> tuple[int, dict]:
        response = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )
        return response.status_code, response.json()

    return _login
