"""Demo housekeeping: restore the seeded workbook data on demand.

A public demo accumulates whatever visitors post. This lets a reviewer put it
back to the pristine state without a redeploy. It is disabled when
``RPCI_ALLOW_DEMO_RESET`` is false.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.exceptions import PermissionDeniedError
from app.seed.loader import SeedReport, seed_if_empty


def reset_demo() -> SeedReport:
    """Drop every table, recreate the schema, and re-seed from the workbook.

    Uses its own connection so the request's session is not left pointing at a
    table that no longer exists.
    """
    if not settings.allow_demo_reset:
        raise PermissionDeniedError("Demo reset is disabled on this deployment")

    # Imported so the models register on the metadata before create_all runs.
    from app import models_registry  # noqa: F401

    engine.dispose()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        report = seed_if_empty(session)

    from app.modules.settings import service as settings_service

    with SessionLocal() as session:
        settings_service.seed_defaults(session)
        session.commit()

    return report
