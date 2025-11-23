"""add_security_tables

Revision ID: cd1654383490
Revises: fda55fe08263
Create Date: 2025-11-23 11:41:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'cd1654383490'
down_revision = 'fda55fe08263'
branch_labels = None
depends_on = None


def upgrade():
    # Create new security tables
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_id', sa.String(length=64), nullable=False),
        sa.Column('key_hash', sa.String(length=128), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        sa.Column('rate_limit_per_hour', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        sa.Column('description', sa.String(length=512), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_keys_client_active', 'api_keys', ['client_id', 'active'], unique=False)
    op.create_index('idx_api_keys_key_id', 'api_keys', ['key_id'], unique=False)
    op.create_index(op.f('ix_api_keys_client_id'), 'api_keys', ['client_id'], unique=False)
    op.create_index(op.f('ix_api_keys_id'), 'api_keys', ['id'], unique=False)
    op.create_index(op.f('ix_api_keys_key_id'), 'api_keys', ['key_id'], unique=True)
    
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=True),
        sa.Column('key_id', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=128), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('extra_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_logs_client_event', 'audit_logs', ['client_id', 'event_type'], unique=False)
    op.create_index('idx_audit_logs_created', 'audit_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_audit_logs_client_id'), 'audit_logs', ['client_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_event_type'), 'audit_logs', ['event_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    
    op.create_table('rate_limit_tracker',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key_id', sa.String(length=64), nullable=False),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_type', sa.String(length=20), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['key_id'], ['api_keys.key_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_rate_limit_key_window', 'rate_limit_tracker', ['key_id', 'window_start', 'window_type'], unique=False)
    op.create_index(op.f('ix_rate_limit_tracker_id'), 'rate_limit_tracker', ['id'], unique=False)
    op.create_index(op.f('ix_rate_limit_tracker_key_id'), 'rate_limit_tracker', ['key_id'], unique=False)
    
    # Add new columns to agents table (SQLite compatible)
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.add_column(sa.Column('endpoint', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('signature', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('tags', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index(batch_op.f('ix_agents_agent_id'), ['agent_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_agents_id'), ['id'], unique=False)
        batch_op.drop_column('status')
        batch_op.drop_column('endpoint_url')
        batch_op.drop_column('owner_address')
        batch_op.drop_column('description')
        batch_op.drop_column('version')
        batch_op.drop_column('last_heartbeat')
        batch_op.drop_column('avatar_url')
    
    # Add new columns to tasks table (SQLite compatible)
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timeout_seconds', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('cancelled_by', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('cancellation_reason', sa.String(length=512), nullable=True))


def downgrade():
    # Remove new columns from tasks
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('cancellation_reason')
        batch_op.drop_column('cancelled_by')
        batch_op.drop_column('cancelled_at')
        batch_op.drop_column('timeout_seconds')
    
    # Remove new columns from agents
    with op.batch_alter_table('agents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_agents_id'))
        batch_op.drop_index(batch_op.f('ix_agents_agent_id'))
        batch_op.add_column(sa.Column('avatar_url', sa.VARCHAR(length=512), nullable=True))
        batch_op.add_column(sa.Column('last_heartbeat', sa.DATETIME(), nullable=True))
        batch_op.add_column(sa.Column('version', sa.VARCHAR(length=32), nullable=True))
        batch_op.add_column(sa.Column('description', sa.VARCHAR(length=512), nullable=True))
        batch_op.add_column(sa.Column('owner_address', sa.VARCHAR(length=128), nullable=True))
        batch_op.add_column(sa.Column('endpoint_url', sa.VARCHAR(length=512), nullable=True))
        batch_op.add_column(sa.Column('status', sa.VARCHAR(length=32), nullable=True))
        batch_op.drop_column('updated_at')
        batch_op.drop_column('last_seen_at')
        batch_op.drop_column('tags')
        batch_op.drop_column('signature')
        batch_op.drop_column('endpoint')
    
    # Drop security tables
    op.drop_index(op.f('ix_rate_limit_tracker_key_id'), table_name='rate_limit_tracker')
    op.drop_index(op.f('ix_rate_limit_tracker_id'), table_name='rate_limit_tracker')
    op.drop_index('idx_rate_limit_key_window', table_name='rate_limit_tracker')
    op.drop_table('rate_limit_tracker')
    
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_event_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_client_id'), table_name='audit_logs')
    op.drop_index('idx_audit_logs_created', table_name='audit_logs')
    op.drop_index('idx_audit_logs_client_event', table_name='audit_logs')
    op.drop_table('audit_logs')
    
    op.drop_index(op.f('ix_api_keys_key_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_client_id'), table_name='api_keys')
    op.drop_index('idx_api_keys_key_id', table_name='api_keys')
    op.drop_index('idx_api_keys_client_active', table_name='api_keys')
    op.drop_table('api_keys')
