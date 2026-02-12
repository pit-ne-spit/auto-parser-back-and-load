"""Автоматический перевод извлеченных непереведенных значений."""

import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.auto_translator import get_auto_translator
from app.utils.logger import logger


def auto_translate_extracted(
    input_file: str = "translations_to_add.json",
    output_file: str = "translations_translated.json",
    provider: str = "google",
    min_priority: str = "low"  # Параметр оставлен для обратной совместимости, но не используется - переводим все
):
    """
    Автоматически переводит извлеченные непереведенные значения.
    Переводит все значения независимо от приоритета (description исключен - не переводим).
    
    Args:
        input_file: Путь к файлу с извлеченными значениями
        output_file: Путь к выходному файлу с переводами
        provider: Провайдер перевода ("google", "deepl", "yandex", "argos")
        min_priority: Параметр оставлен для обратной совместимости, но не используется
    """
    input_path = Path(__file__).parent.parent / input_file
    
    if not input_path.exists():
        logger.error(f"Файл не найден: {input_path}")
        return 1
    
    logger.info(f"Загрузка данных из: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Инициализируем переводчик
    translator = get_auto_translator(provider)
    logger.info(f"Используется провайдер перевода: {translator.provider}")
    
    # Переводим значения (без фильтрации по приоритетам - переводим все)
    translations_by_field = data.get("translations_by_field", {})
    translated_data = {
        "metadata": data.get("metadata", {}),
        "translations_by_field": {},
        "summary": {
            "total_translated": 0,
            "total_skipped": 0,
            "errors": 0
        }
    }
    
    total_to_translate = sum(
        len(field_data) for field_data in translations_by_field.values()
    )
    
    logger.info(f"Всего значений для перевода: {total_to_translate}")
    logger.info("Переводим все значения независимо от приоритета (description исключен - не переводим)")
    
    translated_count = 0
    skipped_count = 0
    error_count = 0
    
    for field_name, field_translations in translations_by_field.items():
        logger.info(f"\nОбработка поля: {field_name} ({len(field_translations)} значений)")
        
        translated_field = {}
        
        for cn_text, info in field_translations.items():
            # Переводим все значения без фильтрации по приоритетам
            priority = info.get("priority", "low")
            
                # Переводим
            try:
                ru_text = translator.translate(cn_text, source_lang="zh", target_lang="ru")
                
                # Логируем первые несколько примеров для отладки
                if translated_count + skipped_count < 10:
                    logger.info(f"  Пример перевода: '{cn_text[:50]}' -> '{ru_text[:50] if ru_text else 'None'}'")
                    logger.info(f"    ru_text is None: {ru_text is None}")
                    logger.info(f"    ru_text == cn_text: {ru_text == cn_text if ru_text else 'N/A'}")
                    logger.info(f"    len(ru_text.strip()): {len(ru_text.strip()) if ru_text else 'N/A'}")
                
                # Проверяем, что перевод успешен
                if ru_text and len(ru_text.strip()) > 0:
                    import re
                    chinese_chars = re.findall(r'[\u4e00-\u9fff]', ru_text)
                    non_chinese_length = len(re.sub(r'[\u4e00-\u9fff\s,，。、]', '', ru_text))
                    
                    # Для адресов Argos может вернуть оригинал (имена собственные) - это нормально
                    # Принимаем перевод, если:
                    # 1. Результат отличается от оригинала ИЛИ
                    # 2. Это поле адреса (имена собственные не переводятся) ИЛИ
                    # 3. Результат содержит некитайские символы
                    is_different = ru_text != cn_text
                    is_address_field = field_name == 'address'
                    has_non_chinese = non_chinese_length > 0
                    
                    if is_different or is_address_field or has_non_chinese:
                        # Перевод успешен
                        translated_field[cn_text] = {
                            "translation": ru_text,
                            "count": info.get("count", 0),
                            "priority": priority,
                            "auto_translated": True
                        }
                        translated_count += 1
                        
                        if translated_count % 10 == 0:
                            logger.info(f"  Переведено: {translated_count}/{total_to_translate}")
                    else:
                        # Результат совпадает с оригиналом и содержит только китайские символы
                        # (не адрес и не содержит некитайских символов)
                        if skipped_count < 5:
                            logger.debug(f"  Пропущено (перевод не изменился, не адрес): '{cn_text[:50]}' -> '{ru_text[:50]}'")
                        skipped_count += 1
                else:
                    # Логируем первые несколько пропущенных для отладки
                    if skipped_count < 5:
                        logger.debug(f"  Пропущено (перевод пустой или None): '{cn_text[:50]}' -> '{ru_text[:50] if ru_text else 'None'}'")
                    skipped_count += 1
            except Exception as e:
                # Логируем первые несколько ошибок для отладки
                if error_count < 5:
                    logger.debug(f"  Ошибка при переводе '{cn_text[:50]}...': {e}")
                error_count += 1
        
        if translated_field:
            translated_data["translations_by_field"][field_name] = translated_field
    
    # Обновляем метаданные
    translated_data["summary"]["total_translated"] = translated_count
    translated_data["summary"]["total_skipped"] = skipped_count
    translated_data["summary"]["errors"] = error_count
    from datetime import datetime
    translated_data["metadata"]["translated_at"] = datetime.utcnow().isoformat()
    translated_data["metadata"]["provider"] = translator.provider
    
    # Сохраняем результат
    output_path = Path(__file__).parent.parent / output_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(translated_data, f, ensure_ascii=False, indent=2)
    
    logger.info("\n" + "=" * 80)
    logger.info("РЕЗУЛЬТАТЫ АВТОМАТИЧЕСКОГО ПЕРЕВОДА:")
    logger.info("=" * 80)
    logger.info(f"Переведено: {translated_count}")
    logger.info(f"Пропущено: {skipped_count}")
    logger.info(f"Ошибок: {error_count}")
    logger.info(f"\nРезультаты сохранены в: {output_path}")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Автоматический перевод извлеченных значений')
    parser.add_argument(
        '--input',
        type=str,
        default='translations_to_add.json',
        help='Входной файл с извлеченными значениями (по умолчанию: translations_to_add.json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='translations_translated.json',
        help='Выходной файл с переводами (по умолчанию: translations_translated.json)'
    )
    parser.add_argument(
        '--provider',
        type=str,
        default='argos',
        choices=['deep_translator', 'translators', 'argos', 'google', 'deepl', 'yandex'],
        help='Провайдер перевода (по умолчанию: argos - офлайн)'
    )
    parser.add_argument(
        '--min-priority',
        type=str,
        default='low',
        choices=['high', 'medium', 'low'],
        help='Минимальный приоритет для перевода (по умолчанию: low)'
    )
    
    args = parser.parse_args()
    
    # Настройка кодировки для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    exit_code = auto_translate_extracted(
        input_file=args.input,
        output_file=args.output,
        provider=args.provider,
        min_priority=args.min_priority
    )
    
    sys.exit(exit_code)
