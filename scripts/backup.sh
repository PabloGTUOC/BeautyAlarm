#!/bin/sh
# Dump the database to BACKUP_DIR, keeping the last KEEP_DAYS files.
#
# Run it from the repository root, e.g. nightly from the NAS crontab:
#   15 3 * * * cd /volume1/docker/beautyalarm && ./scripts/backup.sh >> backup.log 2>&1
#
# Restore with:
#   gunzip -c backups/beauty_alarm-YYYY-MM-DD.sql.gz | \
#     docker compose exec -T db mysql -u root -p"$MYSQL_ROOT_PASSWORD" beauty_alarm
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-30}"

# shellcheck disable=SC1091
[ -f .env ] && . ./.env

DATABASE="${MYSQL_DATABASE:-beauty_alarm}"
ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:?MYSQL_ROOT_PASSWORD is not set}"

mkdir -p "$BACKUP_DIR"
TARGET="$BACKUP_DIR/$DATABASE-$(date +%F).sql.gz"

docker compose exec -T db \
    mysqldump -u root -p"$ROOT_PASSWORD" --single-transaction --quick "$DATABASE" \
    | gzip > "$TARGET"

echo "wrote $TARGET ($(du -h "$TARGET" | cut -f1))"

find "$BACKUP_DIR" -name "$DATABASE-*.sql.gz" -mtime "+$KEEP_DAYS" -delete
echo "pruned dumps older than $KEEP_DAYS days"
