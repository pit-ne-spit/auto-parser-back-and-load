"""Database models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Date, BigInteger,
    Index, UniqueConstraint, Float
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class RawData(Base):
    """Raw data from CHE168 API."""
    
    __tablename__ = "raw_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    inner_id = Column(String, unique=True, nullable=False, index=True)
    change_type = Column(String, nullable=False)  # "added", "changed", "removed"
    created_at = Column(DateTime, nullable=False)  # Date from API
    data = Column(JSONB, nullable=False)  # Full offer data as JSON
    first_loaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String, nullable=False)  # "initial_load" or "daily_update"
    active_status = Column(Integer, nullable=False, default=0)  # 0 = active, 1 = inactive
    is_processed = Column(Boolean, nullable=False, default=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_raw_data_active_status', 'active_status'),
        Index('idx_raw_data_is_processed', 'is_processed'),
        Index('idx_raw_data_source', 'source'),
        Index('idx_raw_data_last_updated_at', 'last_updated_at'),
    )


class ProcessedData(Base):
    """Normalized data from raw_data."""
    
    __tablename__ = "processed_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    inner_id = Column(String, nullable=False, index=True)  # Link to raw_data by inner_id
    active_status = Column(Integer, nullable=False, default=0)  # 0 = active, 1 = inactive
    created_at = Column(DateTime, nullable=False)  # Date from raw_data.created_at
    
    # Basic fields from data block
    url = Column(String, nullable=True)
    mark = Column(String, nullable=True, index=True)  # Марка автомобиля
    model = Column(String, nullable=True, index=True)  # Модель автомобиля
    year = Column(Integer, nullable=True, index=True)  # Год выпуска
    color = Column(String, nullable=True)
    price = Column(Integer, nullable=True, index=True)  # Цена в юанях
    km_age = Column(Integer, nullable=True, index=True)  # Пробег в км
    engine_type = Column(String, nullable=True, index=True)  # Тип двигателя
    transmission_type = Column(String, nullable=True, index=True)  # Тип КПП
    body_type = Column(String, nullable=True, index=True)  # Тип кузова
    address = Column(String, nullable=True)
    section = Column(String, nullable=True, index=True)  # б/у или новый
    offer_created = Column(Date, nullable=True)  # Дата создания объявления
    displacement = Column(Float, nullable=True)  # Объем двигателя в литрах
    vin = Column(String, nullable=True)
    first_registration = Column(Date, nullable=True)  # Дата первой регистрации
    power = Column(Integer, nullable=True)  # Мощность в л.с.
    drive_type = Column(String, nullable=True)  # Тип привода
    
    # JSONB fields for complex data
    description = Column(Text, nullable=True)  # Описание автомобиля
    images = Column(JSONB, nullable=True)  # Массив URL изображений
    options = Column(JSONB, nullable=True)  # Массив названий опций из extra.option
    configuration = Column(JSONB, nullable=True)  # Параметры конфигурации по ID
    
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_processed_data_inner_id', 'inner_id'),
        Index('idx_processed_data_active_status', 'active_status'),
        Index('idx_processed_data_mark', 'mark'),
        Index('idx_processed_data_model', 'model'),
        Index('idx_processed_data_year', 'year'),
        Index('idx_processed_data_price', 'price'),
        Index('idx_processed_data_km_age', 'km_age'),
        Index('idx_processed_data_engine_type', 'engine_type'),
        Index('idx_processed_data_transmission_type', 'transmission_type'),
        Index('idx_processed_data_body_type', 'body_type'),
        Index('idx_processed_data_section', 'section'),
        # GIN index for JSONB fields (will be created in migration)
    )


class ApiToken(Base):
    """API tokens for authentication."""
    
    __tablename__ = "api_tokens"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(16), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # NULL if unlimited
    description = Column(String, nullable=True)
    last_used_at = Column(DateTime, nullable=True)


class OperationsLog(Base):
    """Logs of data operations."""
    
    __tablename__ = "operations_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_type = Column(String, nullable=False)  # "data_fetch" or "normalization"
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    duration = Column(Integer, nullable=False)  # Duration in seconds
    status = Column(String, nullable=False)  # "OK" or "ERROR"
    details = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_operations_log_operation_type', 'operation_type'),
        Index('idx_operations_log_started_at', 'started_at'),
        Index('idx_operations_log_status', 'status'),
    )


class SyncState(Base):
    """Synchronization state for tracking updates."""
    
    __tablename__ = "sync_state"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    last_successful_date = Column(Date, nullable=False, index=True)
    last_change_id = Column(BigInteger, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Only one record should exist
    __table_args__ = (
        UniqueConstraint('id', name='uq_sync_state_single_record'),
    )
