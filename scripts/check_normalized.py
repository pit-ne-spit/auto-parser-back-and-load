"""Проверка результатов нормализации."""

import asyncio
import sys
from pathlib import Path

# Настройка кодировки для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database.connection import AsyncSessionLocal
from app.database.models import ProcessedData
from sqlalchemy import select, func
import json


async def main():
    """Проверка результатов нормализации."""
    async with AsyncSessionLocal() as session:
        # Общее количество записей
        count_result = await session.execute(select(func.count(ProcessedData.id)))
        total_count = count_result.scalar()
        print(f"Всего записей в processed_data: {total_count}")
        
        # Получаем несколько примеров
        sample_result = await session.execute(
            select(ProcessedData)
            .limit(3)
        )
        samples = sample_result.scalars().all()
        
        print("\n" + "=" * 80)
        print("Примеры нормализованных данных:")
        print("=" * 80)
        
        for i, record in enumerate(samples, 1):
            print(f"\n--- Запись {i} (inner_id: {record.inner_id}) ---")
            print(f"Марка: {record.mark}")
            print(f"Модель: {record.model}")
            print(f"Год: {record.year}")
            print(f"Цена: {record.price}")
            print(f"Пробег: {record.km_age}")
            print(f"Тип двигателя: {record.engine_type}")
            print(f"Тип КПП: {record.transmission_type}")
            print(f"Тип кузова: {record.body_type}")
            print(f"Адрес: {record.address}")
            print(f"Опций: {len(record.options) if record.options else 0}")
            if record.options:
                print(f"  Примеры опций: {', '.join(record.options[:3])}")
            print(f"Параметров конфигурации: {len(record.configuration) if record.configuration else 0}")
            if record.configuration:
                config_keys = list(record.configuration.keys())[:5]
                print(f"  Примеры ID параметров: {', '.join(config_keys)}")
                if config_keys:
                    first_key = config_keys[0]
                    print(f"  Параметр {first_key}: {record.configuration[first_key]}")


if __name__ == "__main__":
    asyncio.run(main())
