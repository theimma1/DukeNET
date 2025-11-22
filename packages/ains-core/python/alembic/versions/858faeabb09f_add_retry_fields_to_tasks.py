"""add_retry_fields_to_tasks

Revision ID: 858faeabb09f
Revises: f4c81af9a9ba
Create Date: 2025-11-22 11:53:54.479533

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '858faeabb09f'
down_revision: Union[str, Sequence[str], None] = 'f4c81af9a9ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# alembic/versions/XXXXX_add_retry_fields_to_tasks.py

def upgrade():
    op.add_column('tasks', sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False))
    op.add_column('tasks', sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False))
    op.add_column('tasks', sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('tasks', sa.Column('retry_policy', sa.String(), server_default='exponential', nullable=False))
    op.add_column('tasks', sa.Column('last_error', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('tasks', 'last_error')
    op.drop_column('tasks', 'retry_policy')
    op.drop_column('tasks', 'next_retry_at')
    op.drop_column('tasks', 'retry_count')
    op.drop_column('tasks', 'max_retries')
