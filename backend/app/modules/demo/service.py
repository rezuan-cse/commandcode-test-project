"""Demo housekeeping: restore the seeded workbook data on demand.

A public demo accumulates whatever visitors post. This lets a reviewer put it
back to the pristine state without a redeploy. It is disabled when
``RPCI_ALLOW_DEMO_RESET`` is false.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.db import SessionLocal, clear_all_data
from app.core.exceptions import PermissionDeniedError
from app.seed.loader import SeedReport, seed_if_empty


def reset_demo() -> SeedReport:
    """Empty every table and re-seed from the workbook.

    Empties rows rather than dropping the schema, so it is safe to run while the
    application is serving requests. On Postgres a DROP TABLE would wait for an
    exclusive lock and hang behind any open reader.
    """
    if not settings.allow_demo_reset:
        raise PermissionDeniedError("Demo reset is disabled on this deployment")

    with SessionLocal() as session:
        clear_all_data(session)
        report = seed_if_empty(session)
        session.commit()

    from app.modules.settings import service as settings_service

    with SessionLocal() as session:
        settings_service.seed_defaults(session)
        session.commit()

    return report
