"""The startup database description must name the database without leaking secrets."""

from __future__ import annotations

from app.core.config import settings
from app.core.db import describe_database


def test_it_names_a_hosted_postgres_without_the_password(monkeypatch) -> None:
    """The log line says which Postgres is in use, never the password."""
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+psycopg://books_user:sup3r-secret@ep-example-1.neon.tech/books?sslmode=require",
    )
    described = describe_database()

    assert "sup3r-secret" not in described
    assert "postgresql" in described
    assert "books" in described
    assert "ep-example-1.neon.tech" in described


def test_it_names_a_sqlite_file(monkeypatch) -> None:
    """A sqlite path is shown as-is, so an ephemeral file is obvious in the log."""
    monkeypatch.setattr(settings, "database_url", "sqlite:////data/rpci_demo.db")
    assert describe_database() == "sqlite file /data/rpci_demo.db"
