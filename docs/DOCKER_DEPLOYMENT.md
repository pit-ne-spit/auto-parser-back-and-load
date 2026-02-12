# Развёртывание на VPS через Docker

Полное руководство по развёртыванию проекта на VPS с миграцией данных из локальной БД.

## Архитектура

```
VPS
├── Docker Compose
│   ├── che168_postgres  — PostgreSQL 18 (данные в volume)
│   └── che168_app       — приложение (скрипты, миграции)
├── Cron (на хосте)      — ежедневный запуск daily_update
└── Volumes
    ├── postgres_data    — данные БД
    └── ./logs           — логи приложения
```

## Требования

- VPS: минимум 2 GB RAM, 20 GB SSD
- Доступ по SSH
- Docker Engine 24+, Docker Compose v2+

---

# Пошаговая инструкция

## Шаг 0: Установка Docker на VPS (если ещё не установлен)

Подключитесь к VPS по SSH и выполните:

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Выйдите из SSH и зайдите снова, чтобы применилась группа `docker`.

Проверка:
```bash
docker --version
docker compose version
```

---

## Шаг 1: Бэкап локальной БД (на вашем компьютере)

### Windows (PowerShell) — в папке проекта

```powershell
# Загрузить .env
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

# Создать бэкап (нужен pg_dump в PATH)
$env:PGPASSWORD = $env:DB_PASSWORD
pg_dump -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -F p -f backup_$(Get-Date -Format 'yyyyMMdd').sql
```

Или используйте скрипт:
```powershell
.\scripts\db_backup.ps1
```

Проверьте, что файл создан:
```powershell
Get-Item backup_*.sql
```

---

## Шаг 2: Клонирование проекта на VPS

```bash
ssh user@ВАШ_VPS_IP

# Создать директорию и клонировать
sudo mkdir -p /opt
cd /opt
sudo git clone https://github.com/ВАШ_РЕПОЗИТОРИЙ/auto-parser-back-and-load.git auto-parser
# или: git clone git@github.com:...
cd auto-parser
```

Если репозиторий частный — нужен SSH‑ключ или токен.

---

## Шаг 3: Настройка .env

```bash
cp .env.example .env
nano .env
```

Заполните (подставьте свои значения):

```env
DB_USER=postgres
DB_PASSWORD=надёжный_пароль
DB_NAME=che168_db
CHE168_API_KEY=ваш_api_ключ_от_auto_parser
CHE168_ACCESS_NAME=autobase
```

Сохраните (Ctrl+O, Enter, Ctrl+X в nano).

---

## Шаг 4: Копирование бэкапа на VPS

На **вашем компьютере** (PowerShell):

```powershell
scp backup_20260212.sql user@ВАШ_VPS_IP:/opt/auto-parser/backup.sql
```

Замените `backup_20260212.sql` на имя вашего файла, `user` — на пользователя SSH.

---

## Шаг 5: Запуск PostgreSQL

На **VPS**:

```bash
cd /opt/auto-parser
docker compose up -d postgres
```

Подождите 30–60 секунд. Проверка:

```bash
docker compose ps
# postgres должен быть Up (healthy)
```

---

## Шаг 6: Восстановление бэкапа

```bash
cd /opt/auto-parser

# Скопировать дамп в контейнер
docker cp backup.sql che168_postgres:/tmp/backup.sql

# Восстановить
docker exec che168_postgres psql -U postgres -d che168_db -f /tmp/backup.sql

# Удалить временный файл
docker exec che168_postgres rm /tmp/backup.sql
```

Проверка данных:

```bash
docker exec -it che168_postgres psql -U postgres -d che168_db -c "SELECT COUNT(*) FROM raw_data;"
docker exec -it che168_postgres psql -U postgres -d che168_db -c "SELECT COUNT(*) FROM processed_data;"
```

---

## Шаг 7: Запуск приложения

```bash
docker compose up -d
```

Приложение будет:
1. Применять миграции Alembic (если нужны)
2. Переходить в режим ожидания

Проверка:

```bash
docker compose ps
docker compose logs app
```

---

## Шаг 8: Проверка работы

```bash
# Тестовый запуск ежедневного обновления
docker exec che168_app python scripts/daily_update.py
```

Если всё идёт успешно — скрипт отработает без ошибок.

---

## Шаг 9: Настройка Cron (ежедневное обновление)

```bash
# Создать папку для логов (если не создана)
mkdir -p /opt/auto-parser/logs

crontab -e
```

Добавьте строку (обновление каждый день в 3:00):

```
0 3 * * * cd /opt/auto-parser && docker exec che168_app python scripts/daily_update.py >> /opt/auto-parser/logs/cron.log 2>&1
```

Сохраните и выйдите.

---

## Шаг 10: Готово

Развёртывание завершено. Полезные команды:

| Действие | Команда |
|----------|---------|
| Логи | `tail -f /opt/auto-parser/logs/app.log` |
| Обновление вручную | `docker exec che168_app python scripts/daily_update.py` |
| Нормализация | `docker exec che168_app python scripts/normalize.py` |
| Статус контейнеров | `docker compose ps` |
| Остановить всё | `docker compose down` |
| Запустить | `docker compose up -d` |

---

# Дополнительные разделы

---

## Часть 1: Подготовка локального бэкапа (подробно)

### Windows (PowerShell)

```powershell
# Загрузить переменные из .env
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#][^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), 'Process')
    }
}

# Создать бэкап
$env:PGPASSWORD = $env:DB_PASSWORD
pg_dump -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -F p -f backup_$(Get-Date -Format 'yyyyMMdd').sql
```

### Linux/macOS

```bash
source .env
./scripts/db_backup.sh
# или вручную:
PGPASSWORD=$DB_PASSWORD pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -F p -f backup.sql
```

