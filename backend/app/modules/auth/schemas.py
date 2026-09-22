"""Pydantic schemas for authentication and the second factor."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.modules.users_roles.schemas import UserOut

__all__ = [
    "ChangePasswordRequest",
    "DisableTwoFactorRequest",
    "LoginRequest",
    "LoginResponse",
    "MessageResponse",
    "SessionResponse",
    "TotpEnableRequest",
    "TotpEnableResponse",
    "TotpLoginRequest",
    "TotpSetupResponse",
    "UserOut",
]


class LoginRequest(BaseModel):
    """Step one: who you are."""

    email: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    """Either a session, or a request for the second factor.

    ``needs_2fa`` decides which. When it is true, ``access_token`` is absent and
    ``challenge_token`` must be presented with a code instead — the challenge
    token cannot be used as a session.
    """

    needs_2fa: bool
    challenge_token: str | None = None
    access_token: str | None = None
    expires_in_minutes: int | None = None
    user: UserOut | None = None


class TotpLoginRequest(BaseModel):
    """Step two: the six-digit code, or a recovery code."""

    challenge_token: str
    code: str = Field(min_length=6, max_length=32)


class TotpSetupResponse(BaseModel):
    """Enrolment details for an authenticator app."""

    secret: str
    otpauth_uri: str
    qr_png_data_uri: str


class TotpEnableRequest(BaseModel):
    """Confirm enrolment by proving the app produces the right code."""

    code: str = Field(min_length=6, max_length=6)


class TotpEnableResponse(BaseModel):
    """Recovery codes, shown exactly once."""

    recovery_codes: list[str]
    message: str


class DisableTwoFactorRequest(BaseModel):
    """Turning 2FA off requires the password, not just a session."""

    password: str = Field(min_length=1, max_length=200)


class ChangePasswordRequest(BaseModel):
    """Change your own password."""

    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class MessageResponse(BaseModel):
    """A plain result message."""

    message: str


class SessionResponse(BaseModel):
    """A freshly issued session."""

    access_token: str
    expires_in_minutes: int
    user: UserOut


# Re-exported for the frontend's sake: EmailStr is not used above because the
# seeded demo addresses are not real mailboxes, but keeping the import makes the
# intended shape obvious if stricter validation is wanted later.
__all__ = [
    "ChangePasswordRequest",
    "DisableTwoFactorRequest",
    "EmailStr",
    "LoginRequest",
    "LoginResponse",
    "MessageResponse",
    "SessionResponse",
    "TotpEnableRequest",
    "TotpEnableResponse",
    "TotpLoginRequest",
    "TotpSetupResponse",
    "UserOut",
]
