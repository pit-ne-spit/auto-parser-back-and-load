# Анализ ошибки ежедневного обновления

## Описание ошибки

При выполнении ежедневного обновления возникает ошибка:
```
ConnectionResetError(10054, '...')
```

Ошибка происходит при вызове `get_change_id()` для получения начального ID изменений.

## Причины проблемы

### 1. Блокировка event loop синхронными вызовами

**Проблема:**
- В `daily_updater.py` (строка 152) вызывается синхронный метод `self.client.get_change_id(process_date)`
- Этот метод использует `retry_sync()`, который при ошибке вызывает `time.sleep(720)` (12 минут)
- `time.sleep()` блокирует весь event loop в async контексте

**Код проблемы:**
```python
# app/loaders/daily_updater.py:152
change_id = self.client.get_change_id(process_date)  # Синхронный вызов в async функции
```

```python
# app/utils/retry.py:173
time.sleep(interval_seconds)  # Блокирует event loop!
```

### 2. Ошибка подключения ConnectionResetError(10054)

**Причины:**
- Сервер CHE168 закрыл соединение (таймаут, перегрузка, проблемы с сетью)
- Windows ошибка 10054 = "An existing connection was forcibly closed by the remote host"

### 3. Неправильная обработка ошибок в async контексте

При ошибке в `get_change_id()`:
- Retry механизм пытается повторить запрос через 12 минут
- Это блокирует выполнение на 12 минут
- В тестовом режиме это неприемлемо

## Решения

### Решение 1: Обернуть синхронные вызовы в executor (рекомендуется)

Использовать `asyncio.to_thread()` или `loop.run_in_executor()` для выполнения синхронных вызовов в отдельном потоке:

```python
import asyncio

# В daily_updater.py
change_id = await asyncio.to_thread(self.client.get_change_id, process_date)
response = await asyncio.to_thread(self.client.get_changes, change_id=current_change_id)
```

**Преимущества:**
- Не блокирует event loop
- Минимальные изменения кода
- Сохраняет существующую логику retry

### Решение 2: Создать async версию клиента

Создать async методы в CHE168Client, которые используют `aiohttp` вместо `requests`:

```python
import aiohttp

async def get_change_id_async(self, date_param: date) -> int:
    async with aiohttp.ClientSession() as session:
        # async запрос
        async with session.get(url) as response:
            return await response.json()
```

**Преимущества:**
- Полностью async
- Лучшая производительность
- Правильная архитектура

**Недостатки:**
- Требует больше изменений
- Нужно добавить зависимость `aiohttp`

### Решение 3: Уменьшить интервал retry для тестирования

Добавить возможность переопределения интервала retry для тестовых режимов:

```python
# В config.yaml добавить тестовый режим
retry:
  test_mode: true
  test_interval_seconds: 5  # Для тестов использовать 5 секунд вместо 720
```

## Рекомендуемое решение

**Использовать Решение 1** - обернуть синхронные вызовы в `asyncio.to_thread()`:

1. Минимальные изменения кода
2. Не требует новых зависимостей
3. Решает проблему блокировки
4. Сохраняет существующую логику retry

## ✅ Реализованное исправление

Проблема исправлена в следующих файлах:

### `app/loaders/daily_updater.py`
- Добавлен `import asyncio`
- `get_change_id()` обернут в `asyncio.to_thread()`
- `get_changes()` обернут в `asyncio.to_thread()`

### `app/loaders/initial_loader.py`
- Добавлен `import asyncio`
- `get_offers()` обернут в `asyncio.to_thread()` (для консистентности)

**Результат:**
- Синхронные API вызовы теперь выполняются в отдельном потоке
- Event loop не блокируется при retry механизме
- Retry механизм работает корректно без блокировки на 12 минут

## Дополнительные улучшения

1. **Улучшить обработку ошибок**: Добавить более детальное логирование ошибок подключения
2. **Добавить таймауты**: Убедиться, что таймауты настроены правильно
3. **Обработка сетевых ошибок**: Различать временные и постоянные ошибки
4. **Метрики**: Добавить метрики для отслеживания успешности запросов
