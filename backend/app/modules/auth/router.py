"""HTTP routes for authentication, the second factor, and account security."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.auth import service
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    DisableTwoFactorRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    SessionResponse,
    TotpEnableRequest,
    TotpEnableResponse,
    TotpLoginRequest,
    TotpSetupResponse,
    UserOut,
)
from app.modules.users_roles.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """Sign in with a password.

    Returns a session, or — when the account has 2FA — a challenge token that
    must be exchanged at ``/auth/login/totp``.
    """
    return service.login(db, payload)


@router.post("/login/totp", response_model=SessionResponse)
def login_totp(
    payload: TotpLoginRequest, db: Session = Depends(get_db)
) -> SessionResponse:
    """Complete sign-in with an authenticator code or a recovery code."""
    return service.complete_two_factor(db, payload.challenge_token, payload.code)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    """Return the signed-in user."""
    return UserOut.model_validate(user)


@router.post("/2fa/setup", response_model=TotpSetupResponse)
def setup_two_factor(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> TotpSetupResponse:
    """Begin enrolment: returns the secret and a QR code to scan."""
    return service.start_two_factor_setup(db, user)


@router.post("/2fa/enable", response_model=TotpEnableResponse)
def enable_two_factor(
    payload: TotpEnableRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TotpEnableResponse:
    """Confirm enrolment with a code. The recovery codes are returned once."""
    codes = service.enable_two_factor(db, user, payload.code)
    return TotpEnableResponse(
        recovery_codes=codes,
        message=(
            "Two-factor authentication is on. Save these recovery codes now — "
            "they are not shown again."
        ),
    )


@router.post("/2fa/disable", response_model=MessageResponse)
def disable_two_factor(
    payload: DisableTwoFactorRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Switch 2FA off. Requires the password."""
    service.disable_two_factor(db, user, payload.password)
    return MessageResponse(message="Two-factor authentication is off")


@router.post("/password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Change your own password."""
    service.change_password(db, user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed")
