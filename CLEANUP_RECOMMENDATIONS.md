# Рекомендации по очистке проекта

## Временные файлы для удаления

Ниже перечислены файлы, которые можно безопасно удалить. Они являются результатами тестирования и анализа и не используются в рабочем процессе проекта.

### Текстовые файлы с результатами анализа

```
check_models_marks.txt          - результат проверки моделей и марок
check_result.txt                - результат проверки
untranslated_analysis.txt        - анализ непереведенных данных
untranslated_after_update.txt   - непереведенные данные после обновления
untranslated_output.txt         - вывод непереведенных данных
final_analysis.txt              - финальный анализ
test_translation_output.txt     - результат тестирования перевода
translated_output.txt           - вывод переведенных данных
```

### JSON файлы с тестовыми данными

```
temp_car.json                   - временный файл с данными автомобиля
translated_car.json             - переведенные данные автомобиля (тестовые)
translated_car_ru.json          - переведенные данные автомобиля на русском (тестовые)
```

## Команды для удаления

### Windows (PowerShell)

```powershell
# Удаление текстовых файлов
Remove-Item check_models_marks.txt, check_result.txt, untranslated_analysis.txt, untranslated_after_update.txt, untranslated_output.txt, final_analysis.txt, test_translation_output.txt, translated_output.txt -ErrorAction SilentlyContinue

# Удаление JSON файлов
Remove-Item temp_car.json, translated_car.json, translated_car_ru.json -ErrorAction SilentlyContinue
```

### Linux/Mac (Bash)

```bash
# Удаление текстовых файлов
rm -f check_models_marks.txt check_result.txt untranslated_analysis.txt untranslated_after_update.txt untranslated_output.txt final_analysis.txt test_translation_output.txt translated_output.txt

# Удаление JSON файлов
rm -f temp_car.json translated_car.json translated_car_ru.json
```

## Файлы, которые следует оставить

### Справочники и документация

- `filters_reference.json` - справочник фильтров API (используется в проекте)
- `filters_full_response.json` - полный ответ API фильтров (справочный материал)
- `example.txt` - пример данных из API (справочный материал)
- Все `.md` файлы - документация проекта

## Добавление в .gitignore

Если эти файлы могут создаваться в процессе разработки, рекомендуется добавить их в `.gitignore`:

```gitignore
# Временные файлы результатов анализа
check_models_marks.txt
check_result.txt
untranslated_*.txt
final_analysis.txt
test_translation_output.txt
translated_output.txt

# Временные JSON файлы
temp_*.json
translated_car*.json
```

## Примечания

- Удаление этих файлов не повлияет на функциональность проекта
- Все временные файлы являются результатами тестирования и анализа
- Рекомендуется удалить их для поддержания чистоты проекта
- После удаления можно добавить паттерны в `.gitignore`, чтобы они не создавались в будущем

## Подробный анализ

Подробный анализ временных файлов см. в [docs/TEMP_FILES_ANALYSIS.md](docs/TEMP_FILES_ANALYSIS.md)
