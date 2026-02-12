#!/bin/bash
# Entrypoint: миграции при старте, затем выполнение команды
# postgres уже готов (depends_on + healthcheck в docker-compose)
set -e

echo "Waiting for database..."
sleep 3

echo "Running database migrations..."
alembic upgrade head

echo "Starting: $*"
exec "$@"
