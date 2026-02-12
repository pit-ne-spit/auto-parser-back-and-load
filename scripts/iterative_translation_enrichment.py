"""Итеративный процесс обогащения словаря переводов.

Цикл:
1. Нормализуем все объявления (где is_processed = false)
2. Запускаем анализатор непереведенных значений
3. Извлекаем непереведенные значения в JSON
4. (Ручной этап: добавляем переводы в JSON файл)
5. Добавляем переводы в словарь
6. Сбрасываем is_processed = false для повторной нормализации
7. Повторяем до тех пор, пока не будет непереведенных значений
"""

import sys
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import RawData
from sqlalchemy import select, update
from app.utils.logger import logger


async def reset_is_processed():
    """Сбрасывает флаг is_processed для всех записей в raw_data."""
    logger.info("Сброс флага is_processed для всех записей...")
    
    async with AsyncSessionLocal() as session:
        # Получаем статистику до сброса
        result = await session.execute(
            select(RawData.id).where(RawData.is_processed == True)
        )
        processed_count = len(result.scalars().all())
        
        # Сбрасываем флаг
        await session.execute(
            update(RawData).values(is_processed=False)
        )
        await session.commit()
        
        logger.info(f"Сброшено флагов is_processed: {processed_count}")
        logger.info("Все записи готовы к повторной нормализации")


async def count_untranslated() -> int:
    """Подсчитывает количество записей с непереведенными значениями."""
    from scripts.analyze_untranslated import contains_chinese, extract_chinese_texts
    from app.database.models import ProcessedData
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ProcessedData))
        records = result.scalars().all()
        
        count = 0
        for record in records:
            # Проверяем текстовые поля (description исключен - не переводим)
            text_fields = [
                record.mark, record.model, record.color,
                record.engine_type, record.transmission_type, record.body_type,
                record.address, record.section, record.drive_type
                # record.description - не переводим
            ]
            
            has_chinese = False
            for field_value in text_fields:
                if field_value and contains_chinese(field_value):
                    has_chinese = True
                    break
            
            if not has_chinese and record.options:
                for option in record.options:
                    if option and contains_chinese(option):
                        has_chinese = True
                        break
            
            if not has_chinese and record.configuration:
                config_chinese = extract_chinese_texts(record.configuration, 'configuration')
                if config_chinese:
                    has_chinese = True
            
            if has_chinese:
                count += 1
        
        return count


