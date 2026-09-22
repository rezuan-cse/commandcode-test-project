"""Authentication: password sign-in, TOTP second factor, and account security.

The flow is deliberately two-step. A password alone yields a short-lived
*challenge* token that can only be exchanged for a code; only the code step
produces a session token. So a stolen password is not by itself enough to get in,
and a challenge token cannot be replayed as a session.
"""

from __future__ import annotations

import base64
import datetime as dt
import io

import pyotp
import qrcode
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import DomainError, NotFoundError
from app.core.security import (
    CHALLENGE_MINUTES,
    create_token,
    generate_recovery_codes,
    hash_password,
    hash_recovery_code,
    read_token,
    verify_password,
)
from app.modules.auth import repository
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    SessionResponse,
    TotpSetupResponse,
    UserOut,
)
from app.modules.users_roles.models import User

ISSUER = "RPCI ERP"


class AuthenticationError(DomainError):
    """Credentials were wrong, or the account cannot sign in."""

    status_code = 401


def _now() -> dt.datetime:
    """Current UTC time."""
    return dt.datetime.now(dt.timezone.utc)


def get_user(db: Session, user_id: int) -> User:
    """Fetch a user or raise :class:`NotFoundError`."""
    user = repository.get_user(db, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def list_users(db: Session) -> list[User]:
    """List every user, for the admin screen."""
    return repository.list_users(db)


def _session(db: Session, user: User) -> SessionResponse:
    """Issue a session token and record the sign-in time."""
    user.last_login_at = _now()
    db.commit()
    return SessionResponse(
        access_token=create_token(user.id, user.role.value),
        expires_in_minutes=settings.access_token_minutes,
        user=UserOut.model_validate(user),
    )


def login(db: Session, payload: LoginRequest) -> LoginResponse:
    """Verify a password and either sign the user in or ask for their code.

    The same message is returned whether the email is unknown or the password is
    wrong, so the endpoint cannot be used to discover which accounts exist.
    """
    user = repository.get_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Email or password is incorrect")
    if not user.is_active:
        raise AuthenticationError("This account has been disabled")

    if user.is_2fa_enabled and user.totp_secret:
        return LoginResponse(
            needs_2fa=True,
            challenge_token=create_token(
                user.id,
                user.role.value,
                purpose="2fa_challenge",
                expires_minutes=CHALLENGE_MINUTES,
            ),
        )
    return LoginResponse(needs_2fa=False, **(_session(db, user).model_dump()))


def _code_is_valid(db: Session, user: User, code: str) -> bool:
    """Accept a current authenticator code, or consume a recovery code.

    The authenticator is tried first, then recovery. Trying both rather than
    branching on the shape of the input avoids an edge case where a recovery
    code happens to be all digits and would be rejected as a bad TOTP code.
    """
    if user.totp_secret and len(code) == 6 and code.isdigit():
        # valid_window=1 tolerates one step of clock drift in either direction,
        # which is normal between a phone and a server.
        if pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
            return True

    found = repository.find_recovery_code(db, user, hash_recovery_code(code))
    if found is None:
        return False
    repository.mark_recovery_code_used(found)
    return True


def complete_two_factor(db: Session, challenge_token: str, code: str) -> SessionResponse:
    """Exchange a challenge token plus a code for a session."""
    claims = read_token(challenge_token, purpose="2fa_challenge")
    user = get_user(db, int(claims["sub"]))
    if not user.is_active:
        raise AuthenticationError("This account has been disabled")

    if not _code_is_valid(db, user, code.strip().replace(" ", "")):
        raise AuthenticationError("That code is not valid")
    return _session(db, user)


def start_two_factor_setup(db: Session, user: User) -> TotpSetupResponse:
    """Generate a new secret and the enrolment QR code.

    The secret is stored immediately but is not trusted until a code from the
    authenticator confirms it — see :func:`enable_two_factor`.
    """
    secret = pyotp.random_base32()
    user.totp_secret = secret
    user.is_2fa_enabled = False
    db.commit()

    uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=ISSUER)
    return TotpSetupResponse(
        secret=secret,
        otpauth_uri=uri,
        qr_png_data_uri=_qr_data_uri(uri),
    )


def _qr_data_uri(text: str) -> str:
    """Render the enrolment URI as a PNG data URI the browser can display."""
    image = qrcode.make(text)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def enable_two_factor(db: Session, user: User, code: str) -> list[str]:
    """Switch 2FA on once a code proves the authenticator works, and issue codes."""
    if not user.totp_secret:
        raise DomainError("Start the setup before enabling two-factor authentication")
    if not pyotp.TOTP(user.totp_secret).verify(code.strip(), valid_window=1):
        raise AuthenticationError("That code is not valid; check the time on your device")

    codes = generate_recovery_codes()
    repository.replace_recovery_codes(db, user, [hash_recovery_code(c) for c in codes])
    user.is_2fa_enabled = True
    user.totp_confirmed_at = _now()
    db.commit()
    return codes


def disable_two_factor(db: Session, user: User, password: str) -> None:
    """Switch 2FA off. Requires the password, not merely a live session."""
    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Password is incorrect")
    user.is_2fa_enabled = False
    user.totp_secret = None
    user.totp_confirmed_at = None
    repository.replace_recovery_codes(db, user, [])
    db.commit()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    """Change the signed-in user's own password."""
    if not verify_password(current, user.password_hash):
        raise AuthenticationError("Current password is incorrect")
    if verify_password(new, user.password_hash):
        raise DomainError("The new password must be different from the current one")
    repository.set_password(db, user, hash_password(new))
    db.commit()


def set_user_password(db: Session, user: User, password: str) -> None:
    """Set a user's password, used when seeding and by an administrator."""
    repository.set_password(db, user, hash_password(password))
