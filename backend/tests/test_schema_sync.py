"""Schema upgrades against a database that already holds data.

A live deployment is not a fresh database. ``create_all`` creates missing tables
but never alters an existing one, so without an additive sync the first schema
change after a deployment fails at request time with a missing-column error.
That is what happened when the password and 2FA columns were added, so these
tests pin the behaviour down.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from app.core.db import engine, init_db, sync_schema


def test_sync_is_a_no_op_when_the_schema_is_current(db) -> None:
    """Running it on an up-to-date database changes nothing."""
    assert sync_schema() == []


def test_init_db_can_run_repeatedly(db) -> None:
    """Startup may call it on every boot, so it must be safe to repeat."""
    init_db()
    init_db()


def test_a_missing_column_is_added_and_data_is_kept(db) -> None:
    """Dropping a column and syncing restores it without losing the row.

    This mirrors the real upgrade: an existing users table gained six columns
    with the rows already in place.
    """
    db.execute(
        text(
            "INSERT INTO users (email, full_name, role, is_active) "
            "VALUES ('existing@rpci.demo', 'Existing Row', 'Admin', TRUE)"
        )
    )
    db.commit()

    # Take the column away to recreate the older schema.
    db.execute(text("ALTER TABLE users DROP COLUMN last_login_at"))
    db.commit()
    assert "last_login_at" not in {
        column["name"] for column in inspect(engine).get_columns("users")
    }

    applied = sync_schema()
    assert "users.last_login_at" in applied

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert "last_login_at" in columns

    # The row that predates the change is still there.
    remaining = db.execute(
        text("SELECT count(*) FROM users WHERE email = 'existing@rpci.demo'")
    ).scalar_one()
    assert remaining == 1


def test_a_missing_table_is_created(db) -> None:
    """Tables introduced later appear on an existing database."""
    db.execute(text("DROP TABLE recovery_codes"))
    db.commit()
    assert "recovery_codes" not in inspect(engine).get_table_names()

    sync_schema()

    assert "recovery_codes" in inspect(engine).get_table_names()


def test_a_required_column_without_a_default_is_refused(db, monkeypatch) -> None:
    """Rather than guess a value, the sync raises and says what to do.

    Silently inventing data for a NOT NULL column on a populated table would be
    worse than stopping.
    """
    import app.core.db as db_module

    # Pretend a model gained a required column with no server default.
    users = db_module.Base.metadata.tables["users"]
    from sqlalchemy import Column, String

    users.append_column(Column("cannot_guess", String(10), nullable=False))
    try:
        with pytest.raises(RuntimeError, match="cannot_guess"):
            sync_schema()
    finally:
        users._columns.remove(users.c.cannot_guess)
