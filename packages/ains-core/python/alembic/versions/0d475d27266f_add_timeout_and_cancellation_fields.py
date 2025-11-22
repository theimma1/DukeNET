"""add_timeout_and_cancellation_fields

Revision ID: 0d475d27266f
Revises: 858faeabb09f
Create Date: 2025-11-22 13:00:27.260660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d475d27266f'
down_revision: Union[str, Sequence[str], None] = '858faeabb09f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
