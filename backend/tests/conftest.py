"""Shared pytest fixtures.

The app is pointed at a throwaway SQLite file before any app module is
imported. Each test then gets a freshly created and freshly seeded database, so
posting tests can commit without leaking state into one another.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="rpci-tests-"))
os.environ["RPCI_DATABASE_URL"] = f"sqlite:///{_TMP_DIR / 'test.db'}"
os.environ["RPCI_AUTO_SEED"] = "false"

from app import models_registry  # noqa: E402,F401
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.seed.loader import seed_if_empty  # noqa: E402


@pytest.fixture
def db():
    """Yield a session backed by a freshly seeded database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_if_empty(session)
    session.commit()
    try:
        yield session
    finally:
        session.close()
