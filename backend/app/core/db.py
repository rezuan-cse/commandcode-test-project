"""Database engine, session factory, and declarative base.

The demo uses SQLite for zero-ops hosting. Money columns are SQLAlchemy
``Numeric`` values and are read back as :class:`decimal.Decimal` so no float
math ever touches the ledger.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import Enum as SAEnum
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Declarative base shared by every module's models."""


def enum_col(enum_cls: type, length: int = 32) -> SAEnum:
    """Build an enum column that stores the readable value rather than the name.

    Storing values keeps the demo database legible (``Manufacturing`` rather than
    ``MANUFACTURING``) and matches the strings used in the client's workbook.
    """
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda enum_type: [member.value for member in enum_type],
    )


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Bring the database schema up to date. Imports models so they register."""
    for change in sync_schema():
        print(f"[schema] added {change}")


def sync_schema() -> list[str]:
    """Create missing tables and add missing columns, returning what changed.

    ``create_all`` only creates tables that do not exist yet; it never alters
    one. Without this, the first schema change after a deployment would fail at
    request time with a missing-column error, which is exactly what happened
    when password and 2FA columns were introduced against a live database.

    This is deliberately **additive only**. It adds tables and columns and does
    nothing else: no drops, no renames, no type changes, no data backfill. A
    column that is NOT NULL and has no server default cannot be added to a table
    that already holds rows, so that case raises rather than guessing a value.

    It is a stopgap, not a migration framework. The build specification calls
    for Alembic, and that is the right long-term answer once the schema starts
    changing in ways this cannot express.
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.schema import CreateColumn

    from app import models_registry  # noqa: F401

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    applied: list[str] = []

    for table in Base.metadata.sorted_tables:
        present = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            if not column.nullable and column.server_default is None:
                raise RuntimeError(
                    f"Cannot add required column {table.name}.{column.name} to an "
                    f"existing table. Give it a server_default, or migrate by hand."
                )
            ddl = str(CreateColumn(column).compile(dialect=engine.dialect))
            with engine.begin() as connection:
                connection.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {ddl}"))
            applied.append(f"{table.name}.{column.name}")

    return applied


def clear_all_data(session: Session) -> None:
    """Delete every row, children before parents.

    Deliberately not DROP TABLE. Dropping needs an exclusive lock on each table,
    so on Postgres it blocks behind any other session holding a read lock — which
    the running application always has. Plain DELETE takes only a row lock, which
    is compatible with readers, and it works identically on SQLite.

    Table order comes from the metadata's dependency sort, reversed, so foreign
    keys are never violated and the helper needs no maintenance when models are
    added.
    """
    from app import models_registry  # noqa: F401

    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.flush()
