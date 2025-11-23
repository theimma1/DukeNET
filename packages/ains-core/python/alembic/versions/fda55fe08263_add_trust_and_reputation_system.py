"""add_trust_and_reputation_system

Revision ID: fda55fe08263
Revises: 5621bab17f7d
Create Date: 2025-11-22 13:53:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fda55fe08263'
down_revision = '5621bab17f7d'
branch_labels = None
depends_on = None


def upgrade():
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing columns in agents table
    existing_columns = [col['name'] for col in inspector.get_columns('agents')]
    
    # Add trust fields to agents table (only if they don't exist)
    if 'trust_score' not in existing_columns:
        op.add_column('agents', sa.Column('trust_score', sa.Float(), server_default='0.5', nullable=False))
    if 'total_tasks_completed' not in existing_columns:
        op.add_column('agents', sa.Column('total_tasks_completed', sa.Integer(), server_default='0', nullable=False))
    if 'total_tasks_failed' not in existing_columns:
        op.add_column('agents', sa.Column('total_tasks_failed', sa.Integer(), server_default='0', nullable=False))
    if 'avg_completion_time_seconds' not in existing_columns:
        op.add_column('agents', sa.Column('avg_completion_time_seconds', sa.Float(), nullable=True))
    if 'last_task_completed_at' not in existing_columns:
        op.add_column('agents', sa.Column('last_task_completed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Check if trust_records table exists
    existing_tables = inspector.get_table_names()
    
    # Create trust_records table (only if it doesn't exist)
    if 'trust_records' not in existing_tables:
        op.create_table(
            'trust_records',
            sa.Column('record_id', sa.String(), nullable=False),
            sa.Column('agent_id', sa.String(), nullable=False),
            sa.Column('event_type', sa.String(), nullable=False),
            sa.Column('task_id', sa.String(), nullable=True),
            sa.Column('trust_delta', sa.Float(), nullable=False),
            sa.Column('trust_score_before', sa.Float(), nullable=False),
            sa.Column('trust_score_after', sa.Float(), nullable=False),
            sa.Column('reason', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('record_id')
        )
        
        # Create indexes
        op.create_index('idx_trust_records_agent_id', 'trust_records', ['agent_id'])
        op.create_index('idx_trust_records_created_at', 'trust_records', ['created_at'])


def downgrade():
    op.drop_index('idx_trust_records_created_at', table_name='trust_records')
    op.drop_index('idx_trust_records_agent_id', table_name='trust_records')
    op.drop_table('trust_records')
    
    op.drop_column('agents', 'last_task_completed_at')
    op.drop_column('agents', 'avg_completion_time_seconds')
    op.drop_column('agents', 'total_tasks_failed')
    op.drop_column('agents', 'total_tasks_completed')
    op.drop_column('agents', 'trust_score')
