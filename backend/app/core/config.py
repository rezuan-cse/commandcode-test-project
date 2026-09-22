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
    auto_seed: bool = True
    default_segment: str = "Shared"
    # When the interface is hosted on a different origin (Vercel, Netlify) the
    # browser needs permission to call this API. "*" is fine for a public demo
    # because no cookies are used; narrow it to the exact site if preferred.
    cors_origins: str = "*"
    # Allow a visitor to wipe and re-seed the demo from the interface. Disable
    # this if the data must be preserved.
    allow_demo_reset: bool = True

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

