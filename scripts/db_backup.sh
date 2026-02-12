#!/bin/bash
# Backup local PostgreSQL database for migration to VPS
# Запуск: ./scripts/db_backup.sh
# Требует: .env с DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

set -e

source .env 2>/dev/null || true

OUTPUT_FILE="${1:-backup_$(date +%Y%m%d_%H%M%S).sql}"
OUTPUT_PATH="$(dirname "$0")/../$OUTPUT_FILE"

echo "Backing up database ${DB_NAME:-che168_db} to $OUTPUT_PATH..."
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "${DB_HOST:-localhost}" \
    -p "${DB_PORT:-5432}" \
    -U "${DB_USER:-postgres}" \
    -d "${DB_NAME:-che168_db}" \
    -F p \
    -f "$OUTPUT_PATH"

echo "Backup completed: $OUTPUT_PATH"
echo "File size: $(du -h "$OUTPUT_PATH" | cut -f1)"
