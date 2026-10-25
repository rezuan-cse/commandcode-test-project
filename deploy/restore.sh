#!/bin/sh
# Restore a dump written by deploy/backup.sh.
#
#     deploy/restore.sh backups/rpci-20261031-0215.dump            # dry run: checks only
#     deploy/restore.sh backups/rpci-20261031-0215.dump --yes      # OVERWRITES the database
#
# **This replaces the live books.** Stop the application first, so nothing writes
# while the restore runs:
#
#     docker compose -f docker-compose.prod.yml stop app
#     deploy/restore.sh backups/… --yes
#     docker compose -f docker-compose.prod.yml start app
#
# Afterwards sign in and check the Dashboard: the trial-balance difference must
# read 0.0000 and the balances must be what you expect for that date.

set -eu

cd "$(dirname "$0")/.."

ARCHIVE="${1:-}"
CONFIRM="${2:-}"

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
    echo "Usage: deploy/restore.sh <archive.dump> [--yes]" >&2
    exit 1
fi

COMPOSE="docker compose -f docker-compose.prod.yml"
ENV_FILE="${ENV_FILE:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
    echo "No $ENV_FILE; run this from the repository root on the server." >&2
    exit 1
fi

# shellcheck disable=SC1090
. "./$ENV_FILE"
: "${POSTGRES_USER:?POSTGRES_USER missing from $ENV_FILE}"
: "${POSTGRES_DB:?POSTGRES_DB missing from $ENV_FILE}"

# The archive has to be readable inside the container, so it is piped in rather
# than mounted — that keeps working wherever the dump was written.
if [ "$CONFIRM" != "--yes" ]; then
    echo "Would restore $ARCHIVE over database '$POSTGRES_DB'."
    echo "Re-run with --yes to do it. Nothing has been changed."
    exit 0
fi

echo "Replacing '$POSTGRES_DB' from $ARCHIVE"
# --clean --if-exists drops what is there first, so the result is exactly the
# archive rather than the archive merged into whatever survived.
$COMPOSE exec -T db pg_restore \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" < "$ARCHIVE"

echo "Restored. Start the application and check the Dashboard."
