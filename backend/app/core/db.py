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


def _type_signature(column_type: object) -> str:
    """A normalised description of a column type, for comparing model to database.

    Compiled to DDL and stripped of whitespace and case, because the two sides
    are produced by different code paths and differ cosmetically.
    """
    compiled = str(column_type.compile(dialect=engine.dialect)).upper()
    return compiled.replace(" ", "")


def detect_schema_drift() -> tuple[list[str], list[str]]:
    """Find columns where the database disagrees with the models.

    Returns two lists: columns whose type differs from the model, and columns
    that exist in the database but no model claims.

    Both are cases ``sync_schema`` cannot fix, and both used to pass unnoticed:

    * A **type mismatch** is the dangerous one. Widening a money column in the
      model, say from ``Numeric(18,4)`` to a larger precision, would leave the
      database on the old type and quietly truncate amounts rather than failing.
    * An **unclaimed column** usually means a rename went wrong: the new column
      was added empty while the old one kept the data, so the application reads
      blanks where the values still sit.
    """
    from sqlalchemy import inspect

    from app import models_registry  # noqa: F401

    inspector = inspect(engine)
    mismatched: list[str] = []
    unclaimed: list[str] = []

    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        actual = {column["name"]: column for column in inspector.get_columns(table.name)}

        for column in table.columns:
            found = actual.get(column.name)
            if found is None:
                continue
            if _type_signature(column.type) != _type_signature(found["type"]):
                mismatched.append(
                    f"{table.name}.{column.name}: model says "
                    f"{_type_signature(column.type)}, database has "
                    f"{_type_signature(found['type'])}"
                )

        claimed = {column.name for column in table.columns}
        for name in sorted(set(actual) - claimed):
            unclaimed.append(f"{table.name}.{name}")

    return mismatched, unclaimed


def sync_schema() -> list[str]:
    """Bring the schema up to date, and refuse to run if it cannot.

    ``create_all`` only creates tables that do not exist yet; it never alters
    one. Without this, the first schema change after a deployment would fail at
    request time with a missing-column error, which is exactly what happened
    when password and 2FA columns were introduced against a live database.

    That makes this **additive only**: it adds tables and columns, and does
    nothing else. No drops, no renames, no type changes, no backfills. The
    limits are real, so rather than let a change it cannot express pass in
    silence, it checks for drift and **stops** on a type mismatch — a narrowed
    money column would truncate amounts quietly, which is worse than a service
    that refuses to start.

    Columns the database holds that no model claims are reported but do not stop
    anything: they are a sign that something is not as expected, not a reason to
    be down.

    It remains a stopgap rather than a migration framework. The build
    specification calls for Alembic, which adds the history and the backfills
    this cannot do.
    """
    from sqlalchemy import inspect, text
    from sqlalchemy.schema import CreateColumn

    from app import models_registry  # noqa: F401

    Base.metadata.create_all(bind=engine)

    mismatched, unclaimed = detect_schema_drift()
    if mismatched:
        detail = "\n  ".join(mismatched)
        raise RuntimeError(
            "The database does not match the models, and this upgrade cannot "
            "change a column's type.\n  "
            f"{detail}\n"
            "Alter the column by hand, or introduce a migration. Starting with "
            "the wrong type would corrupt the data this column holds."
        )
    for name in unclaimed:
        print(
            f"[schema] warning: {name} exists in the database but no model claims "
            f"it. Left untouched; probably a leftover from a rename."
        )

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
