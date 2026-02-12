"""add_offer_created_to_processed_data

Revision ID: 67daed722540
Revises: 5cde61592795
Create Date: 2026-02-09 11:25:52.399631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '67daed722540'
down_revision: Union[str, Sequence[str], None] = '5cde61592795'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Проверяем существование колонки offer_created перед добавлением
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('processed_data')]
    
    if 'offer_created' not in columns:
        # Добавляем поле offer_created (дата создания объявления)
        op.add_column('processed_data', sa.Column('offer_created', sa.Date(), nullable=True))
    
    # Пересоздаем индексы с правильными именами (ix_ вместо idx_)
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('processed_data')]
    
    # Удаляем старые индексы с префиксом idx_ (кроме GIN индексов)
    old_indexes = [
        'idx_processed_data_body_type',
        'idx_processed_data_engine_type',
        'idx_processed_data_km_age',
        'idx_processed_data_mark',
        'idx_processed_data_model',
        'idx_processed_data_price',
        'idx_processed_data_section',
        'idx_processed_data_transmission_type',
        'idx_processed_data_year'
    ]
    
    for idx_name in old_indexes:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name='processed_data')
    
    # Создаем новые индексы с префиксом ix_ (если их еще нет)
    new_indexes = [
        ('ix_processed_data_body_type', 'body_type'),
        ('ix_processed_data_engine_type', 'engine_type'),
        ('ix_processed_data_km_age', 'km_age'),
        ('ix_processed_data_mark', 'mark'),
        ('ix_processed_data_model', 'model'),
        ('ix_processed_data_price', 'price'),
        ('ix_processed_data_section', 'section'),
        ('ix_processed_data_transmission_type', 'transmission_type'),
        ('ix_processed_data_year', 'year')
    ]
    
    for idx_name, column_name in new_indexes:
        if idx_name not in existing_indexes:
            op.create_index(idx_name, 'processed_data', [column_name], unique=False)
    
    # Проверяем существование ограничения перед созданием через SQL
    from sqlalchemy import text
    result = conn.execute(text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'sync_state' 
        AND constraint_name = 'uq_sync_state_single_record'
    """))
    constraint_exists = result.fetchone() is not None
    
    if not constraint_exists:
        # Создаем уникальное ограничение для sync_state
        op.create_unique_constraint('uq_sync_state_single_record', 'sync_state', ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем уникальное ограничение для sync_state
    op.drop_constraint('uq_sync_state_single_record', 'sync_state', type_='unique')
    
    # Удаляем индексы с именами ix_
    op.drop_index(op.f('ix_processed_data_year'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_transmission_type'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_section'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_price'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_model'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_mark'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_km_age'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_engine_type'), table_name='processed_data')
    op.drop_index(op.f('ix_processed_data_body_type'), table_name='processed_data')
    
    # Восстанавливаем GIN индексы
    op.create_index(op.f('idx_processed_data_options_gin'), 'processed_data', ['options'], unique=False, postgresql_using='gin')
    op.create_index(op.f('idx_processed_data_configuration_gin'), 'processed_data', ['configuration'], unique=False, postgresql_using='gin')
    
    # Удаляем поле offer_created
    op.drop_column('processed_data', 'offer_created')
