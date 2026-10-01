#!/usr/bin/env python3
"""Back the database up to a single dated file.

Deliberately portable: it backs up whatever ``RPCI_DATABASE_URL`` points at, on
any host, cloud or on-prem, with no provider-specific service involved.

* **Postgres** — ``pg_dump`` in custom format, compressed, which ``pg_restore``
  rebuilds exactly (indexes, constraints and all).
* **SQLite** — a copy taken through SQLite's own backup API, which is consistent
  even while the application is serving.

    backend/.venv/bin/python scripts/backup_db.py
    backend/.venv/bin/python scripts/backup_db.py --out /mnt/backups --keep 30

**Run it every night.** These are the client's books; a hosted free tier usually
has no automated backup of its own, and a backup that has never been restored is
a guess. Restore one into a scratch database at least once, to prove it works.

A sensible schedule on any host:

* nightly, keeping 30 days;
* before every upgrade;
* before an import or a data reset, which are the two operations that replace
  what is there.

On Linux/macOS a cron entry or a systemd timer runs it; on Windows, Task
Scheduler. Keeping the output off the machine that runs the database is the
point — a backup beside the database is lost with the database.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import settings  # noqa: E402


def _sqlite_path(url: str) -> Path | None:
    """The database file behind a SQLite URL, or None if it is not SQLite."""
    if not url.startswith("sqlite"):
        return None
    _, _, raw = url.partition(":///")
    return Path(raw)


def _libpq_url(url: str) -> str:
    """A URL libpq (pg_dump/pg_restore) understands.

    SQLAlchemy addresses the psycopg 3 driver explicitly; the command-line tools
    want the plain scheme.
    """
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix) :]
    return url


def _stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _prune(out_dir: Path, keep: int) -> list[Path]:
    """Delete the oldest archives beyond ``keep``, newest first."""
    archives = sorted(out_dir.glob("rpci-*"), key=lambda p: p.stat().st_mtime)
    removed = archives[:-keep] if keep > 0 else []
    for path in removed:
        path.unlink()
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "backups"),
        help="directory to write into (default: ./backups)",
    )
    parser.add_argument(
        "--keep", type=int, default=30, help="how many archives to retain"
    )
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    url = settings.database_url
    sqlite_file = _sqlite_path(url)

    if sqlite_file is not None:
        if not sqlite_file.exists():
            raise SystemExit(f"No database file at {sqlite_file}; nothing to back up.")
        target = out_dir / f"rpci-{_stamp()}.db"
        source = sqlite3.connect(f"file:{sqlite_file}?mode=ro", uri=True)
        try:
            destination = sqlite3.connect(target)
            try:
                source.backup(destination)
            finally:
                destination.close()
        finally:
            source.close()
    else:
        if shutil.which("pg_dump") is None:
            raise SystemExit(
                "pg_dump is not on PATH. Install the PostgreSQL client tools "
                "(Debian/Ubuntu: postgresql-client; macOS: brew install "
                "libpq), then run this again."
            )
        target = out_dir / f"rpci-{_stamp()}.dump"
        result = subprocess.run(
            [
                "pg_dump",
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                f"--file={target}",
                _libpq_url(url),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit(f"pg_dump failed:\n{result.stderr.strip()}")

    size_mb = target.stat().st_size / (1024 * 1024)
    print(f"Wrote {target}  ({size_mb:.2f} MB)")

    for removed in _prune(out_dir, args.keep):
        print(f"Removed old archive {removed.name}")

    print(
        "\nRestore it with scripts/restore_db.py. Test a restore into a scratch "
        "database before relying on this."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
