#!/bin/bash
# Restore PostgreSQL database from backup (on VPS, inside Docker)
# Запуск: ./scripts/db_restore.sh backup.sql
# Использование:
#   1. Скопировать backup на VPS
#   2. docker cp backup.sql che168_postgres:/tmp/backup.sql
#   3. docker exec -i che168_postgres psql -U postgres -d che168_db < backup.sql
#   Или: ./scripts/db_restore.sh backup.sql (если скрипт на VPS рядом с backup)

set -e

BACKUP_FILE="${1:?Usage: $0 <backup.sql>}"
CONTAINER="${2:-che168_postgres}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-che168_db}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "File not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring database $DB_NAME from $BACKUP_FILE..."
docker cp "$BACKUP_FILE" "$CONTAINER:/tmp/restore.sql"
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/restore.sql
docker exec "$CONTAINER" rm /tmp/restore.sql

echo "Restore completed."
