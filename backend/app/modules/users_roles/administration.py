"""Administrative actions on user accounts.

Kept apart from ``service.py``, which is the permission matrix. This module is
about looking after accounts: adding a colleague, correcting their details,
issuing a password, clearing a second factor they have lost the device for, or
granting them an area their role does not cover.

Every action here records an audit row. Clearing somebody's second factor lowers
the security of their account, so "who did this, and when" has to be answerable
afterwards.
"""

from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.core.exceptions import DomainError, DuplicateError, NotFoundError
from app.modules.auth import repository as auth_repository
from app.modules.auth import service as auth_service
from app.modules.users_roles import service as permissions_service
from app.modules.users_roles.models import AdminAuditLog, User
from app.modules.users_roles.schemas import PermissionsUpdate, UserCreate, UserUpdate
from app.modules.users_roles.service import Access, RESOURCES


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


def _assert_not_last_admin(db: Session, target: User) -> None:
    """Refuse a change that would leave the system with no administrator.

    Only triggered when the person being changed is the one remaining Admin, so
    an ordinary edit is never blocked by it.
    """
    if target.role != Role.ADMIN:
        return
    admins = db.execute(
        select(func.count()).select_from(User).where(User.role == Role.ADMIN)
    ).scalar_one()
    if admins <= 1:
        raise DomainError(
            "This is the only administrator. Give somebody else the Admin role "
            "before changing or removing this account."
        )


def create_user(
    db: Session, actor: User, payload: UserCreate
) -> tuple[User, str | None]:
    """Add an account, returning it and any password that was generated.

    A password given here is the administrator's choice and is not echoed back. A
    generated one is returned once so it can be handed over; it is stored only as
    a hash.
    """
    email = payload.email.strip().lower()
    if auth_repository.get_by_email(db, email) is not None:
        raise DuplicateError(f"An account already exists for {email}.")

    user = User(
        email=email, full_name=payload.full_name.strip(), role=payload.role
    )
    db.add(user)
    db.flush()

    password = payload.password or secrets.token_urlsafe(9)
    auth_service.set_user_password(db, user, password)

    record(
        db,
        actor,
        "create_user",
        user,
        f"Created with the {payload.role.value} role",
    )
    db.commit()
    return user, (None if payload.password else password)


def update_user(db: Session, actor: User, user_id: int, payload: UserUpdate) -> User:
    """Change an account's name, email or role.

    An administrator cannot change their **own** role: demoting themselves would
    lock them out of the very screen they are standing on, and there is no way
    back in.
    """
    target = _target(db, user_id)
    changes: list[str] = []

    if payload.email is not None:
        email = payload.email.strip().lower()
        if email != target.email:
            existing = auth_repository.get_by_email(db, email)
            if existing is not None and existing.id != target.id:
                raise DuplicateError(f"An account already exists for {email}.")
            target.email = email
            changes.append(f"email set to {email}")

    if payload.full_name is not None and payload.full_name.strip() != target.full_name:
        target.full_name = payload.full_name.strip()
        changes.append("name changed")

    if payload.role is not None and payload.role != target.role:
        if target.id == actor.id:
            raise DomainError(
                "You cannot change your own role. Ask another administrator to do "
                "it — demoting yourself would lock you out of this screen."
            )
        _assert_not_last_admin(db, target)
        changes.append(f"role {target.role.value} → {payload.role.value}")
        target.role = payload.role

    if not changes:
        return target

    record(db, actor, "update_user", target, "; ".join(changes))
    db.commit()
    return target


def delete_user(db: Session, actor: User, user_id: int) -> str:
    """Remove an account. Their second factor and access grants go with it.

    The audit trail keeps the address as text, so the record of who did what
    survives the account it refers to. Posted transactions are untouched: they
    carry the name of whoever entered them as plain text, not a link.
    """
    target = _target(db, user_id)
    if target.id == actor.id:
        raise DomainError(
            "You cannot delete your own account. Ask another administrator to do "
            "it."
        )
    _assert_not_last_admin(db, target)

    name = target.full_name
    record(db, actor, "delete_user", target, f"Deleted the {target.role.value} account")
    db.delete(target)
    db.commit()
    return f"{name} has been deleted."


def user_permissions(db: Session, user_id: int) -> dict[str, object]:
    """What one person may do: their role's default, their grants, and the result."""
    target = _target(db, user_id)
    overrides = permissions_service.overrides_for(db, target)
    return {
        "user_id": target.id,
        "role": target.role,
        "resources": RESOURCES,
        "role_defaults": permissions_service.permissions_for(target.role),
        "overrides": {key: level.value for key, level in overrides.items()},
        "effective": permissions_service.permissions_for_user(db, target),
    }


def set_user_permissions(
    db: Session, actor: User, user_id: int, payload: PermissionsUpdate
) -> None:
    """Grant or deny one person areas, on top of their role.

    An administrator cannot change their own access, for the same reason they
    cannot change their own role: a slip would lock them out of this screen.
    """
    target = _target(db, user_id)
    if target.id == actor.id:
        raise DomainError(
            "You cannot change your own access, in case you lock yourself out of "
            "this screen. Ask another administrator to do it."
        )

    desired: dict[str, Access] = {}
    for resource, level in payload.access.items():
        if resource not in RESOURCES:
            raise DomainError(f"Unknown area: {resource}")
        try:
            desired[resource] = Access(level)
        except ValueError:
            raise DomainError(
                f"{resource} must be one of: none, view, full"
            ) from None

    permissions_service.set_overrides(db, target, desired)

    granted = sorted(
        resource
        for resource, level in desired.items()
        if level != permissions_service.access_for(target.role, resource)
    )
    record(
        db,
        actor,
        "set_permissions",
        target,
        "Access set to the role default"
        if not granted
        else "Different from the role for: " + ", ".join(granted),
    )
    db.commit()


def recent_actions(db: Session, limit: int = 50) -> list[AdminAuditLog]:
    """The most recent administrative actions, newest first."""
    stmt = (
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())
