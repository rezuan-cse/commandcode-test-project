"""Request dependencies for authentication.

The role used for every permission check is now derived from a signed token
rather than a client-supplied header, so a caller cannot choose to be an
administrator by setting a request header.
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import DomainError
from app.core.security import read_token
from app.modules.users_roles.models import User

# auto_error=False so a missing token produces our own message and status
# rather than FastAPI's default, and so public routes can opt out cleanly.
_bearer = HTTPBearer(auto_error=False)


class NotAuthenticatedError(DomainError):
    """No usable session was presented."""

    status_code = 401


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the signed-in user from the bearer token.

    Raises 401 when the token is absent, malformed, expired, or belongs to a
    user who has since been disabled — so disabling an account takes effect on
    the next request rather than when the token happens to expire.
    """
    if credentials is None or not credentials.credentials:
        raise NotAuthenticatedError("Sign in to continue")

    claims = read_token(credentials.credentials)
    user = db.get(User, int(claims["sub"]))
    if user is None:
        raise NotAuthenticatedError("This account no longer exists")
    if not user.is_active:
        raise NotAuthenticatedError("This account has been disabled")
    return user


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the signed-in user when there is one, without requiring it."""
    if credentials is None or not credentials.credentials:
        return None
    try:
        claims = read_token(credentials.credentials)
    except DomainError:
        return None
    return db.get(User, int(claims["sub"]))
