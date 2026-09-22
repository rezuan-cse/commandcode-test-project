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
    """Create all tables. Imports models so they register on the metadata."""
    from app import models_registry  # noqa: F401

    Base.metadata.create_all(bind=engine)


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
