"""add_webhook_support

Revision ID: 48a2995fc42f
Revises: 0d475d27266f
Create Date: 2025-11-22 13:28:58.302815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '48a2995fc42f'
down_revision: Union[str, Sequence[str], None] = '0d475d27266f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# alembic/versions/XXXXX_add_webhook_support.py

def upgrade():
    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('webhook_id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('events', sa.String(), nullable=False),  # JSON array of event types
        sa.Column('secret', sa.String(), nullable=True),
        sa.Column('active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('webhook_id')
    )
    
    # Create webhook_deliveries table for tracking
    op.create_table(
        'webhook_deliveries',
        sa.Column('delivery_id', sa.String(), nullable=False),
        sa.Column('webhook_id', sa.String(), nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('payload', sa.String(), nullable=False),  # JSON
        sa.Column('status', sa.String(), nullable=False),  # pending, success, failed
        sa.Column('response_code', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.String(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('delivery_id')
    )

def downgrade():
    op.drop_table('webhook_deliveries')
    op.drop_table('webhooks')
