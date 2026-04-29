"""add character_reference_images table + detailed_description + character_angles

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create character_reference_images table
    op.create_table(
        'character_reference_images',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('character_id', sa.Integer(), nullable=False),
        sa.Column('angle', sa.String(length=20), nullable=False),
        sa.Column('image_path', sa.String(length=500), nullable=True),
        sa.Column('prompt_cn', sa.Text(), nullable=True),
        sa.Column('prompt_en', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('character_id', 'angle', name='uq_char_ref_angle'),
    )

    # 2. Add detailed_description to characters
    op.add_column('characters', sa.Column('detailed_description', sa.Text(), nullable=True))

    # 3. Add character_angles to shots
    op.add_column('shots', sa.Column('character_angles', sa.String(length=500), nullable=True))

    # 4. Data migration: create front reference for characters with existing reference_image_path
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT INTO character_reference_images (character_id, angle, image_path, status, created_at, updated_at) "
            "SELECT id, 'front', reference_image_path, 'completed', "
            ":now, :now "
            "FROM characters WHERE reference_image_path IS NOT NULL"
        ),
        {"now": datetime.utcnow()},
    )


def downgrade() -> None:
    op.drop_table('character_reference_images')
    op.drop_column('characters', 'detailed_description')
    op.drop_column('shots', 'character_angles')
