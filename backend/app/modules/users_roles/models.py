"""User and authentication models.

Identity lives in one place: the user record, the second-factor secret, and the
recovery codes. The :mod:`app.modules.auth` module owns the behaviour that uses
them, but the schema stays together so it can be read as a whole.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    false,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, enum_col
from app.core.enums import Role


class User(Base):
    """A system user with exactly one role."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[Role] = mapped_column(enum_col(Role), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    # Nullable so a user record can exist before a password is issued, and so an
    # account can be disabled by clearing it. Never returned by the API.
    password_hash: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Second factor. The secret is only set once enrolment starts; it is not
    # trusted until is_2fa_enabled is true, which requires a verified code.
    totp_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # The server default matters for schema upgrades: an existing table can only
    # gain a NOT NULL column if the database knows what to put in existing rows.
    is_2fa_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    totp_confirmed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    last_login_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    # Sign-in throttling, so a password cannot be guessed by brute force. A wrong
    # password counts up; at the limit the account locks until ``locked_until``
    # passes. Held in the database rather than in memory, so restarting the
    # service does not clear a lock.
    #
    # Times here are naive UTC on purpose: a DateTime column with no time zone
    # gives back a naive value, and comparing a naive value against an aware one
    # raises. The rest of the system formats aware UTC for display; this is the
    # one place a stored time is compared.
    failed_logins: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    locked_until: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    # When the row was last altered, so the admin screen can show it.
    #
    # Deliberately nullable, and with no DDL default: the schema sync adds columns
    # with ALTER TABLE, and SQLite refuses to add a column whose default is a
    # non-constant expression such as now(). The default is applied by the ORM on
    # insert and on update instead, so the column needs neither. Accounts that
    # existed before this column show "—" until they are next changed.
    updated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=True
    )

    recovery_codes: Mapped[list["RecoveryCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    permission_overrides: Mapped[list["UserPermission"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def has_password(self) -> bool:
        """True when the account can be signed into with a password."""
        return bool(self.password_hash)


class UserPermission(Base):
    """One person's access to one area, where it differs from their role.

    The role supplies the default. A row here records only the exception an
    administrator has granted or denied, so a change to the permission matrix
    still flows through to everybody who has not been singled out.

    A row is removed when the access is set back to what the role already gives,
    which keeps "no row" meaning "follow the role".
    """

    __tablename__ = "user_permissions"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    resource: Mapped[str] = mapped_column(String(40), primary_key=True)
    # "none", "view" or "full", matching users_roles.service.Access.
    access: Mapped[str] = mapped_column(String(8), nullable=False)

    user: Mapped[User] = relationship(back_populates="permission_overrides")


class RecoveryCode(Base):
    """A single-use code that bypasses 2FA when the authenticator is lost.

    Stored hashed, like a password. A user who loses their phone is otherwise
    locked out permanently, so these are not optional.
    """

    __tablename__ = "recovery_codes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(120), nullable=False)
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="recovery_codes")


class AdminAuditLog(Base):
    """A record of a security-relevant action taken by an administrator.

    Clearing somebody's second factor or issuing them a new password is exactly
    the kind of action that needs to be answerable later — "who reset this, and
    when?". Rows are append-only: nothing in the application updates or deletes
    them.
    """

    __tablename__ = "admin_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_email: Mapped[str] = mapped_column(String(160), nullable=False)
    action: Mapped[str] = mapped_column(String(48), nullable=False, index=True)
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Kept as text so the record survives the account being renamed or removed.
    target_email: Mapped[str] = mapped_column(String(160), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
