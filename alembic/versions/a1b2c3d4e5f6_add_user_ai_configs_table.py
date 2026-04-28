"""add user_ai_configs table

Revision ID: a1b2c3d4e5f6
Revises: 05b2f5b6e18e
Create Date: 2026-04-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '05b2f5b6e18e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_ai_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('config_name', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('service_type', sa.String(length=30), nullable=False),
        sa.Column('api_base_url', sa.String(length=500), nullable=True),
        sa.Column('encrypted_api_key', sa.String(length=500), nullable=True),
        sa.Column('api_key_hint', sa.String(length=100), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('extra_config', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_ai_configs_user_id', 'user_ai_configs', ['user_id'])
    op.create_index('ix_user_ai_configs_user_service', 'user_ai_configs', ['user_id', 'service_type'])


def downgrade() -> None:
    op.drop_index('ix_user_ai_configs_user_service', table_name='user_ai_configs')
    op.drop_index('ix_user_ai_configs_user_id', table_name='user_ai_configs')
    op.drop_table('user_ai_configs')
