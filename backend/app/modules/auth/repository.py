"""Database queries for authentication."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.users_roles.models import RecoveryCode, User


def get_user(db: Session, user_id: int) -> User | None:
    """Fetch a user by primary key."""
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    """Find a user by email address, ignoring case and surrounding spaces."""
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return db.execute(stmt).scalar_one_or_none()


def list_users(db: Session) -> list[User]:
    """List every user, ordered by id."""
    return list(db.execute(select(User).order_by(User.id)).scalars().all())


def set_password(db: Session, user: User, password_hash: str) -> None:
    """Store a new password hash."""
    user.password_hash = password_hash
    db.flush()


def find_recovery_code(db: Session, user: User, code_hash: str) -> RecoveryCode | None:
    """Find an unused recovery code by its hash."""
    stmt = select(RecoveryCode).where(
        RecoveryCode.user_id == user.id,
        RecoveryCode.code_hash == code_hash,
        RecoveryCode.used_at.is_(None),
    )
    return db.execute(stmt).scalars().first()


def replace_recovery_codes(db: Session, user: User, code_hashes: list[str]) -> None:
    """Replace all of a user's recovery codes with a fresh set."""
    for existing in list(user.recovery_codes):
        db.delete(existing)
    db.flush()
    for code_hash in code_hashes:
        db.add(RecoveryCode(user_id=user.id, code_hash=code_hash))
    db.flush()


def mark_recovery_code_used(code: RecoveryCode) -> None:
    """Consume a recovery code so it cannot be reused."""
    code.used_at = dt.datetime.now(dt.timezone.utc)
