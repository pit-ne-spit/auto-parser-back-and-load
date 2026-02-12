# Парсер CHE168.COM API

Проект для работы с API парсера объявлений с китайской площадки CHE168.COM

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Настройте переменные окружения в файле `.env`:
```
CHE168_API_KEY=ваш_api_ключ
CHE168_ACCESS_NAME=ваш_access_name
```

**Важно:** `access_name` - это уникальное имя, выданное при регистрации на auto-parser.ru. 
Формат URL: `https://{access_name}.auto-parser.ru/api/v2/che168`

## Использование

### Получение фильтров

Запустите скрипт для получения и анализа фильтров:
```bash
python get_filters.py
```

Скрипт:
- Выполнит запрос к `/filters` эндпоинту
- Проанализирует структуру ответа
- Создаст справочники фильтров:
  - `filters_full_response.json` - полный ответ от API
  - `filters_reference.json` - структурированный справочник
  - `filters_reference.py` - Python модуль со справочником

## Развёртывание на VPS (Docker)

Проект готов к развёртыванию в Docker-контейнерах:

```bash
# Клонировать, создать .env из .env.example
docker compose up -d

# Миграция локальной БД: см. docs/DOCKER_DEPLOYMENT.md
```

Подробнее: [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)

## Структура проекта

### Основные модули

- `app/loaders/` - модули загрузки данных:
  - `initial_loader.py` - единоразовое скачивание всех объявлений
  - `daily_updater.py` - ежедневное обновление данных
- `app/normalizers/` - модули нормализации данных:
  - `data_normalizer.py` - нормализация сырых данных в структурированный формат
- `app/api/` - публичное API (в разработке)
- `app/database/` - модели базы данных и подключение
- `app/utils/` - утилиты (клиент API, логирование, retry механизм и т.д.)

### Скрипты

- `scripts/initial_load.py` - запуск первоначальной загрузки
- `scripts/daily_update.py` - запуск ежедневного обновления
- `scripts/normalize.py` - запуск нормализации данных
- `get_filters.py` - скрипт для получения фильтров

### Документация

- `CHE168_API_DOCUMENTATION.md` - полная документация API CHE168
- `TASKS.md` - задачи проекта и статус реализации
- `TESTING.md` - документация по тестированию
- `docs/MODULE_INITIAL_LOADER.md` - документация модуля единоразового скачивания
- `docs/MODULE_DAILY_UPDATER.md` - документация модуля ежедневного обновления
- `docs/MODULE_NORMALIZER.md` - документация модуля нормализации
- `docs/TEMP_FILES_ANALYSIS.md` - анализ временных файлов проекта

### Конфигурация

- `config.yaml` - технические настройки проекта
- `.env` - переменные окружения (не попадает в git)
- `requirements.txt` - зависимости Python
- `alembic.ini` - конфигурация миграций БД
