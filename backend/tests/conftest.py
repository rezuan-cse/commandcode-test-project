"""Shared pytest fixtures.

The app is pointed at a throwaway database before any app module is imported.
Each test then gets a freshly created and freshly seeded database, so posting
tests can commit without leaking state into one another.

By default the database is a temporary SQLite file. Set RPCI_TEST_DATABASE_URL
to run the same suite against another engine, which is how the Postgres path is
verified before deployment:

    RPCI_TEST_DATABASE_URL=postgresql+psycopg://rpci:rpci@localhost:55432/rpci \
        .venv/bin/python -m pytest tests -q
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="rpci-tests-"))
os.environ["RPCI_DATABASE_URL"] = os.environ.get(
    "RPCI_TEST_DATABASE_URL", f"sqlite:///{_TMP_DIR / 'test.db'}"
)
os.environ["RPCI_AUTO_SEED"] = "false"

from app import models_registry  # noqa: E402,F401
from app.core.db import Base, SessionLocal, clear_all_data, engine  # noqa: E402
from app.seed.loader import seed_if_empty  # noqa: E402


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
