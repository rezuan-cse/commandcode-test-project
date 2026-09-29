"""Fresh-start and import operations for the books.

A deployment can start empty, from a standard starter chart of accounts, or from
the client's workbook — and an administrator can import a workbook or start over
at any time. All of it goes through here so the rules live in one place.
"""

from __future__ import annotations

import io

from app.core.config import settings
from app.core.db import SessionLocal, clear_all_data
from app.seed.loader import (
    SeedReport,
    ensure_demo_users,
    import_workbook,
    seed_if_empty,
)
from app.seed.starter import seed_starter


def _restore_basics(session) -> None:
    """Re-create the demo users and configuration after a wipe."""
    from app.modules.settings import service as settings_service

    settings_service.seed_defaults(session)
    ensure_demo_users(session)
    session.commit()


def reset(mode: str | None = None) -> SeedReport:
    """Empty every table and start again in the chosen mode.

    Modes: ``fresh`` (starter chart of accounts), ``workbook`` (the sample
    workbook), or ``none`` (leave the books empty).
    """
    chosen = mode or settings.seed_mode
    with SessionLocal() as session:
        clear_all_data(session)
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