async def iterative_enrichment_cycle(
    max_iterations: int = 10,
    translations_file: str = "translations_to_add.json",
    min_count: int = 1,
    auto_add: bool = True,
    auto_translate: bool = True,
    translation_provider: str = "argos",
    wait_for_manual_translations: bool = False
):
    """
    Итеративный цикл обогащения словаря переводов.
    
    Args:
        max_iterations: Максимальное количество итераций
        translations_file: Путь к файлу с переводами
        min_count: Минимальное количество вхождений для извлечения
        auto_add: Автоматически добавлять переводы (если они уже есть в файле)
        wait_for_manual_translations: Ожидать ручного добавления переводов между итерациями
    """
    logger.info("=" * 80)
    logger.info("НАЧАЛО ИТЕРАТИВНОГО ПРОЦЕССА ОБОГАЩЕНИЯ СЛОВАРЯ ПЕРЕВОДОВ")
    logger.info("=" * 80)
    
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        logger.info("\n" + "=" * 80)
        logger.info(f"ИТЕРАЦИЯ {iteration}/{max_iterations}")
        logger.info("=" * 80)
        
        # Шаг 1: Нормализация всех необработанных записей
        logger.info("\n[ШАГ 1] Нормализация всех объявлений...")
        try:
            result = subprocess.run(
                [sys.executable, "scripts/normalize.py"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                logger.error(f"Ошибка при нормализации: {result.stderr}")
                return 1
            logger.info("✓ Нормализация завершена")
        except Exception as e:
            logger.error(f"Ошибка при нормализации: {e}", exc_info=True)
            return 1
        
        # Шаг 2: Анализ непереведенных значений
        logger.info("\n[ШАГ 2] Анализ непереведенных значений...")
        try:
            result = subprocess.run(
                [sys.executable, "scripts/analyze_untranslated.py"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                logger.error(f"Ошибка при анализе: {result.stderr}")
                return 1
            logger.info("✓ Анализ завершен")
        except Exception as e:
            logger.error(f"Ошибка при анализе: {e}", exc_info=True)
            return 1
        
        # Шаг 3: Извлечение непереведенных значений
        logger.info("\n[ШАГ 3] Извлечение непереведенных значений...")
        try:
            result = subprocess.run(
                [sys.executable, "scripts/extract_translations.py",
                 "--output", translations_file, "--min-count", str(min_count)],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                logger.error(f"Ошибка при извлечении: {result.stderr}")
                return 1
            logger.info("✓ Извлечение завершено")
        except Exception as e:
            logger.error(f"Ошибка при извлечении: {e}", exc_info=True)
            return 1
        
        # Проверяем, есть ли непереведенные значения
        translations_path = Path(__file__).parent.parent / translations_file
        if not translations_path.exists():
            logger.warning("Файл с переводами не найден")
            break
        
        # Проверяем количество непереведенных значений
        import json
        with open(translations_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        new_translations_count = data.get('metadata', {}).get('new_translations_count', 0)
        
        if new_translations_count == 0:
            logger.info("\n" + "=" * 80)
            logger.info("✓ ВСЕ ЗНАЧЕНИЯ ПЕРЕВЕДЕНЫ!")
            logger.info("=" * 80)
            break
        
        logger.info(f"\nНайдено непереведенных значений: {new_translations_count}")
        
        # Шаг 4: Автоматический перевод непереведенных значений
        translated_file = translations_file
        if auto_translate:
            logger.info("\n[ШАГ 4] Автоматический перевод непереведенных значений...")
            logger.info(f"Используется провайдер: {translation_provider}")
            if translation_provider == "argos":
                logger.info("⚠ Argos Translate работает офлайн, но требует установки языковых пакетов")
                logger.info("Если пакеты не установлены, запустите: python scripts/setup_argos_translate.py")
            try:
                translated_file = translations_file.replace(".json", "_translated.json")
                result = subprocess.run(
                    [sys.executable, "scripts/auto_translate_extracted.py",
                     "--input", translations_file,
                     "--output", translated_file,
                     "--provider", translation_provider,
                     "--min-priority", "low"],
                    cwd=Path(__file__).parent.parent,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                if result.returncode != 0:
                    logger.warning(f"Ошибка при автоматическом переводе: {result.stderr}")
                    logger.info("Продолжаем без автоматического перевода...")
                    translated_file = translations_file
                else:
                    logger.info("✓ Автоматический перевод завершен")
                    translations_path = Path(__file__).parent.parent / translated_file
            except Exception as e:
                logger.warning(f"Ошибка при автоматическом переводе: {e}")
                logger.info("Продолжаем без автоматического перевода...")
                translated_file = translations_file
        else:
            logger.info("\n[ШАГ 4] Автоматический перевод пропущен (auto_translate=False)")
        
        # Если нужен ручной ввод
        if wait_for_manual_translations and not auto_add:
            logger.info("\n" + "=" * 80)
            logger.info("[ШАГ 4.5] ОЖИДАНИЕ РУЧНОГО ДОБАВЛЕНИЯ ПЕРЕВОДОВ")
            logger.info("=" * 80)
            logger.info(f"Отредактируйте файл: {translations_path}")
            logger.info("Нажмите Enter когда закончите...")
            input()
        
        # Шаг 5: Добавление переводов в словарь
        if auto_add:
            logger.info("\n[ШАГ 5] Добавление переводов в словарь...")
            try:
                cmd = [sys.executable, "scripts/add_translations.py", str(translations_path)]
                result = subprocess.run(
                    cmd,
                    cwd=Path(__file__).parent.parent,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                if result.returncode != 0:
                    logger.error(f"Ошибка при добавлении переводов: {result.stderr}")
                    logger.info("Продолжаем без добавления переводов...")
                else:
                    logger.info("✓ Переводы добавлены в словарь")
            except Exception as e:
                logger.error(f"Ошибка при добавлении переводов: {e}", exc_info=True)
                logger.info("Продолжаем без добавления переводов...")
        else:
            logger.info("\n[ШАГ 5] Добавление переводов пропущено (auto_add=False)")
            logger.info(f"Для добавления переводов запустите:")
            logger.info(f"  python scripts/add_translations.py {translations_path}")
        
        # Шаг 6: Сброс флага is_processed для повторной нормализации
        logger.info("\n[ШАГ 6] Сброс флага is_processed для повторной нормализации...")
        try:
            await reset_is_processed()
            logger.info("✓ Флаг is_processed сброшен")
        except Exception as e:
            logger.error(f"Ошибка при сбросе флага: {e}", exc_info=True)
            return 1
        
        # Проверяем, остались ли непереведенные значения
        logger.info("\nПроверка количества записей с непереведенными значениями...")
        try:
            untranslated_count = await count_untranslated()
            logger.info(f"Записей с непереведенными значениями: {untranslated_count}")
            
            if untranslated_count == 0:
                logger.info("\n" + "=" * 80)
                logger.info("✓ ВСЕ ЗНАЧЕНИЯ ПЕРЕВЕДЕНЫ!")
                logger.info("=" * 80)
                break
        except Exception as e:
            logger.warning(f"Не удалось подсчитать непереведенные записи: {e}")
    
    logger.info("\n" + "=" * 80)
    logger.info("ИТЕРАТИВНЫЙ ПРОЦЕСС ЗАВЕРШЕН")
    logger.info("=" * 80)
    logger.info(f"Выполнено итераций: {iteration}")
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Итеративный процесс обогащения словаря переводов'
    )
    parser.add_argument(
        '--max-iterations',
        type=int,
        default=10,
        help='Максимальное количество итераций (по умолчанию: 10)'
    )
    parser.add_argument(
        '--translations-file',
        type=str,
        default='translations_to_add.json',
        help='Путь к файлу с переводами (по умолчанию: translations_to_add.json)'
    )
    parser.add_argument(
        '--min-count',
        type=int,
        default=1,
        help='Минимальное количество вхождений для извлечения (по умолчанию: 1)'
    )
    parser.add_argument(
        '--auto-add',
        action='store_true',
        default=True,
        help='Автоматически добавлять переводы из файла (по умолчанию: True)'
    )
    parser.add_argument(
        '--no-auto-add',
        dest='auto_add',
        action='store_false',
        help='Не добавлять переводы автоматически'
    )
    parser.add_argument(
        '--auto-translate',
        action='store_true',
        default=True,
        help='Автоматически переводить через API (по умолчанию: True)'
    )
    parser.add_argument(
        '--no-auto-translate',
        dest='auto_translate',
        action='store_false',
        help='Не переводить автоматически'
    )
    parser.add_argument(
        '--translation-provider',
        type=str,
        default='argos',
        choices=['deep_translator', 'translators', 'argos', 'google', 'deepl', 'yandex'],
        help='Провайдер автоматического перевода (по умолчанию: argos - офлайн)'
    )
    parser.add_argument(
        '--wait',
        action='store_true',
        dest='wait_for_manual_translations',
        help='Ждать ручного добавления переводов между итерациями'
    )
    
    args = parser.parse_args()
    
    # Настройка кодировки для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    exit_code = asyncio.run(iterative_enrichment_cycle(
        max_iterations=args.max_iterations,
        translations_file=args.translations_file,
        min_count=args.min_count,
        auto_add=args.auto_add,
        auto_translate=args.auto_translate,
        translation_provider=args.translation_provider,
        wait_for_manual_translations=args.wait_for_manual_translations
    ))
    
    sys.exit(exit_code)
