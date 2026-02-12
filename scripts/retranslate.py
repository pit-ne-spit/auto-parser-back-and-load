"""Повторная нормализация данных с обновленным словарем переводов."""

import asyncio
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import ProcessedData, RawData
from sqlalchemy import select, update
from app.normalizers.data_normalizer import DataNormalizer
from app.utils.logger import logger


def contains_chinese(text: str) -> bool:
    """Проверяет, содержит ли текст китайские иероглифы."""
    if not isinstance(text, str):
        return False
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    return bool(chinese_pattern.search(text))


def has_chinese_in_record(record: ProcessedData) -> bool:
    """Проверяет, есть ли китайские символы в записи."""
    # Проверяем текстовые поля (description исключен - не переводим)
    text_fields = [
        record.mark, record.model, record.color,
        record.engine_type, record.transmission_type, record.body_type,
        record.address, record.section, record.drive_type
        # record.description - не переводим
    ]
    
    for field_value in text_fields:
        if field_value and contains_chinese(field_value):
            return True
    
    # Проверяем JSONB поля
    if record.options:
        for option in record.options:
            if option and contains_chinese(option):
                return True
    
    if record.configuration:
        # Рекурсивная проверка configuration
        def check_dict(d):
            if isinstance(d, dict):
                for v in d.values():
                    if isinstance(v, str) and contains_chinese(v):
                        return True
                    elif isinstance(v, (dict, list)):
                        if check_dict(v):
                            return True
            elif isinstance(d, list):
                for item in d:
                    if isinstance(item, str) and contains_chinese(item):
                        return True
                    elif isinstance(item, (dict, list)):
                        if check_dict(item):
                            return True
            return False
        
        if check_dict(record.configuration):
            return True
    
    return False


async def retranslate_records(
    fields: Optional[list] = None,
    limit: Optional[int] = None,
    batch_size: int = 200
):
    """
    Повторно нормализует записи с китайскими символами используя обновленный словарь.
    
    Args:
        fields: Список полей для обновления (None = все поля)
        limit: Максимальное количество записей для обработки
        batch_size: Размер батча для обработки
    """
    logger.info("Начало повторной нормализации с обновленным словарем...")
    
    if fields:
        logger.info(f"Обновление полей: {', '.join(fields)}")
    else:
        logger.info("Обновление всех полей")
    
    async with AsyncSessionLocal() as session:
        # Находим записи с китайскими символами
        result = await session.execute(select(ProcessedData))
        all_records = result.scalars().all()
        
        logger.info(f"Всего записей в processed_data: {len(all_records)}")
        
        # Фильтруем записи с китайскими символами
        records_to_update = []
        for record in all_records:
            if has_chinese_in_record(record):
                records_to_update.append(record)
        
        logger.info(f"Найдено записей с китайскими символами: {len(records_to_update)}")
        
        if limit:
            records_to_update = records_to_update[:limit]
            logger.info(f"Ограничение: обрабатываем {len(records_to_update)} записей")
        
        if not records_to_update:
            logger.info("Нет записей для обновления")
            return
        
        # Создаем нормализатор
        normalizer = DataNormalizer(batch_size=batch_size)
        
        # Получаем соответствующие raw_data записи
        inner_ids = [r.inner_id for r in records_to_update]
        
        # Обрабатываем батчами
        total_updated = 0
        total_errors = 0
        
        for i in range(0, len(inner_ids), batch_size):
            batch_inner_ids = inner_ids[i:i + batch_size]
            
            try:
                # Получаем raw_data для этого батча
                raw_result = await session.execute(
                    select(RawData).where(RawData.inner_id.in_(batch_inner_ids))
                )
                raw_records = raw_result.scalars().all()
                
                if len(raw_records) != len(batch_inner_ids):
                    logger.warning(f"Не все raw_data найдены для батча {i//batch_size + 1}")
                
                # Нормализуем каждую запись
                for raw_record in raw_records:
                    try:
                        # Нормализуем запись
                        normalized_fields = normalizer._normalize_record(raw_record.data)
                        
                        # Находим соответствующую processed_data запись
                        processed_result = await session.execute(
                            select(ProcessedData).where(ProcessedData.inner_id == raw_record.inner_id)
                        )
                        processed_record = processed_result.scalar_one_or_none()
                        
                        if not processed_record:
                            logger.warning(f"ProcessedData не найдена для inner_id: {raw_record.inner_id}")
                            continue
                        
                        # Обновляем только указанные поля или все поля
                        if fields:
                            for field in fields:
                                if field in normalized_fields:
                                    setattr(processed_record, field, normalized_fields[field])
                        else:
                            # Обновляем все поля
                            for field, value in normalized_fields.items():
                                if field != 'inner_id':  # inner_id не обновляем
                                    setattr(processed_record, field, value)
                        
                        processed_record.updated_at = datetime.utcnow()
                        total_updated += 1
                        
                    except Exception as e:
                        logger.error(f"Ошибка при обработке inner_id {raw_record.inner_id}: {e}")
                        total_errors += 1
                
                # Коммитим батч
                await session.commit()
                logger.info(f"Обработан батч {i//batch_size + 1}: обновлено {total_updated} записей")
                
            except Exception as e:
                logger.error(f"Ошибка при обработке батча {i//batch_size + 1}: {e}")
                await session.rollback()
                total_errors += 1
        
        logger.info("=" * 60)
        logger.info("РЕЗУЛЬТАТЫ ПОВТОРНОЙ НОРМАЛИЗАЦИИ:")
        logger.info("=" * 60)
        logger.info(f"Всего обработано записей: {len(records_to_update)}")
        logger.info(f"Успешно обновлено: {total_updated}")
        logger.info(f"Ошибок: {total_errors}")
        logger.info("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Повторная нормализация данных с обновленным словарем')
    parser.add_argument(
        '--fields',
        type=str,
        nargs='+',
        default=None,
        help='Список полей для обновления (по умолчанию: все поля)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Максимальное количество записей для обработки'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=200,
        help='Размер батча для обработки (по умолчанию: 200)'
    )
    
    args = parser.parse_args()
    
    # Настройка кодировки для Windows
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    
    asyncio.run(retranslate_records(args.fields, args.limit, args.batch_size))
