"""Добавление переводов в словарь translator.py."""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.translator import TRANSLATIONS_CN_RU
from app.utils.logger import logger


def validate_translation_entry(cn_text: str, ru_text: str) -> tuple[bool, str]:
    """
    Валидирует запись перевода.
    
    Returns:
        (is_valid, error_message)
    """
    if not cn_text or not isinstance(cn_text, str):
        return False, "Китайский текст не может быть пустым"
    
    if not ru_text or not isinstance(ru_text, str):
        return False, "Русский текст не может быть пустым"
    
    # Проверяем, что китайский текст содержит китайские символы
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    if not chinese_pattern.search(cn_text):
        return False, "Китайский текст должен содержать китайские иероглифы"
    
    return True, ""


def add_translations_from_json(json_file: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Добавляет переводы из JSON файла в словарь.
    
    Args:
        json_file: Путь к JSON файлу с переводами
        dry_run: Если True, только проверяет без добавления
    
    Returns:
        Статистика добавления
    """
    json_path = Path(json_file)
    
    if not json_path.exists():
        raise FileNotFoundError(f"Файл не найден: {json_file}")
    
    logger.info(f"Загрузка переводов из: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Поддерживаем два формата:
    # 1. Формат из extract_translations.py (с metadata)
    # 2. Простой формат {cn_text: ru_text}
    
    translations_to_add = {}
    
    if "translations_by_field" in data:
        # Формат из extract_translations.py
        for field_name, field_translations in data["translations_by_field"].items():
            for cn_text, info in field_translations.items():
                if isinstance(info, dict) and "translation" in info:
                    # Если есть готовый перевод
                    translations_to_add[cn_text] = info["translation"]
                elif isinstance(info, dict) and "ru" in info:
                    translations_to_add[cn_text] = info["ru"]
    elif isinstance(data, dict):
        # Простой формат {cn_text: ru_text}
        for cn_text, ru_text in data.items():
            if isinstance(ru_text, str):
                translations_to_add[cn_text] = ru_text
    
    if not translations_to_add:
        logger.warning("Не найдено переводов для добавления")
        return {
            "total": 0,
            "added": 0,
            "skipped": 0,
            "errors": 0
        }
    
    logger.info(f"Найдено {len(translations_to_add)} переводов для добавления")
    
    # Валидация и проверка дубликатов
    stats = {
        "total": len(translations_to_add),
        "added": 0,
        "skipped": 0,
        "errors": 0,
        "already_exists": 0
    }
    
    valid_translations = {}
    errors = []
    
    for cn_text, ru_text in translations_to_add.items():
        is_valid, error_msg = validate_translation_entry(cn_text, ru_text)
        
        if not is_valid:
            errors.append(f"{cn_text}: {error_msg}")
            stats["errors"] += 1
            continue
        
        if cn_text in TRANSLATIONS_CN_RU:
            if TRANSLATIONS_CN_RU[cn_text] == ru_text:
                stats["skipped"] += 1
                stats["already_exists"] += 1
            else:
                logger.warning(f"Перевод уже существует с другим значением: '{cn_text}' -> '{TRANSLATIONS_CN_RU[cn_text]}' (новый: '{ru_text}')")
                stats["skipped"] += 1
            continue
        
        valid_translations[cn_text] = ru_text
        stats["added"] += 1
    
    if errors:
        logger.warning(f"Найдено {len(errors)} ошибок валидации:")
        for error in errors[:10]:  # Показываем первые 10
            logger.warning(f"  - {error}")
        if len(errors) > 10:
            logger.warning(f"  ... и еще {len(errors) - 10} ошибок")
    
    if dry_run:
        logger.info("РЕЖИМ ПРОВЕРКИ (dry-run): переводы не будут добавлены")
        logger.info(f"Будет добавлено: {stats['added']}")
        logger.info(f"Пропущено (уже есть): {stats['skipped']}")
        logger.info(f"Ошибки: {stats['errors']}")
        return stats
    
    if not valid_translations:
        logger.warning("Нет валидных переводов для добавления")
        return stats
    
    # Читаем текущий файл translator.py
    translator_file = Path(__file__).parent.parent / "app" / "utils" / "translator.py"
    
    logger.info(f"Чтение файла: {translator_file}")
    with open(translator_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Находим словарь TRANSLATIONS_CN_RU
    pattern = r'(TRANSLATIONS_CN_RU\s*=\s*\{)(.*?)(\})'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError("Не удалось найти словарь TRANSLATIONS_CN_RU в файле translator.py")
    
    # Формируем новые записи
    new_entries = []
    for cn_text, ru_text in sorted(valid_translations.items()):
        # Экранируем кавычки в текстах
        cn_escaped = cn_text.replace('"', '\\"')
        ru_escaped = ru_text.replace('"', '\\"')
        new_entries.append(f'    "{cn_escaped}": "{ru_escaped}",')
    
    # Вставляем новые записи перед закрывающей скобкой
    new_dict_content = match.group(1) + match.group(2)
    
    # Добавляем новые записи, если их еще нет
    if new_entries:
        # Проверяем, есть ли уже комментарий для новых переводов
        if "# Новые переводы" not in new_dict_content:
            new_dict_content += "\n    # Новые переводы (добавлено автоматически)\n"
        
        new_dict_content += "\n".join(new_entries) + "\n"
    
    new_dict_content += match.group(3)
    
    # Заменяем словарь в файле
    new_content = content[:match.start()] + new_dict_content + content[match.end():]
    
    # Сохраняем обновленный файл
    logger.info(f"Сохранение обновленного файла: {translator_file}")
    with open(translator_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    logger.info("=" * 60)
    logger.info("РЕЗУЛЬТАТЫ ДОБАВЛЕНИЯ ПЕРЕВОДОВ:")
    logger.info("=" * 60)
    logger.info(f"Всего обработано: {stats['total']}")
    logger.info(f"Добавлено новых: {stats['added']}")
    logger.info(f"Пропущено (уже есть): {stats['skipped']}")
    logger.info(f"Ошибки валидации: {stats['errors']}")
    logger.info("=" * 60)
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Добавление переводов в словарь translator.py')
    parser.add_argument(
        'json_file',
        type=str,
        help='Путь к JSON файлу с переводами'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим проверки без добавления переводов'
    )
    
    args = parser.parse_args()
    
    try:
        stats = add_translations_from_json(args.json_file, dry_run=args.dry_run)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        sys.exit(1)
