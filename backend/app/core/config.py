"""Application configuration loaded from environment variables.

All tunable values (database location, demo password, workbook path) live here
so nothing is hardcoded in business logic.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime settings for the RPCI demo backend."""

    model_config = SettingsConfigDict(env_prefix="RPCI_", extra="ignore")

    database_url: str = f"sqlite:///{PROJECT_ROOT / 'rpci_demo.db'}"
    demo_password: str = "rpci"
    seed_from_excel_path: str = str(PROJECT_ROOT / "RPCI Accounts.xlsx")
    # What a brand-new, empty database starts with:
    #   fresh    - a standard starter chart of accounts, no balances (default)
    #   workbook - the client's sample workbook
    #   none     - nothing; the books stay empty until data is entered or imported
    seed_mode: str = "fresh"
    default_segment: str = "Shared"
    # Timestamps are stored in UTC and shown at this offset from it. Bangladesh is
    # a fixed +06:00 with no daylight saving, so an offset is exact here.
    utc_offset_hours: int = 6
    # When the interface is hosted on a different origin (Vercel, Netlify) the
    # browser needs permission to call this API. "*" is fine for a public demo
    # because no cookies are used; narrow it to the exact site if preferred.
    cors_origins: str = "*"
    # Allow an administrator to empty the books and start over from
    # Administration → Data. Disable this on a deployment where the data must
    # never be lost.
    allow_data_reset: bool = True
    # Session signing key. Leave unset and a random one is generated per process,
    # which works locally but signs everybody out on restart. Set it on any real
    # deployment. Generate one with: python -c "import secrets;
    # print(secrets.token_urlsafe(48))"
    jwt_secret: str = ""
    # How long a signed-in session lasts before the user must sign in again.
    access_token_minutes: int = 720

    @field_validator("seed_mode", mode="after")
    @classmethod
    def normalise_seed_mode(cls, value: str) -> str:
        """Accept only the three known modes; anything else means the default."""
        return value if value in {"fresh", "workbook", "none"} else "fresh"

    @field_validator("database_url", mode="after")
    @classmethod
    def route_postgres_to_psycopg(cls, value: str) -> str:
        """Accept a plain Postgres URL and route it to the psycopg 3 driver.

        Hosted providers hand out ``postgresql://…`` or ``postgres://…``, which
        SQLAlchemy would send to psycopg2. Only psycopg 3 is installed, so the
        URL is rewritten here. A pasted connection string then works unchanged.
        """
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value


settings = Settings()

