"""Administrative actions on user accounts.

Kept apart from ``service.py``, which is the permission matrix. This module is
about helping a colleague who cannot get in: clearing a second factor they have
lost the device for, or issuing a fresh password.

Every action here records an audit row. Clearing somebody's second factor lowers
the security of their account, so "who did this, and when" has to be answerable
afterwards.
"""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError, NotFoundError
from app.modules.auth import repository as auth_repository
from app.modules.auth import service as auth_service
from app.modules.users_roles.models import AdminAuditLog, User


def _target(db: Session, user_id: int) -> User:
    """Fetch the account an action is aimed at."""
    user = auth_repository.get_user(db, user_id)
    if user is None:
        raise NotFoundError(f"No user with id {user_id}")
    return user


def _refuse_self(actor: User, target: User, what: str, where: str) -> None:
    """Stop an administrator acting on their own account by mistake.

    Doing so is not a security hole — they are already signed in — but clearing
    your own second factor or password through an admin screen is far more likely
    to be a slip than an intention, and the screen is not the place for it.
    """
    if actor.id == target.id:
        raise DomainError(
            f"Use the {where} page to change {what} on your own account."
        )


def record(
    db: Session,
    actor: User,
    action: str,
    target: User,
    detail: str | None = None,
) -> None:
    """Append an audit row. Never updates an existing one."""
    db.add(
        AdminAuditLog(
            actor_id=actor.id,
            actor_email=actor.email,
            action=action,
            target_user_id=target.id,
            target_email=target.email,
            detail=detail,
        )
    )
    db.flush()


def reset_two_factor(db: Session, actor: User, user_id: int) -> str:
    """Clear a user's second factor so a password is enough again.

    Their recovery codes go too: they were issued for the old secret and are
    meaningless once it is gone. The user starts from scratch on the Security
    page, which requires proving a new authenticator works before it is trusted.
    """
    target = _target(db, user_id)
    _refuse_self(actor, target, "two-factor authentication", "Security")

    if not target.is_2fa_enabled and not target.totp_secret:
        raise DomainError(
            f"{target.full_name} does not have two-factor authentication enabled."
        )

    target.is_2fa_enabled = False
    target.totp_secret = None
    target.totp_confirmed_at = None
    for code in list(target.recovery_codes):
        db.delete(code)

    record(
        db,
        actor,
        "reset_two_factor",
        target,
        "Second factor cleared and recovery codes voided",
    )
    db.commit()
    return (
        f"Two-factor authentication cleared for {target.full_name}. "
        f"They can sign in with their password and set it up again."
    )


def reset_password(
    db: Session, actor: User, user_id: int, new_password: str | None = None
) -> str:
    """Issue a new password, returning it so the administrator can pass it on.

    It is shown once and not stored in readable form anywhere. It is not a forced
    change: the user can keep using it. Requiring a change at next sign-in is the
    tidier behaviour and is noted in the README as still to do.
    """
    target = _target(db, user_id)
    _refuse_self(actor, target, "your password", "Security")

    password = new_password or secrets.token_urlsafe(9)
    auth_service.set_user_password(db, target, password)
    record(
        db,
        actor,
        "reset_password",
        target,
        "Password reset by an administrator",
    )
    db.commit()
    return password


def set_active(db: Session, actor: User, user_id: int, is_active: bool) -> str:
    """Enable or disable an account.

    Disabling takes effect on the user's next request rather than when their
    token happens to expire, because the token dependency reloads the user.

    There is deliberately no "last administrator" check here. It would be
    unreachable: an administrator can only disable somebody else, and disabling
    one of two administrators always leaves one, so the count can never reach
    zero this way. The only route to zero would be disabling yourself, which is
    refused below. If a future change lets a role be reassigned, that check
    becomes necessary and should be added with the feature.
    """
    target = _target(db, user_id)

    if not is_active and target.id == actor.id:
        # There is no screen that disables your own account, so pointing at one
        # would be misleading.
        raise DomainError(
            "You cannot disable your own account. Ask another administrator to "
            "do it. This is also what stops the system being left with nobody "
            "able to administer it."
        )

    target.is_active = is_active
    record(
        db,
        actor,
        "enable_account" if is_active else "disable_account",
        target,
        f"Account {'enabled' if is_active else 'disabled'}",
    )
    db.commit()
    return f"{target.full_name} has been {'enabled' if is_active else 'disabled'}."


def recent_actions(db: Session, limit: int = 50) -> list[AdminAuditLog]:
    """The most recent administrative actions, newest first."""
    stmt = (
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
