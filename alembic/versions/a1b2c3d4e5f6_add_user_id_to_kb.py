"""add_user_id_to_kb

Revision ID: a1b2c3d4e5f6
Revises: 4a5f7b3e1c9d
Create Date: 2026-04-22 00:50:48.226591

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '4a5f7b3e1c9d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("kb_cases") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_kb_cases_user_id", "users", ["user_id"], ["id"])

    with op.batch_alter_table("kb_script_templates") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key("fk_kb_script_templates_user_id", "users", ["user_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("kb_script_templates") as batch_op:
        batch_op.drop_constraint("fk_kb_script_templates_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("kb_cases") as batch_op:
        batch_op.drop_constraint("fk_kb_cases_user_id", type_="foreignkey")
        batch_op.drop_column("user_id")
