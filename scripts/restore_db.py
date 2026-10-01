#!/usr/bin/env python3
"""Restore the database from an archive written by scripts/backup_db.py.

**This overwrites the current database.** It refuses to run without ``--yes``,
and it insists on a ``--scratch`` URL unless you say ``--yes`` — restoring into a
scratch database is how you prove a backup works without risking the live books.

    # Prove the archive (recommended first, and worth doing monthly)
    backend/.venv/bin/python scripts/restore_db.py backups/rpci-20261031-0200.dump \\
        --scratch postgresql://user:pw@host/scratch_db

    # Restore over the configured database — destructive, asks for --yes
    backend/.venv/bin/python scripts/restore_db.py backups/rpci-20261031-0200.dump --yes

Stop the application before restoring over the live database, so nothing is
writing while the restore runs.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402

from backup_db import _libpq_url, _sqlite_path  # noqa: E402


def _restore_sqlite(archive: Path, target: Path) -> None:
    if not shutil.which("sqlite3") and not target.exists():
        # The file has to exist for SQLite to open it; an empty one is fine.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    source = sqlite3.connect(f"file:{archive}?mode=ro", uri=True)
    try:
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()


def _restore_postgres(archive: Path, url: str) -> None:
    if shutil.which("pg_restore") is None:
        raise SystemExit(
            "pg_restore is not on PATH. Install the PostgreSQL client tools "
            "(Debian/Ubuntu: postgresql-client; macOS: brew install libpq)."
        )
    result = subprocess.run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            f"--dbname={_libpq_url(url)}",
            str(archive),
        ],
        capture_output=True,
        text=True,
    )
    # pg_restore reports the harmless DROP ... IF EXISTS notices on stderr and
    # still exits 0; anything else is a real failure.
    if result.returncode != 0:
        raise SystemExit(f"pg_restore failed:\n{result.stderr.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="the .dump or .db file to restore")
    parser.add_argument(
        "--scratch",
        default=None,
        help="restore into this database instead, to prove the archive works",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm overwriting the configured database",
    )
    args = parser.parse_args()

    archive = Path(args.archive).expanduser().resolve()
    if not archive.exists():
        raise SystemExit(f"No such archive: {archive}")

    if args.scratch:
        target_url = args.scratch
        print(f"Restoring {archive.name} into the scratch database.")
    else:
        target_url = settings.database_url
        if not args.yes:
            raise SystemExit(
                f"Refusing to overwrite {target_url} without --yes.\n"
                f"Prefer --scratch <url> first, to prove the archive restores."
            )
        print(f"Restoring {archive.name} over the configured database.")

    sqlite_file = _sqlite_path(target_url)
    if sqlite_file is not None:
        _restore_sqlite(archive, sqlite_file)
        print(f"Restored into {sqlite_file}")
    else:
        _restore_postgres(archive, target_url)
        print("Restored. Start the application and check the Dashboard.")

    print(
        "\nCheck the Dashboard: the trial balance difference must read 0.0000, "
        "and the account balances must match what you expect for that date."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
