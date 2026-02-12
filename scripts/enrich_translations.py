"""Скрипт-оркестратор для автоматизации процесса обогащения словаря переводов."""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.logger import logger
import subprocess


async def enrich_translations_workflow(
    translations_file: str = "translations_to_add.json",
    min_count: int = 1,
    auto_add: bool = False,
    auto_retranslate: bool = False,
    dry_run: bool = False
):
    """
    Полный цикл обогащения словаря переводов.
    
    Args:
        translations_file: Путь к файлу с переводами для добавления
        min_count: Минимальное количество вхождений для извлечения
        auto_add: Автоматически добавлять переводы из файла
        auto_retranslate: Автоматически запускать повторную нормализацию
        dry_run: Режим проверки без изменений
    """
    logger.info("=" * 80)
    logger.info("НАЧАЛО ПРОЦЕССА ОБОГАЩЕНИЯ СЛОВАРЯ ПЕРЕВОДОВ")
    logger.info("=" * 80)
    
    # Шаг 1: Извлечение непереведенных значений
    logger.info("\n" + "=" * 80)
    logger.info("ШАГ 1: ИЗВЛЕЧЕНИЕ НЕПЕРЕВЕДЕННЫХ ЗНАЧЕНИЙ")
    logger.info("=" * 80)
    
    try:
        # Запускаем extract_translations через subprocess
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
            logger.error(f"✗ Ошибка при извлечении: {result.stderr}")
            return 1
        logger.info("✓ Извлечение завершено успешно")
    except Exception as e:
        logger.error(f"✗ Ошибка при извлечении: {e}", exc_info=True)
        return 1
    
    # Шаг 2: Проверка наличия файла с переводами
    translations_path = Path(__file__).parent.parent / translations_file
    
    if not translations_path.exists():
        logger.warning(f"\nФайл с переводами не найден: {translations_path}")
        logger.info("Создайте файл с переводами в формате:")
        logger.info('  {')
        logger.info('    "translations_by_field": {')
        logger.info('      "mark": {')
        logger.info('        "大通": {"translation": "Maxus"}')
        logger.info('      }')
        logger.info('    }')
        logger.info('  }')
        logger.info("\nИли используйте простой формат:")
        logger.info('  {')
        logger.info('    "大通": "Maxus",')
        logger.info('    "智界": "Zhijie"')
        logger.info('  }')
        return 0
    
    # Шаг 3: Добавление переводов
    if auto_add:
        logger.info("\n" + "=" * 80)
        logger.info("ШАГ 2: ДОБАВЛЕНИЕ ПЕРЕВОДОВ В СЛОВАРЬ")
        logger.info("=" * 80)
        
        try:
            # Запускаем add_translations через subprocess
            cmd = [sys.executable, "scripts/add_translations.py", str(translations_path)]
            if dry_run:
                cmd.append("--dry-run")
            
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                logger.error(f"✗ Ошибка при добавлении переводов: {result.stderr}")
                return 1
            logger.info("✓ Переводы добавлены успешно")
        except Exception as e:
            logger.error(f"✗ Ошибка при добавлении переводов: {e}", exc_info=True)
            return 1
    else:
        logger.info("\n" + "=" * 80)
        logger.info("ШАГ 2: ПРОПУЩЕН (auto_add=False)")
        logger.info("=" * 80)
        logger.info(f"Для добавления переводов запустите:")
        logger.info(f"  python scripts/add_translations.py {translations_file}")
        if dry_run:
            logger.info("  (добавьте --dry-run для проверки)")
    
    # Шаг 4: Повторная нормализация
    if auto_retranslate and not dry_run:
        logger.info("\n" + "=" * 80)
        logger.info("ШАГ 3: ПОВТОРНАЯ НОРМАЛИЗАЦИЯ ДАННЫХ")
        logger.info("=" * 80)
        
        try:
            # Запускаем retranslate через subprocess
            result = subprocess.run(
                [sys.executable, "scripts/retranslate.py", "--batch-size", "200"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            if result.returncode != 0:
                logger.error(f"✗ Ошибка при повторной нормализации: {result.stderr}")
                return 1
            logger.info("✓ Повторная нормализация завершена успешно")
        except Exception as e:
            logger.error(f"✗ Ошибка при повторной нормализации: {e}", exc_info=True)
            return 1
    elif auto_retranslate and dry_run:
        logger.info("\n" + "=" * 80)
        logger.info("ШАГ 3: ПРОПУЩЕН (dry-run режим)")
        logger.info("=" * 80)
    else:
        logger.info("\n" + "=" * 80)
        logger.info("ШАГ 3: ПРОПУЩЕН (auto_retranslate=False)")
        logger.info("=" * 80)
        logger.info("Для повторной нормализации запустите:")
        logger.info("  python scripts/retranslate.py")
    
    # Шаг 5: Анализ результатов
    logger.info("\n" + "=" * 80)
    logger.info("ШАГ 4: АНАЛИЗ РЕЗУЛЬТАТОВ")
    logger.info("=" * 80)
    
    try:
        # Запускаем analyze_untranslated через subprocess
        result = subprocess.run(
            [sys.executable, "scripts/analyze_untranslated.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode != 0:
            logger.error(f"✗ Ошибка при анализе: {result.stderr}")
            return 1
        logger.info("✓ Анализ завершен успешно")
    except Exception as e:
        logger.error(f"✗ Ошибка при анализе: {e}", exc_info=True)
        return 1
    
    logger.info("\n" + "=" * 80)
    logger.info("ПРОЦЕСС ОБОГАЩЕНИЯ СЛОВАРЯ ЗАВЕРШЕН")
    logger.info("=" * 80)
    
    return 0


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Оркестратор для автоматизации процесса обогащения словаря переводов'
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
        help='Автоматически добавлять переводы из файла'
    )
    parser.add_argument(
        '--auto-retranslate',
        action='store_true',
        help='Автоматически запускать повторную нормализацию после добавления переводов'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Режим проверки без изменений'
    )
    
    args = parser.parse_args()
    
    # Настройка кодировки для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    exit_code = asyncio.run(enrich_translations_workflow(
        translations_file=args.translations_file,
        min_count=args.min_count,
        auto_add=args.auto_add,
        auto_retranslate=args.auto_retranslate,
        dry_run=args.dry_run
    ))
    
    sys.exit(exit_code)
