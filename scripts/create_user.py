#!/usr/bin/env python3
"""Create the first administrator on a deployment that has no accounts.

A deployment holding real books is started with ``RPCI_SEED_DEMO_USERS`` off, so
it has no users at all — and nothing to sign in with. This makes the first one:

    backend/.venv/bin/python scripts/create_user.py \\
        --email admin@resinovabd.com --name "Md. Sarwar Hossain" --role admin

Pass ``--password`` to choose one; leave it out and a strong one is generated and
printed. Either way the password is shown once and stored only as a bcrypt hash,
so write it down before the terminal scrolls.

Every later account is better made from Roles & Access, where the role and the
individual menu grants are set together. This script exists for the
chicken-and-egg case of the very first sign-in, and for recovering access if the
last administrator is ever lost.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.db import SessionLocal, init_db  # noqa: E402
from app.core.enums import Role  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.modules.users_roles.models import User  # noqa: E402


def _role(value: str) -> Role:
    """Accept a role by name or by value, however it is written."""
    wanted = value.strip().lower().replace("-", "_").replace(" ", "_")
    for role in Role:
        if wanted in {role.name.lower(), str(role.value).lower()}:
            return role
    options = ", ".join(sorted(role.name.lower() for role in Role))
    raise SystemExit(f"Unknown role {value!r}. Choose one of: {options}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="sign-in address")
    parser.add_argument("--name", required=True, help="full name, shown in the app")
    parser.add_argument("--role", default="admin", help="role (default: admin)")
    parser.add_argument(
        "--password",
        default=None,
        help="choose the password; omit to have a strong one generated",
    )
    args = parser.parse_args()

    email = args.email.strip().lower()
    if "@" not in email:
        raise SystemExit(f"{email!r} does not look like an email address.")

    role = _role(args.role)
    generated = args.password is None
    password = args.password or secrets.token_urlsafe(12)

    init_db()
    with SessionLocal() as session:
        taken = (
            session.query(User).filter(User.email == email).one_or_none()
        )
        if taken is not None:
            raise SystemExit(
                f"{email} already exists (role {taken.role.value}). "
                f"Nothing was changed. Give it a new password from Roles & Access, "
                f"or reset it with --password if you have lost it."
            )

        session.add(
            User(
                email=email,
                full_name=args.name.strip(),
                role=role,
                password_hash=hash_password(password),
                is_active=True,
            )
        )
        session.commit()

    print(f"Created {email} ({args.name.strip()}, role {role.value}).")
    if generated:
        print(f"\n    Password: {password}\n")
        print("Shown once. Store it safely, then change it after signing in.")
    else:
        print("The password is the one you supplied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
