"""Анализ непереведенных данных для расширения словаря переводов."""

import asyncio
import sys
import re
from pathlib import Path
from collections import Counter
from typing import Set, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import ProcessedData
from sqlalchemy import select
from app.utils.translator import TRANSLATIONS_CN_RU


def contains_chinese(text: str) -> bool:
    """Проверяет, содержит ли текст китайские иероглифы."""
    if not isinstance(text, str):
        return False
    # Китайские иероглифы находятся в диапазоне \u4e00-\u9fff
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(chinese_pattern.search(text))


def extract_chinese_texts(data: any, path: str = "", results: Dict[str, Set[str]] = None) -> Dict[str, Set[str]]:
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


async def analyze_untranslated():
    """Анализирует нормализованные данные и находит непереведенные китайские тексты."""
    print("Анализ непереведенных данных...")
    print("=" * 80)
    
    async with AsyncSessionLocal() as session:
        # Получаем все записи
        result = await session.execute(select(ProcessedData))
        records = result.scalars().all()
        
        print(f"Всего записей для анализа: {len(records)}")
        
        # Собираем непереведенные тексты по полям
        untranslated_by_field: Dict[str, Counter] = {}
        all_untranslated: Set[str] = set()
        
        for record in records:
            # Проверяем текстовые поля
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
        
        # Выводим результаты
        print("\n" + "=" * 80)
        print("НЕПЕРЕВЕДЕННЫЕ ТЕКСТЫ ПО ПОЛЯМ:")
        print("=" * 80)
        
        for field_name, counter in sorted(untranslated_by_field.items(), key=lambda x: sum(x[1].values()), reverse=True):
            print(f"\n--- {field_name} ({sum(counter.values())} вхождений, {len(counter)} уникальных) ---")
            # Показываем топ-20 самых частых
            for text, count in counter.most_common(20):
                print(f"  [{count}x] {text}")
        
        # Создаем список для добавления в словарь
        print("\n" + "=" * 80)
        print("РЕКОМЕНДУЕМЫЕ ДОБАВЛЕНИЯ В СЛОВАРЬ:")
        print("=" * 80)
        
        new_translations = []
        already_in_dict = []
        
        for text in sorted(all_untranslated):
            if text in TRANSLATIONS_CN_RU:
                already_in_dict.append(text)
            else:
                new_translations.append(text)
        
        print(f"\nУже есть в словаре: {len(already_in_dict)}")
        print(f"Нужно добавить: {len(new_translations)}")
        
        # Сортируем по частоте (инициализируем всегда, даже если new_translations пуст)
        frequency_map = {}
        for field_name, counter in untranslated_by_field.items():
            for text, count in counter.items():
                if text not in TRANSLATIONS_CN_RU:
                    frequency_map[text] = frequency_map.get(text, 0) + count
        
        sorted_by_freq = sorted(frequency_map.items(), key=lambda x: x[1], reverse=True) if frequency_map else []
        
        if new_translations:
            print("\nТоп-50 самых частых непереведенных текстов для добавления:")
            print("-" * 80)
            
            for i, (text, freq) in enumerate(sorted_by_freq[:50], 1):
                print(f"{i:2d}. [{freq:3d}x] {text}")
        
        # Сохраняем результаты в файл
        output_file = Path(__file__).parent.parent / "untranslated_analysis.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("АНАЛИЗ НЕПЕРЕВЕДЕННЫХ ДАННЫХ\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Всего уникальных непереведенных текстов: {len(all_untranslated)}\n")
            f.write(f"Уже в словаре: {len(already_in_dict)}\n")
            f.write(f"Нужно добавить: {len(new_translations)}\n\n")
            
            f.write("НЕПЕРЕВЕДЕННЫЕ ТЕКСТЫ ПО ПОЛЯМ:\n")
            f.write("=" * 80 + "\n\n")
            for field_name, counter in sorted(untranslated_by_field.items(), key=lambda x: sum(x[1].values()), reverse=True):
                f.write(f"\n--- {field_name} ({sum(counter.values())} вхождений, {len(counter)} уникальных) ---\n")
                for text, count in counter.most_common():
                    f.write(f"  [{count}x] {text}\n")
            
            if sorted_by_freq:
                f.write("\n\nТОП-100 САМЫХ ЧАСТЫХ ДЛЯ ДОБАВЛЕНИЯ:\n")
                f.write("=" * 80 + "\n\n")
                for i, (text, freq) in enumerate(sorted_by_freq[:100], 1):
                    f.write(f"{i:3d}. [{freq:4d}x] {text}\n")
        
        print(f"\n\nРезультаты сохранены в: {output_file}")
        print(f"Всего найдено {len(all_untranslated)} уникальных непереведенных текстов")


if __name__ == "__main__":
    # Настройка кодировки для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    asyncio.run(analyze_untranslated())
