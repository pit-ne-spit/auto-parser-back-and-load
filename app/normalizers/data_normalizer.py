"""Data normalizer for processing raw_data into processed_data."""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import select

from app.normalizers.base_normalizer import BaseNormalizer
from app.database.connection import AsyncSessionLocal
from app.database.models import RawData, ProcessedData
from app.utils.config import config
from app.utils.logger import logger
from app.utils.progress import ProgressBar
from app.utils.translator import translate_field


class DataNormalizer(BaseNormalizer):
    """Normalizer for processing raw_data into processed_data."""
    
    def __init__(self, batch_size: Optional[int] = None):
        """
        Initialize data normalizer.
        
        Args:
            batch_size: Number of records per batch (default from config)
        """
        super().__init__("normalization")
        batch_config = config.get_batch_config()
        self.batch_size = batch_size or batch_config.get('normalization_size', 200)
    
    async def normalize(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Normalize all unprocessed records from raw_data.
        
        Args:
            limit: Optional limit on number of records to process (for testing)
        
        Returns:
            Dictionary with statistics: total_processed, total_errors, total_batches
        """
        await self.start_operation()
        
        stats = {
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'total_batches': 0
        }
        
        try:
            # Get total count of unprocessed records
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(RawData.id).where(RawData.is_processed == False)
                )
                total_count = len(result.scalars().all())
            
            if total_count == 0:
                logger.info("No unprocessed records found")
                await self.finish_operation("OK")
                return stats
            
            # Apply limit if specified
            target_count = min(total_count, limit) if limit else total_count
            
            if limit and limit < total_count:
                logger.info(f"Found {total_count} unprocessed records, processing {target_count} (limit: {limit})")
            else:
                logger.info(f"Found {total_count} unprocessed records to normalize")
            
            # Initialize progress bar
            progress = ProgressBar(
                total=target_count,
                description="Normalization",
                update_interval=1.0
            )
            
            # Process records in batches
            offset = 0
            while True:
                # Check if we've reached the limit
                if limit and stats['total_processed'] >= limit:
                    logger.info(f"Reached limit of {limit} records, stopping")
                    break
                
                # Adjust batch size if we're near the limit
                remaining = limit - stats['total_processed'] if limit else None
                if remaining and remaining < self.batch_size:
                    # Process smaller batch for the last iteration
                    original_batch_size = self.batch_size
                    self.batch_size = remaining
                    batch_stats = await self._process_batch(offset)
                    self.batch_size = original_batch_size
                else:
                    batch_stats = await self._process_batch(offset)
                
                if batch_stats['processed'] == 0:
                    break
                
                stats['total_processed'] += batch_stats['processed']
                stats['total_created'] += batch_stats['created']
                stats['total_updated'] += batch_stats['updated']
                stats['total_errors'] += batch_stats['errors']
                stats['total_batches'] += 1
                
                # Update progress
                progress.update(batch_stats['processed'])
                
                # Move to next batch
                offset += self.batch_size
                
                # Log batch completion
                logger.debug(
                    f"Batch {stats['total_batches']}: "
                    f"processed={batch_stats['processed']}, "
                    f"created={batch_stats['created']}, "
                    f"updated={batch_stats['updated']}, "
                    f"errors={batch_stats['errors']}"
                )
            
            progress.finish()
            
            await self.finish_operation(
                "ERROR" if stats['total_errors'] > 0 else "OK"
            )
            
            logger.info(
                f"Normalization completed: "
                f"processed={stats['total_processed']}, "
                f"created={stats['total_created']}, "
                f"updated={stats['total_updated']}, "
                f"errors={stats['total_errors']}, "
                f"batches={stats['total_batches']}"
            )
            
            return stats
            
        except Exception as e:
            self.record_error(e, "normalization")
            await self.finish_operation("ERROR")
            raise
    
    async def _process_batch(self, offset: int) -> Dict[str, int]:
        """
        Process a batch of records.
        
        Args:
            offset: Offset for batch selection
            
        Returns:
            Dictionary with batch statistics
        """
        stats = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        async with AsyncSessionLocal() as session:
            records = []
            try:
                # Fetch batch of unprocessed records
                result = await session.execute(
                    select(RawData)
                    .where(RawData.is_processed == False)
                    .order_by(RawData.id)
                    .limit(self.batch_size)
                    .offset(offset)
                )
                records = result.scalars().all()
                
                if not records:
                    return stats
                
                # Process each record in transaction
                # Обрабатываем каждую запись отдельно, чтобы ошибка в одной не влияла на остальные
                for raw_record in records:
                    try:
                        # Normalize the record - получаем словарь с полями для сохранения
                        normalized_fields = self._normalize_record(raw_record.data)
                        
                        # Добавляем inner_id для валидации
                        normalized_fields['inner_id'] = raw_record.inner_id
                        
                        # Валидация данных перед сохранением
                        if not self._validate_normalized_data(normalized_fields):
                            logger.warning(f"Skipping record inner_id={raw_record.inner_id} due to validation failure")
                            stats['errors'] += 1
                            continue
                        
                        # Удаляем inner_id из normalized_fields, так как он уже есть в raw_record
                        normalized_fields.pop('inner_id', None)
                        
                        # Check if processed_data already exists
                        existing = await session.execute(
                            select(ProcessedData)
                            .where(ProcessedData.inner_id == raw_record.inner_id)
                        )
                        processed_record = existing.scalar_one_or_none()
                        
                        if processed_record:
                            # Update existing record - обновляем все поля
                            for field, value in normalized_fields.items():
                                setattr(processed_record, field, value)
                            processed_record.active_status = raw_record.active_status
                            processed_record.updated_at = datetime.utcnow()
                            stats['updated'] += 1
                        else:
                            # Create new record - создаем с всеми полями
                            processed_record = ProcessedData(
                                inner_id=raw_record.inner_id,
                                active_status=raw_record.active_status,
                                created_at=raw_record.created_at,
                                **normalized_fields
                            )
                            session.add(processed_record)
                            stats['created'] += 1
                        
                        # Mark raw_record as processed
                        raw_record.is_processed = True
                        stats['processed'] += 1
                        
                    except Exception as e:
                        # Если ошибка в отдельной записи - логируем и пропускаем её
                        # Остальные записи продолжают обрабатываться
                        self.record_error(e, f"record inner_id={raw_record.inner_id if raw_record else 'unknown'}")
                        stats['errors'] += 1
                        # Запись остается с is_processed = False для повторной обработки
                        logger.warning(
                            f"Skipping record inner_id={raw_record.inner_id if raw_record else 'unknown'} "
                            f"due to error: {str(e)}"
                        )
                        continue
                
                # Commit transaction для всех успешно обработанных записей
                try:
                    await session.commit()
                except Exception as e:
                    # Если ошибка при коммите - откатываем весь батч
                    await session.rollback()
                    self.record_error(e, f"commit batch at offset {offset}")
                    # Помечаем все записи как необработанные
                    stats['errors'] += len(records)
                    stats['processed'] = 0
                    stats['created'] = 0
                    stats['updated'] = 0
                    
            except Exception as e:
                # Rollback entire batch on error
                self.record_error(e, f"batch at offset {offset}")
                stats['errors'] += len(records)  # Count all records in batch as errors
                stats['processed'] = 0
                stats['created'] = 0
                stats['updated'] = 0
        
        return stats
    
    def _validate_normalized_data(self, normalized: Dict[str, Any]) -> bool:
        """
        Validate normalized data before saving.
        
        Args:
            normalized: Dictionary with normalized fields
            
        Returns:
            True if data is valid, False otherwise
        """
        # Проверяем обязательные поля
        if not normalized.get('inner_id'):
            logger.warning("Missing inner_id in normalized data")
            return False
        
        # Проверяем разумность числовых значений
        if normalized.get('year'):
            year = normalized['year']
            if not (1900 <= year <= datetime.now().year + 1):
                logger.warning(f"Invalid year: {year}")
                return False
        
        if normalized.get('price'):
            price = normalized['price']
            if price < 0 or price > 100000000:  # Максимальная цена 100 млн юаней
                logger.warning(f"Invalid price: {price}")
                return False
        
        if normalized.get('km_age'):
            km_age = normalized['km_age']
            if km_age < 0 or km_age > 10000000:  # Максимальный пробег 10 млн км
                logger.warning(f"Invalid km_age: {km_age}")
                return False
        
        if normalized.get('power'):
            power = normalized['power']
            if power < 0 or power > 10000:  # Максимальная мощность 10000 л.с.
                logger.warning(f"Invalid power: {power}")
                return False
        
        if normalized.get('displacement'):
            displacement = normalized['displacement']
            if displacement < 0 or displacement > 20:  # Максимальный объем 20 литров
                logger.warning(f"Invalid displacement: {displacement}")
                return False
        
        return True
    
    def _normalize_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single record from raw_data.
        
        Extracts and normalizes key fields from the raw JSON data according to requirements:
        - Basic fields from data block
        - Options list from extra.option
        - Configuration parameters by specific IDs
        
        Args:
            raw_data: Raw data dictionary from raw_data.data field
            
        Returns:
            Dictionary with field names matching ProcessedData model columns
        """
        normalized = {}
        
        # Список ID параметров конфигурации для извлечения
        CONFIG_PARAM_IDS = {93, 91, 90, 88, 116, 101, 108, 92, 115, 97, 95, 38, 58, 3, 13, 6, 11, 14, 17, 20, 24, 23, 41, 40, 42, 46, 43, 44, 47, 48, 49, 50, 53}
        
        # 1. Извлекаем базовые поля из блока data
        # URL
        normalized['url'] = raw_data.get('url')
        
        # Марка и модель
        normalized['mark'] = translate_field(raw_data.get('mark')) if raw_data.get('mark') else None
        normalized['model'] = translate_field(raw_data.get('model')) if raw_data.get('model') else None
        
        # Год
        year = raw_data.get('year')
        if year:
            try:
                if isinstance(year, str):
                    year = ''.join(c for c in year if c.isdigit())
                    normalized['year'] = int(year) if year else None
                else:
                    normalized['year'] = int(year)
            except (ValueError, TypeError):
                normalized['year'] = None
        else:
            normalized['year'] = None
        
        # Цвет
        normalized['color'] = translate_field(raw_data.get('color')) if raw_data.get('color') else None
        
        # Цена
        price = raw_data.get('price')
        if price:
            try:
                if isinstance(price, str):
                    price = ''.join(c for c in price if c.isdigit())
                    normalized['price'] = int(price) if price else None
                else:
                    normalized['price'] = int(price)
            except (ValueError, TypeError):
                normalized['price'] = None
        else:
            normalized['price'] = None
        
        # Пробег
        km_age = raw_data.get('km_age')
        if km_age:
            try:
                if isinstance(km_age, str):
                    km_age = ''.join(c for c in km_age if c.isdigit())
                    normalized['km_age'] = int(km_age) if km_age else None
                else:
                    normalized['km_age'] = int(km_age)
            except (ValueError, TypeError):
                normalized['km_age'] = None
        else:
            normalized['km_age'] = None
        
        # Тип двигателя, КПП, кузова
        normalized['engine_type'] = translate_field(raw_data.get('engine_type')) if raw_data.get('engine_type') else None
        normalized['transmission_type'] = translate_field(raw_data.get('transmission_type')) if raw_data.get('transmission_type') else None
        normalized['body_type'] = translate_field(raw_data.get('body_type')) if raw_data.get('body_type') else None
        
        # Адрес
        normalized['address'] = translate_field(raw_data.get('address')) if raw_data.get('address') else None
        
        # Секция (б/у или новый)
        normalized['section'] = translate_field(raw_data.get('section')) if raw_data.get('section') else None
        
        # Дата создания объявления
        offer_created = raw_data.get('offer_created')
        if offer_created:
            try:
                if isinstance(offer_created, str):
                    # Парсим формат "2025-04-13" или "2025-04"
                    if len(offer_created) == 7 and offer_created[4] == '-':
                        # Формат "YYYY-MM", добавляем день
                        offer_created = f"{offer_created}-01"
                    normalized['offer_created'] = datetime.strptime(offer_created, '%Y-%m-%d').date()
                elif isinstance(offer_created, datetime):
                    normalized['offer_created'] = offer_created.date()
                else:
                    normalized['offer_created'] = offer_created
            except (ValueError, TypeError):
                normalized['offer_created'] = None
        else:
            normalized['offer_created'] = None
        
        # Описание
        normalized['description'] = translate_field(raw_data.get('description')) if raw_data.get('description') else None
        
        # Объем двигателя
        displacement = raw_data.get('displacement')
        if displacement:
            try:
                if isinstance(displacement, str):
                    displacement = ''.join(c for c in displacement if c.isdigit() or c == '.')
                    normalized['displacement'] = float(displacement) if displacement else None
                else:
                    normalized['displacement'] = float(displacement)
            except (ValueError, TypeError):
                normalized['displacement'] = None
        else:
            normalized['displacement'] = None
        
        # VIN
        normalized['vin'] = raw_data.get('vin')
        
        # Дата первой регистрации
        first_registration = raw_data.get('first_registration')
        if first_registration:
            try:
                if isinstance(first_registration, str):
                    # Парсим формат "2019-02" или "2019-02-15"
                    if len(first_registration) == 7 and first_registration[4] == '-':
                        # Формат "YYYY-MM", добавляем день
                        first_registration = f"{first_registration}-01"
                    normalized['first_registration'] = datetime.strptime(first_registration, '%Y-%m-%d').date()
                elif isinstance(first_registration, datetime):
                    normalized['first_registration'] = first_registration.date()
                else:
                    normalized['first_registration'] = first_registration
            except (ValueError, TypeError):
                normalized['first_registration'] = None
        else:
            normalized['first_registration'] = None
        
        # Мощность
        power = raw_data.get('power')
        if power:
            try:
                if isinstance(power, str):
                    power = ''.join(c for c in power if c.isdigit())
                    normalized['power'] = int(power) if power else None
                else:
                    normalized['power'] = int(power)
            except (ValueError, TypeError):
                normalized['power'] = None
        else:
            normalized['power'] = None
        
        # Тип привода
        normalized['drive_type'] = translate_field(raw_data.get('drive_type')) if raw_data.get('drive_type') else None
        
        # Изображения
        images = raw_data.get('images')
        if images:
            if isinstance(images, str):
                try:
                    normalized['images'] = json.loads(images)
                except json.JSONDecodeError:
                    normalized['images'] = []
            elif isinstance(images, list):
                normalized['images'] = images
            else:
                normalized['images'] = []
        else:
            normalized['images'] = []
        
        # 2. Извлекаем опции из extra.option
        options_list = []
        if 'extra' in raw_data and raw_data['extra']:
            extra = raw_data['extra']
            if 'option' in extra and extra['option']:
                option_data = extra['option']
                
                # Из displayopts
                if 'displayopts' in option_data and isinstance(option_data['displayopts'], list):
                    for opt in option_data['displayopts']:
                        if 'optionname' in opt and opt['optionname']:
                            # Переводим название опции
                            option_name = translate_field(opt['optionname'])
                            if option_name and option_name not in options_list:
                                options_list.append(option_name)
                
                # Из moreoptions
                if 'moreoptions' in option_data and isinstance(option_data['moreoptions'], list):
                    for group in option_data['moreoptions']:
                        if 'opts' in group and isinstance(group['opts'], list):
                            for opt in group['opts']:
                                if 'optionname' in opt and opt['optionname']:
                                    # Переводим название опции
                                    option_name = translate_field(opt['optionname'])
                                    if option_name and option_name not in options_list:
                                        options_list.append(option_name)
        
        normalized['options'] = options_list
        
        # 3. Извлекаем параметры конфигурации по конкретным ID
        configuration_dict = {}
        
        # Configuration может быть в raw_data['configuration'] или в raw_data['extra']['configuration']
        config_data = None
        
        # Сначала проверяем прямое поле configuration
        if 'configuration' in raw_data and raw_data['configuration']:
            config_data = raw_data['configuration']
        # Если нет, проверяем в extra.configuration
        elif 'extra' in raw_data and isinstance(raw_data['extra'], dict):
            if 'configuration' in raw_data['extra'] and raw_data['extra']['configuration']:
                config_data = raw_data['extra']['configuration']
        
        if config_data:
            # Переводим конфигурацию
            config_data_translated = translate_field(config_data)
            
            # Проверяем структуру после перевода
            if isinstance(config_data_translated, dict) and 'paramtypeitems' in config_data_translated:
                paramtypeitems = config_data_translated['paramtypeitems']
                if isinstance(paramtypeitems, list):
                    for param_type in paramtypeitems:
                        if isinstance(param_type, dict) and 'paramitems' in param_type:
                            paramitems = param_type['paramitems']
                            if isinstance(paramitems, list):
                                for param in paramitems:
                                    if isinstance(param, dict):
                                        param_id = param.get('id')
                                        
                                        # Нормализуем ID к int для проверки
                                        param_id_int = None
                                        if param_id is not None:
                                            try:
                                                if isinstance(param_id, str):
                                                    # Пытаемся преобразовать строку в int
                                                    param_id_int = int(param_id)
                                                elif isinstance(param_id, int):
                                                    param_id_int = param_id
                                            except (ValueError, TypeError):
                                                # Если не удалось преобразовать, пропускаем параметр
                                                continue
                                        
                                        # Проверяем, есть ли ID в списке нужных параметров
                                        if param_id_int is not None and param_id_int in CONFIG_PARAM_IDS:
                                            param_name = param.get('name', '')
                                            param_value = param.get('value', '')
                                            # Сохраняем ID как строку для ключа словаря
                                            configuration_dict[str(param_id_int)] = {
                                                'name': param_name,
                                                'value': param_value
                                            }
        
        normalized['configuration'] = configuration_dict if configuration_dict else None
        
        return normalized
    
