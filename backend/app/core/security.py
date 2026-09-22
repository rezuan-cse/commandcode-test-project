"""Password hashing and JWT issuing/verification.

Two separate concerns kept in one place so nothing else in the codebase reaches
for a crypto primitive directly:

* Passwords are hashed with bcrypt. The plaintext is never stored, never logged,
  and never leaves the request that supplied it.
* Sessions are JWTs signed with a server secret. The token carries the user id
  and role, so permission checks no longer need to trust a client-supplied
  header.

The secret is read from RPCI_JWT_SECRET. If it is not set, a random one is
generated at process start: that keeps local development frictionless and means
there is never a guessable default in the code, at the cost of invalidating
sessions whenever the process restarts. Set the variable on any real deployment
so logins survive a redeploy.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import secrets
from typing import Any

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import DomainError

ALGORITHM = "HS256"
# A short-lived token handed out between the password step and the 2FA step.
CHALLENGE_MINUTES = 5

# Used only when RPCI_JWT_SECRET is unset. Random per process, so it cannot be
# guessed from the source, but sessions end when the process does.
_EPHEMERAL_SECRET = secrets.token_urlsafe(48)


class TokenError(DomainError):
    """A token was missing, malformed, expired, or signed with the wrong key."""

    status_code = 401


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    """Check a plaintext password against its stored hash.

    Returns False rather than raising when the user has no password set, so a
    half-provisioned account cannot be logged into by accident.
    """
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        # A malformed hash in the database should read as "wrong password",
        # never as a crash that reveals which accounts exist.
        return False


def _secret() -> str:
    """Return the signing secret, falling back to a per-process random one."""
    return settings.jwt_secret or _EPHEMERAL_SECRET


def using_ephemeral_secret() -> bool:
    """True when no secret is configured, so callers can warn at startup."""
    return not settings.jwt_secret


def create_token(
    subject: str | int,
    role: str,
    *,
    purpose: str = "access",
    expires_minutes: int | None = None,
) -> str:
    """Sign a token for a user.

    ``purpose`` distinguishes a fully authenticated session ("access") from the
    half-finished state between supplying a password and supplying a 2FA code
    ("2fa_challenge"), so a challenge token can never be used as a session.
    """
    minutes = expires_minutes or settings.access_token_minutes
    issued = dt.datetime.now(dt.timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "purpose": purpose,
        "iat": int(issued.timestamp()),
        "exp": int((issued + dt.timedelta(minutes=minutes)).timestamp()),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def read_token(token: str, *, purpose: str = "access") -> dict[str, Any]:
    """Verify a token and return its claims, or raise :class:`TokenError`."""
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session has expired; sign in again") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid session token") from exc

    if claims.get("purpose") != purpose:
        raise TokenError("This token cannot be used here")
    return claims


def new_secret() -> str:
    """Generate a secret suitable for RPCI_JWT_SECRET."""
    return secrets.token_urlsafe(48)


def generate_recovery_codes(count: int = 8) -> list[str]:
    """Generate one-time recovery codes, shown to the user exactly once."""
    return [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}" for _ in range(count)]


def hash_recovery_code(code: str) -> str:
    """Hash a recovery code for storage.

    SHA-256 rather than bcrypt here, deliberately. These are machine-generated
    with 48 bits of entropy, not chosen by a person, so there is no dictionary to
    attack and no reason to pay bcrypt's cost on every login attempt. It also
    lets a code be looked up by hash instead of comparing against each unused
    code in turn, which would mean eight bcrypt rounds per attempt.
    """
    normalised = code.strip().lower().replace(" ", "")
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()