### Проверка бэкапа

```bash
# Размер файла
ls -lh backup_*.sql

# Наличие данных (опционально)
grep -c "COPY" backup_*.sql
```

---

## Часть 2: Развёртывание на VPS

### 1. Клонирование и настройка

```bash
# На VPS
cd /opt  # или другая директория
git clone <url-репозитория> auto-parser
cd auto-parser
```

### 2. Создание .env

```bash
cp .env.example .env
nano .env  # или vim
```

Заполните:

```env
DB_USER=postgres
DB_PASSWORD=надёжный_пароль
DB_NAME=che168_db
CHE168_API_KEY=ваш_api_ключ
CHE168_ACCESS_NAME=autobase
```

### 3. Запуск контейнеров (без данных)

```bash
# Запустить только PostgreSQL
docker compose up -d postgres

# Дождаться готовности (30–60 сек)
docker compose ps
```

### 4. Восстановление бэкапа

Скопируйте `backup.sql` на VPS (scp, rsync и т.п.):

```bash
# С локальной машины
scp backup_20260212.sql user@vps-ip:/opt/auto-parser/backup.sql

# На VPS
cd /opt/auto-parser
docker cp backup.sql che168_postgres:/tmp/backup.sql
docker exec che168_postgres psql -U postgres -d che168_db -f /tmp/backup.sql
docker exec che168_postgres rm /tmp/backup.sql
```

**Важно:** при `FATAL: database "che168_db" does not exist` база создаётся контейнером из `POSTGRES_DB`. Проверьте:

```bash
docker exec che168_postgres psql -U postgres -c "\l"
```

### 5. Запуск приложения

```bash
docker compose up -d
```

При старте приложение:

1. Применяет миграции Alembic (если нужны новые)
2. Переходит в режим ожидания

### 6. Проверка

```bash
# Статус контейнеров
docker compose ps

# Логи
docker compose logs -f app

# Подключение к БД
docker exec -it che168_postgres psql -U postgres -d che168_db -c "SELECT COUNT(*) FROM raw_data;"
docker exec -it che168_postgres psql -U postgres -d che168_db -c "SELECT COUNT(*) FROM processed_data;"
```

---

## Часть 3: Cron — ежедневное обновление

### 1. Открыть crontab

```bash
crontab -e
```

### 2. Добавить задачу

```bash
# Ежедневное обновление в 3:00
0 3 * * * cd /opt/auto-parser && docker exec che168_app python scripts/daily_update.py >> logs/cron.log 2>&1
```

Или через docker compose:

```bash
0 3 * * * cd /opt/auto-parser && docker compose exec -T app python scripts/daily_update.py >> logs/cron.log 2>&1
```

### 3. Проверка вручную

```bash
docker exec che168_app python scripts/daily_update.py
docker exec che168_app python scripts/normalize.py
```

---

## Часть 4: Полезные команды

### Скрипты

```bash
# Ежедневное обновление
docker exec che168_app python scripts/daily_update.py

# Только нормализация
docker exec che168_app python scripts/normalize.py

# Единоразовая полная загрузка (при необходимости)
docker exec che168_app python scripts/initial_load.py

# Нормализация с ограничением (тест)
docker exec che168_app python scripts/normalize.py --limit 100
```

### Проверки

```bash
# Состояние синхронизации
docker exec che168_app python scripts/check_sync_state.py

# Прогресс нормализации
docker exec che168_app python scripts/show_progress.py

# Логи
tail -f logs/app.log
```

### Миграции Alembic

```bash
# Применить миграции
docker exec che168_app alembic upgrade head

# Текущая версия
docker exec che168_app alembic current
```

### Бэкапы на VPS

```bash
# Создать бэкап
docker exec che168_postgres pg_dump -U postgres che168_db -F p > backup_$(date +%Y%m%d).sql

# С retention (ежедневно в 4:00)
0 4 * * * docker exec che168_postgres pg_dump -U postgres che168_db -F p > /opt/auto-parser/backups/backup_$(date +\%Y\%m\%d).sql
```

---

## Часть 5: Обновление приложения

```bash
cd /opt/auto-parser
git pull
docker compose build app
docker compose up -d app
```

При перезапуске `app` миграции выполняются автоматически при старте.

---

## Часть 6: Первый запуск без миграции

Если локальной БД нет и нужно всё начать с нуля:

```bash
# 1. Запуск
docker compose up -d

# 2. Миграции (через entrypoint)
# 3. Запуск полной загрузки
docker exec che168_app python scripts/initial_load.py

# 4. Нормализация
docker exec che168_app python scripts/normalize.py

# 5. Дальше — cron для daily_update
```

---

## Устранение неполадок

### Ошибка подключения к БД

- `app` не запускается до `postgres`.
- Проверьте `DB_HOST=postgres` в `docker-compose.yml`.
- Логи: `docker compose logs postgres`

### Порт 5432 занят

```yaml
# В docker-compose.yml
ports:
  - "5433:5432"  # Внешний порт 5433
```

### Ошибки при restore

```bash
# Восстановление в пустую БД
docker exec che168_postgres psql -U postgres -d che168_db -f /tmp/backup.sql
```

### Проверка .env

```bash
docker compose config
```

### Просмотр логов

```bash
docker compose logs -f app
docker compose logs -f postgres
```

---

## Безопасность

1. **.env** — не должен попадать в git.
2. **Пароли** — сложные пароли для БД.
3. **Порты** — если 5432 не нужен снаружи:

```yaml
# Убрать ports у postgres или оставить только для localhost
ports:
  - "127.0.0.1:5432:5432"
```

4. **Файрвол** — откройте только SSH (22) и, при необходимости, HTTPS.
