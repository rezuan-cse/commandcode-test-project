"""Fresh-start and import operations for the books.

A deployment can start empty, from a standard starter chart of accounts, or from
the client's workbook — and an administrator can import a workbook or start over
at any time. All of it goes through here so the rules live in one place.
"""

from __future__ import annotations

import io

from app.core.config import settings
from app.core.db import KEEP_ACCOUNTS, SessionLocal, clear_all_data
from app.seed.loader import (
    SeedReport,
    ensure_demo_users,
    import_workbook,
    seed_if_empty,
)
from app.seed.starter import seed_starter


def _restore_basics(session) -> None:
    """Re-create what a wipe removes that is not the client's data.

    The configuration is rebuilt from the catalogue, and the demo accounts are
    recreated only when they are wanted. User accounts themselves are never
    cleared by a reset, so this cannot be the step that locks somebody out.
    """
    from app.modules.settings import service as settings_service

    settings_service.seed_defaults(session)
    ensure_demo_users(session)
    session.commit()


def reset(mode: str | None = None) -> SeedReport:
    """Empty the books and start again in the chosen mode.

    Modes: ``fresh`` (starter chart of accounts), ``workbook`` (the sample
    workbook), or ``none`` (leave the books empty).

    The accounts that sign in are kept: emptying the books is an accounting
    decision and should not remove the people who use the system.
    """
    chosen = mode or settings.seed_mode
    with SessionLocal() as session:
        clear_all_data(session, keep=KEEP_ACCOUNTS)
        if chosen == "workbook":
            report = seed_if_empty(session)
        elif chosen == "none":
            report = SeedReport(seeded=False, counts={})
        else:
            added = seed_starter(session)
            report = SeedReport(seeded=True, counts={"accounts": added})
        session.commit()
        _restore_basics(session)
    return report


def import_bytes(content: bytes, *, replace: bool = True) -> SeedReport:
    """Import an uploaded workbook (.xlsx)."""
    with SessionLocal() as session:
        return import_workbook(session, io.BytesIO(content), replace=replace)
