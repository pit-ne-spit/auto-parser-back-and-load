"""add_normalized_fields_to_processed_data

Revision ID: 5cde61592795
Revises: 9e5b5b4d7461
Create Date: 2026-02-06 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5cde61592795'
down_revision: Union[str, None] = '9e5b5b4d7461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Удаляем старое поле normalized_data (если оно есть)
    # Проверяем существование колонки перед удалением
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('processed_data')]
    if 'normalized_data' in columns:
        op.drop_column('processed_data', 'normalized_data')
    
    # Изменяем created_at - убираем default, так как будем брать из raw_data
    op.alter_column('processed_data', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=None)
    
    # Добавляем базовые поля из блока data
    op.add_column('processed_data', sa.Column('url', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('mark', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('model', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('year', sa.Integer(), nullable=True))
    op.add_column('processed_data', sa.Column('color', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('price', sa.Integer(), nullable=True))
    op.add_column('processed_data', sa.Column('km_age', sa.Integer(), nullable=True))
    op.add_column('processed_data', sa.Column('engine_type', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('transmission_type', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('body_type', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('address', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('section', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('displacement', sa.Float(), nullable=True))
    op.add_column('processed_data', sa.Column('vin', sa.String(), nullable=True))
    op.add_column('processed_data', sa.Column('first_registration', sa.Date(), nullable=True))
    op.add_column('processed_data', sa.Column('power', sa.Integer(), nullable=True))
    op.add_column('processed_data', sa.Column('drive_type', sa.String(), nullable=True))
    
    # Добавляем JSONB поля
    op.add_column('processed_data', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('processed_data', sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('processed_data', sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('processed_data', sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Создаем индексы для часто используемых полей
    op.create_index('idx_processed_data_mark', 'processed_data', ['mark'], unique=False)
    op.create_index('idx_processed_data_model', 'processed_data', ['model'], unique=False)
    op.create_index('idx_processed_data_year', 'processed_data', ['year'], unique=False)
    op.create_index('idx_processed_data_price', 'processed_data', ['price'], unique=False)
    op.create_index('idx_processed_data_km_age', 'processed_data', ['km_age'], unique=False)
    op.create_index('idx_processed_data_engine_type', 'processed_data', ['engine_type'], unique=False)
    op.create_index('idx_processed_data_transmission_type', 'processed_data', ['transmission_type'], unique=False)
    op.create_index('idx_processed_data_body_type', 'processed_data', ['body_type'], unique=False)
    op.create_index('idx_processed_data_section', 'processed_data', ['section'], unique=False)
    
    # Создаем GIN индексы для JSONB полей (для быстрого поиска внутри JSONB)
    op.execute('CREATE INDEX idx_processed_data_options_gin ON processed_data USING GIN (options)')
    op.execute('CREATE INDEX idx_processed_data_configuration_gin ON processed_data USING GIN (configuration)')


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем GIN индексы
    op.execute('DROP INDEX IF EXISTS idx_processed_data_configuration_gin')
    op.execute('DROP INDEX IF EXISTS idx_processed_data_options_gin')
    
    # Удаляем обычные индексы
    op.drop_index('idx_processed_data_section', table_name='processed_data')
    op.drop_index('idx_processed_data_body_type', table_name='processed_data')
    op.drop_index('idx_processed_data_transmission_type', table_name='processed_data')
    op.drop_index('idx_processed_data_engine_type', table_name='processed_data')
    op.drop_index('idx_processed_data_km_age', table_name='processed_data')
    op.drop_index('idx_processed_data_price', table_name='processed_data')
    op.drop_index('idx_processed_data_year', table_name='processed_data')
    op.drop_index('idx_processed_data_model', table_name='processed_data')
    op.drop_index('idx_processed_data_mark', table_name='processed_data')
    
    # Удаляем JSONB поля
    op.drop_column('processed_data', 'configuration')
    op.drop_column('processed_data', 'options')
    op.drop_column('processed_data', 'images')
    op.drop_column('processed_data', 'description')
    
    # Удаляем базовые поля
    op.drop_column('processed_data', 'drive_type')
    op.drop_column('processed_data', 'power')
    op.drop_column('processed_data', 'first_registration')
    op.drop_column('processed_data', 'vin')
    op.drop_column('processed_data', 'displacement')
    op.drop_column('processed_data', 'section')
    op.drop_column('processed_data', 'address')
    op.drop_column('processed_data', 'body_type')
    op.drop_column('processed_data', 'transmission_type')
    op.drop_column('processed_data', 'engine_type')
    op.drop_column('processed_data', 'km_age')
    op.drop_column('processed_data', 'price')
    op.drop_column('processed_data', 'color')
    op.drop_column('processed_data', 'year')
    op.drop_column('processed_data', 'model')
    op.drop_column('processed_data', 'mark')
    op.drop_column('processed_data', 'url')
    
    # Восстанавливаем старое поле normalized_data
    op.add_column('processed_data', sa.Column('normalized_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    
    # Восстанавливаем default для created_at
    op.alter_column('processed_data', 'created_at',
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.text('CURRENT_TIMESTAMP'))
