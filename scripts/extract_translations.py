"""Извлечение непереведенных значений из нормализованных данных для обогащения словаря переводов."""

import asyncio
import sys
import json
import re
from pathlib import Path
from collections import Counter
from typing import Dict, Set, List, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import ProcessedData
from sqlalchemy import select
from app.utils.translator import TRANSLATIONS_CN_RU
from app.utils.logger import logger


def contains_chinese(text: str) -> bool:
    """Проверяет, содержит ли текст китайские иероглифы."""
    if not isinstance(text, str):
        return False
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(chinese_pattern.search(text))


def extract_chinese_texts(data: Any, path: str = "", results: Dict[str, Set[str]] = None) -> Dict[str, Set[str]]:
    """Рекурсивно извлекает все китайские тексты из структуры данных."""
    if results is None:
        results = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            extract_chinese_texts(value, current_path, results)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            extract_chinese_texts(item, current_path, results)
    elif isinstance(data, str):
        if contains_chinese(data):
            if path not in results:
                results[path] = set()
            results[path].add(data)
    
    return results


def determine_priority(field_name: str, count: int) -> str:
    """Определяет приоритет перевода на основе поля и частоты использования."""
    # Высокий приоритет: часто используемые марки, модели, опции
    high_priority_fields = ['mark', 'model', 'options', 'engine_type', 'transmission_type', 'body_type']
    
    if field_name in high_priority_fields and count >= 10:
        return "high"
    elif field_name in high_priority_fields or count >= 50:
        return "medium"
    elif count >= 10:
        return "medium"
    else:
        return "low"


async def extract_translations(output_file: str = "translations_to_add.json", min_count: int = 1):
    """
    Извлекает непереведенные значения из processed_data и сохраняет в структурированный JSON.
    
    Args:
        output_file: Путь к выходному JSON файлу
        min_count: Минимальное количество вхождений для включения в результат
    """
    logger.info("Начало извлечения непереведенных значений...")
    
    async with AsyncSessionLocal() as session:
        # Получаем все записи
        result = await session.execute(select(ProcessedData))
        records = result.scalars().all()
        
        logger.info(f"Всего записей для анализа: {len(records)}")
        
        # Собираем непереведенные тексты по полям с подсчетом частоты
        untranslated_by_field: Dict[str, Counter] = {}
        all_untranslated: Set[str] = set()
        
        for record in records:
            # Проверяем текстовые поля (description исключен - не переводим)
            text_fields = [
                ('mark', record.mark),
                ('model', record.model),
                ('color', record.color),
                ('engine_type', record.engine_type),
                ('transmission_type', record.transmission_type),
                ('body_type', record.body_type),
                ('address', record.address),
                ('section', record.section),
                # ('description', record.description),  # Не переводим description
                ('drive_type', record.drive_type),
            ]
            
            for field_name, field_value in text_fields:
                if field_value and contains_chinese(field_value):
                    if field_name not in untranslated_by_field:
                        untranslated_by_field[field_name] = Counter()
                    untranslated_by_field[field_name][field_value] += 1
                    all_untranslated.add(field_value)
            
            # Проверяем JSONB поля
            if record.options:
                for option in record.options:
                    if option and contains_chinese(option):
                        if 'options' not in untranslated_by_field:
                            untranslated_by_field['options'] = Counter()
                        untranslated_by_field['options'][option] += 1
                        all_untranslated.add(option)
            
            if record.configuration:
                config_chinese = extract_chinese_texts(record.configuration, 'configuration')
                for path, texts in config_chinese.items():
                    for text in texts:
                        if path not in untranslated_by_field:
                            untranslated_by_field[path] = Counter()
                        untranslated_by_field[path][text] += 1
                        all_untranslated.add(text)
        
        # Фильтруем значения, которые уже есть в словаре
        new_translations = {}
        already_in_dict_count = 0
        
        for field_name, counter in untranslated_by_field.items():
            for text, count in counter.items():
                if text in TRANSLATIONS_CN_RU:
                    already_in_dict_count += count
                    continue
                
                if count >= min_count:
                    if field_name not in new_translations:
                        new_translations[field_name] = {}
                    
                    priority = determine_priority(field_name, count)
                    new_translations[field_name][text] = {
                        "count": count,
                        "priority": priority
                    }
        
        # Создаем структурированный результат
        result_data = {
            "metadata": {
                "extracted_at": datetime.utcnow().isoformat(),
                "total_records_analyzed": len(records),
                "total_untranslated_unique": len(all_untranslated),
                "already_in_dict_count": already_in_dict_count,
                "new_translations_count": sum(len(v) for v in new_translations.values()),
                "min_count_threshold": min_count
            },
            "translations_by_field": new_translations,
            "summary_by_priority": {
                "high": sum(1 for field_data in new_translations.values() 
                           for item in field_data.values() if item["priority"] == "high"),
                "medium": sum(1 for field_data in new_translations.values() 
                             for item in field_data.values() if item["priority"] == "medium"),
                "low": sum(1 for field_data in new_translations.values() 
                          for item in field_data.values() if item["priority"] == "low")
            }
        }
        
        # Сохраняем в JSON файл
        output_path = Path(__file__).parent.parent / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Результаты сохранены в: {output_path}")
        logger.info(f"Всего уникальных непереведенных текстов: {len(all_untranslated)}")
        logger.info(f"Уже в словаре (вхождения): {already_in_dict_count}")
        logger.info(f"Новых для добавления: {result_data['metadata']['new_translations_count']}")
        logger.info(f"  - Высокий приоритет: {result_data['summary_by_priority']['high']}")
        logger.info(f"  - Средний приоритет: {result_data['summary_by_priority']['medium']}")
        logger.info(f"  - Низкий приоритет: {result_data['summary_by_priority']['low']}")
        
        # Выводим топ-20 самых частых по каждому полю
        print("\n" + "=" * 80)
        print("ТОП-20 САМЫХ ЧАСТЫХ НЕПЕРЕВЕДЕННЫХ ЗНАЧЕНИЙ ПО ПОЛЯМ:")
        print("=" * 80)
        
        for field_name in sorted(new_translations.keys()):
            field_data = new_translations[field_name]
            sorted_items = sorted(field_data.items(), key=lambda x: x[1]['count'], reverse=True)
            
            print(f"\n--- {field_name} ({len(field_data)} уникальных) ---")
            for text, info in sorted_items[:20]:
                print(f"  [{info['count']:4d}x] [{info['priority']:5s}] {text}")
        
        return result_data


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Извлечение непереведенных значений для обогащения словаря')
    parser.add_argument(
        '--output',
        type=str,
        default='translations_to_add.json',
        help='Путь к выходному JSON файлу (по умолчанию: translations_to_add.json)'
    )
    parser.add_argument(
        '--min-count',
        type=int,
        default=1,
        help='Минимальное количество вхождений для включения (по умолчанию: 1)'
    )
    
    args = parser.parse_args()
    
    # Настройка кодировки для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    asyncio.run(extract_translations(args.output, args.min_count))
