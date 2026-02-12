# Настройка автоматического ежедневного обновления через Cron

## Описание

После установки приложения на VPS можно настроить автоматический запуск ежедневного обновления через cron. Скрипт `daily_update.py` автоматически:

1. Загружает изменения из API CHE168 за вчерашний день
2. Обновляет таблицу `raw_data` (добавляет новые записи, обновляет существующие, помечает удаленные)
3. Устанавливает `is_processed = False` для всех новых/обновленных записей
4. **Автоматически запускает нормализацию** для обогащения таблицы `processed_data`

## Требования

- Python 3.11+
- Установленные зависимости (`pip install -r requirements.txt`)
- Настроенная база данных PostgreSQL
- Настроенный файл `config.yaml`

## Настройка Cron

### 1. Открыть crontab для редактирования

```bash
crontab -e
```

### 2. Добавить задачу

Рекомендуется запускать обновление каждый день в определенное время (например, в 3:00 ночи):

```bash
# Ежедневное обновление данных в 3:00 утра
0 3 * * * cd /path/to/auto-parser-back-and-load && /usr/bin/python3 scripts/daily_update.py >> logs/cron.log 2>&1
```

Или если используется виртуальное окружение:

```bash
# Ежедневное обновление данных в 3:00 утра (с виртуальным окружением)
0 3 * * * cd /path/to/auto-parser-back-and-load && /path/to/venv/bin/python scripts/daily_update.py >> logs/cron.log 2>&1
```

### 3. Примеры расписаний

```bash
# Каждый день в 3:00 утра
0 3 * * * cd /path/to/auto-parser-back-and-load && /usr/bin/python3 scripts/daily_update.py >> logs/cron.log 2>&1

# Каждый день в 2:00 ночи
0 2 * * * cd /path/to/auto-parser-back-and-load && /usr/bin/python3 scripts/daily_update.py >> logs/cron.log 2>&1

# Каждый день в 4:00 утра и в 16:00 (дважды в день)
0 4,16 * * * cd /path/to/auto-parser-back-and-load && /usr/bin/python3 scripts/daily_update.py >> logs/cron.log 2>&1

# Каждый день в 3:00 утра с отправкой email при ошибках (требует настройки mail)
0 3 * * * cd /path/to/auto-parser-back-and-load && /usr/bin/python3 scripts/daily_update.py >> logs/cron.log 2>&1 || echo "Daily update failed" | mail -s "Daily Update Error" admin@example.com
```

### 4. Формат cron расписания

```
* * * * * команда
│ │ │ │ │
│ │ │ │ └─── день недели (0-7, где 0 и 7 = воскресенье)
│ │ │ └───── месяц (1-12)
│ │ └─────── день месяца (1-31)
│ └───────── час (0-23)
└─────────── минута (0-59)
```

## Параметры командной строки

### Основные параметры

- `--skip-normalization` - Пропустить автоматическую нормализацию после обновления
- `--normalization-batch-size N` - Размер батча для нормализации (по умолчанию из config.yaml)
- `--start-date YYYY-MM-DD` - Начать обработку с указанной даты (по умолчанию: вчера)
- `--max-dates N` - Ограничить количество дат для обработки (для тестирования)

### Примеры использования

```bash
# Стандартный запуск (обновление + нормализация)
python scripts/daily_update.py

# Только обновление без нормализации
python scripts/daily_update.py --skip-normalization

# Обновление с кастомным размером батча для нормализации
python scripts/daily_update.py --normalization-batch-size 500

# Обновление за конкретную дату
python scripts/daily_update.py --start-date 2026-02-09

# Тестовый запуск (только одна дата)
python scripts/daily_update.py --max-dates 1
```

## Логирование

Все логи сохраняются в:
- `logs/app.log` - основной лог приложения
- `logs/cron.log` - вывод cron (если настроен перенаправление)

Для мониторинга можно использовать:

```bash
# Просмотр последних записей
tail -f logs/app.log

# Поиск ошибок
grep ERROR logs/app.log

# Просмотр статистики обновлений
grep "Daily update completed" logs/app.log
```

## Проверка работы

### 1. Ручной запуск для проверки

```bash
cd /path/to/auto-parser-back-and-load
python scripts/daily_update.py
```

### 2. Проверка логов cron

```bash
# Проверка последнего запуска
tail -n 100 logs/cron.log

# Проверка системного лога cron (если настроен)
grep CRON /var/log/syslog
```

### 3. Проверка статуса в БД

```sql
-- Проверить последнюю дату обновления
SELECT * FROM sync_state;

-- Проверить количество необработанных записей
SELECT COUNT(*) FROM raw_data WHERE is_processed = false;

-- Проверить последние операции
SELECT * FROM operations_log ORDER BY started_at DESC LIMIT 10;
```

## Устранение проблем

### Проблема: Cron не запускается

1. Проверить права на выполнение:
   ```bash
   chmod +x scripts/daily_update.py
   ```

2. Проверить путь к Python:
   ```bash
   which python3
   ```

3. Проверить переменные окружения в cron (добавить в начало crontab):
   ```bash
   PATH=/usr/local/bin:/usr/bin:/bin
   ```

### Проблема: Ошибки при выполнении

1. Проверить логи:
   ```bash
   tail -f logs/app.log
   ```

2. Проверить подключение к БД в `config.yaml`

3. Проверить доступность API CHE168

### Проблема: Нормализация не запускается

1. Убедиться, что не установлен флаг `--skip-normalization`

2. Проверить, что обновление завершилось успешно (нет ошибок)

3. Проверить наличие необработанных записей:
   ```sql
   SELECT COUNT(*) FROM raw_data WHERE is_processed = false;
   ```

## Безопасность

- Убедитесь, что файл `config.yaml` с паролями БД имеет ограниченные права доступа:
  ```bash
  chmod 600 config.yaml
  ```

- Не храните пароли в переменных окружения cron (используйте `config.yaml`)

- Регулярно проверяйте логи на наличие ошибок

## Мониторинг

Рекомендуется настроить мониторинг:

1. **Проверка успешности выполнения** - скрипт возвращает код 0 при успехе, 1 при ошибке
2. **Алерты при ошибках** - можно настроить отправку email при ошибках
3. **Мониторинг размера БД** - следить за ростом таблиц `raw_data` и `processed_data`
4. **Мониторинг производительности** - отслеживать время выполнения через `operations_log`
