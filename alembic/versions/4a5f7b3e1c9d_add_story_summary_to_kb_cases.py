"""add story_summary to kb_cases

Revision ID: 4a5f7b3e1c9d
Revises: 3c4cfad6bbde
Create Date: 2026-04-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a5f7b3e1c9d'
down_revision: Union[str, None] = '3c4cfad6bbde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('kb_cases', sa.Column('story_summary', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('kb_cases', 'story_summary')
