# Автоматическое обогащение словаря переводов

## Быстрый старт

Для **полностью автоматического** обогащения словаря переводов просто запустите:

```bash
python scripts/iterative_translation_enrichment.py
```

Скрипт автоматически:
1. ✅ Нормализует все объявления
2. ✅ Находит непереведенные значения
3. ✅ **Автоматически переводит их через Google Translate**
4. ✅ Добавляет переводы в словарь
5. ✅ Повторяет цикл до полного перевода всех значений

**Ручной ввод не требуется!**

## Установка зависимостей

Перед первым запуском установите библиотеку для перевода:

```bash
pip install googletrans==4.0.0rc1
```

Или установите все зависимости:

```bash
pip install -r requirements.txt
```

## Как это работает

1. **Нормализация** - обрабатывает все записи с `is_processed = false`
2. **Анализ** - находит китайские тексты без перевода
3. **Извлечение** - сохраняет их в `translations_to_add.json`
4. **Автоперевод** - переводит через Google Translate API (бесплатно)
5. **Добавление** - автоматически добавляет в словарь `translator.py`
6. **Сброс флагов** - устанавливает `is_processed = false` для повторной нормализации
7. **Повтор** - цикл продолжается до полного перевода

## Параметры запуска

### Базовый запуск (рекомендуется)
```bash
python scripts/iterative_translation_enrichment.py
```

### Ограничение итераций
```bash
python scripts/iterative_translation_enrichment.py --max-iterations 5
```

### Использование другого провайдера перевода

**DeepL (платный, но качественный):**
```bash
export DEEPL_TRANSLATE_API_KEY="your-api-key"
python scripts/iterative_translation_enrichment.py --translation-provider deepl
```

**Yandex Translate (платный):**
```bash
export YANDEX_TRANSLATE_API_KEY="your-api-key"
python scripts/iterative_translation_enrichment.py --translation-provider yandex
```

### Без автоматического перевода (если переводы уже готовы)
```bash
python scripts/iterative_translation_enrichment.py --no-auto-translate --auto-add
```

## Файлы

- `translations_to_add.json` - извлеченные непереведенные значения
- `translations_translated.json` - автоматически переведенные значения
- `untranslated_analysis.txt` - детальный анализ непереведенных значений

## Когда процесс завершится

Процесс автоматически завершится когда:
- ✅ Не останется непереведенных значений
- ✅ Будет достигнуто максимальное количество итераций (по умолчанию: 10)

Вы увидите сообщение:
```
✓ ВСЕ ЗНАЧЕНИЯ ПЕРЕВЕДЕНЫ!
```

## Примечания

- Google Translate API бесплатный, но имеет rate limits
- Для больших объемов данных процесс может занять время
- Рекомендуется запускать процесс в фоновом режиме или через screen/tmux
- Все переводы логируются для отслеживания прогресса

## Troubleshooting

**Ошибка: "googletrans не установлен"**
```bash
pip install googletrans==4.0.0rc1
```

**Ошибка: "Rate limit exceeded"**
- Скрипт автоматически добавляет задержки между запросами
- Если проблема сохраняется, используйте платный API (DeepL/Yandex)

**Процесс останавливается**
- Проверьте логи в `logs/app.log`
- Убедитесь, что база данных доступна
- Проверьте подключение к интернету (для Google Translate)
