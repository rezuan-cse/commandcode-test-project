#!/bin/sh
# Nightly database backup for the VPS deployment.
#
#     deploy/backup.sh               # write a dump and prune older ones
#     BACKUP_DIR=/mnt/usb deploy/backup.sh
#
# Run it from cron on the host, as root or a user in the `docker` group:
#
#     # 02:15 every night, log to a file and to syslog on failure
#     15 2 * * *  cd /opt/rpci && ./deploy/backup.sh >> /var/log/rpci-backup.log 2>&1
#
# WHY THIS EXISTS SEPARATELY FROM scripts/backup_db.py: that script runs pg_dump
# from PATH, and the host has no PostgreSQL client installed — only the `db`
# container has one. So the dump runs inside the container and is copied out.
#
# **KEEP THE OUTPUT OFF THIS MACHINE.** A backup beside the database is lost with
# the database. Set BACKUP_DIR to a mounted drive, or sync the directory to
# somewhere else (rclone, rsync, a storage box) in a second cron entry.
#
# And restore one, once, before you need it:
#     deploy/restore.sh backups/rpci-20261031-0215.dump      (add --yes to overwrite)

set -eu

cd "$(dirname "$0")/.."

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP="${KEEP:-30}"
COMPOSE="docker compose -f docker-compose.prod.yml"
ENV_FILE="${ENV_FILE:-.env.production}"

if [ ! -f "$ENV_FILE" ]; then
    echo "No $ENV_FILE; run this from the repository root on the server." >&2
    exit 1
fi

# Read the credentials the compose file uses, so the dump matches the live database.
# shellcheck disable=SC1090
. "./$ENV_FILE"
: "${POSTGRES_USER:?POSTGRES_USER missing from $ENV_FILE}"
: "${POSTGRES_DB:?POSTGRES_DB missing from $ENV_FILE}"

mkdir -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%d-%H%M)
TARGET="$BACKUP_DIR/rpci-$STAMP.dump"

# -Fc: custom format, compressed, and what pg_restore rebuilds exactly.
# --no-owner: the restore should not depend on the role names matching.
echo "[$(date -u +%FT%TZ)] dumping $POSTGRES_DB to $TARGET"
$COMPOSE exec -T db pg_dump \
    --format=custom \
    --no-owner \
    --no-privileges \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" > "$TARGET"

# A dump that failed halfway is worse than none, because it looks like a backup.
if [ ! -s "$TARGET" ]; then
    echo "Dump is empty — treating as a failure." >&2
    rm -f "$TARGET"
    exit 1
fi

SIZE=$(du -h "$TARGET" | cut -f1)
echo "[$(date -u +%FT%TZ)] wrote $TARGET ($SIZE)"

# Keep the most recent $KEEP and delete the rest, oldest first.
ls -1t "$BACKUP_DIR"/rpci-*.dump 2>/dev/null | tail -n "+$((KEEP + 1))" | while read -r old; do
    echo "  removing old backup $(basename "$old")"
    rm -f "$old"
done

echo "[$(date -u +%FT%TZ)] done — $(ls -1 "$BACKUP_DIR"/rpci-*.dump | wc -l | tr -d ' ') archive(s) retained"
