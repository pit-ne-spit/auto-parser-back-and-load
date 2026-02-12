# Auto-parser CHE168 - Production Dockerfile (оптимизирован: ~2 мин вместо 6)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Только requirements (pg_dump не нужен — бэкапы делают на хосте)
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Код приложения (только нужные файлы — .dockerignore исключает backup, .venv, docs)
COPY app/ app/
COPY scripts/ scripts/
COPY alembic/ alembic/
COPY alembic.ini config.yaml ./

# Create directories for logs and tmp (used by single_instance lock)
RUN mkdir -p logs tmp

# Entrypoint: runs migrations, then executes command
COPY docker/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

# Default command - keep container running for cron
CMD ["sleep", "infinity"]
