"""Demo housekeeping: restore the books to a pristine state on demand.

A public demo accumulates whatever visitors post. This lets a reviewer put it
back to the starting state without a redeploy. It is disabled when
``RPCI_ALLOW_DEMO_RESET`` is false.
"""

from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import PermissionDeniedError
from app.seed.loader import SeedReport


def reset_demo() -> SeedReport:
    """Empty every table and re-seed according to the deployment's seed mode.

    Empties rows rather than dropping the schema, so it is safe to run while the
    application is serving requests. On Postgres a DROP TABLE would wait for an
    exclusive lock and hang behind any open reader.

    Under the default ``fresh`` mode this restores the standard starter chart of
    accounts; under ``workbook`` it restores the sample data.
    """
    if not settings.allow_demo_reset:
        raise PermissionDeniedError("Demo reset is disabled on this deployment")

    from app.modules.data import service as data_service

    return data_service.reset(settings.seed_mode)
