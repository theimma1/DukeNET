"""add_performance_indexes

Revision ID: 5621bab17f7d
Revises: 48a2995fc42f
Create Date: 2025-11-22 13:36:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '5621bab17f7d'
down_revision = '48a2995fc42f'
branch_labels = None
depends_on = None


def index_exists(conn, index_name, table_name):
    """Check if an index exists"""
    try:
        inspector = inspect(conn)
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)
    except:
        return False


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Task indexes (tasks table should always exist)
    if 'tasks' in existing_tables:
        if not index_exists(conn, 'idx_tasks_status', 'tasks'):
            op.create_index('idx_tasks_status', 'tasks', ['status'])
        if not index_exists(conn, 'idx_tasks_client_id', 'tasks'):
            op.create_index('idx_tasks_client_id', 'tasks', ['client_id'])
        if not index_exists(conn, 'idx_tasks_assigned_agent_id', 'tasks'):
            op.create_index('idx_tasks_assigned_agent_id', 'tasks', ['assigned_agent_id'])
        if not index_exists(conn, 'idx_tasks_capability_required', 'tasks'):
            op.create_index('idx_tasks_capability_required', 'tasks', ['capability_required'])
        if not index_exists(conn, 'idx_tasks_priority_created', 'tasks'):
            op.create_index('idx_tasks_priority_created', 'tasks', ['priority', 'created_at'])
        if not index_exists(conn, 'idx_tasks_status_priority', 'tasks'):
            op.create_index('idx_tasks_status_priority', 'tasks', ['status', 'priority'])
    
    # Agent indexes
    if 'agents' in existing_tables:
        if not index_exists(conn, 'idx_agents_trust_score', 'agents'):
            op.create_index('idx_agents_trust_score', 'agents', ['trust_score'])
    
    # Capability indexes (only if table exists)
    if 'capabilities' in existing_tables:
        if not index_exists(conn, 'idx_capabilities_agent_id', 'capabilities'):
            op.create_index('idx_capabilities_agent_id', 'capabilities', ['agent_id'])
        if not index_exists(conn, 'idx_capabilities_name', 'capabilities'):
            op.create_index('idx_capabilities_name', 'capabilities', ['name'])
    
    # Webhook indexes
    if 'webhooks' in existing_tables:
        if not index_exists(conn, 'idx_webhooks_agent_id', 'webhooks'):
            op.create_index('idx_webhooks_agent_id', 'webhooks', ['agent_id'])
        if not index_exists(conn, 'idx_webhooks_active', 'webhooks'):
            op.create_index('idx_webhooks_active', 'webhooks', ['active'])
    
    # Webhook delivery indexes
    if 'webhook_deliveries' in existing_tables:
        if not index_exists(conn, 'idx_webhook_deliveries_webhook_id', 'webhook_deliveries'):
            op.create_index('idx_webhook_deliveries_webhook_id', 'webhook_deliveries', ['webhook_id'])
        if not index_exists(conn, 'idx_webhook_deliveries_status', 'webhook_deliveries'):
            op.create_index('idx_webhook_deliveries_status', 'webhook_deliveries', ['status'])


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop all indexes (only if tables exist)
    if 'webhook_deliveries' in existing_tables:
        if index_exists(conn, 'idx_webhook_deliveries_status', 'webhook_deliveries'):
            op.drop_index('idx_webhook_deliveries_status', table_name='webhook_deliveries')
        if index_exists(conn, 'idx_webhook_deliveries_webhook_id', 'webhook_deliveries'):
            op.drop_index('idx_webhook_deliveries_webhook_id', table_name='webhook_deliveries')
    
    if 'webhooks' in existing_tables:
        if index_exists(conn, 'idx_webhooks_active', 'webhooks'):
            op.drop_index('idx_webhooks_active', table_name='webhooks')
        if index_exists(conn, 'idx_webhooks_agent_id', 'webhooks'):
            op.drop_index('idx_webhooks_agent_id', table_name='webhooks')
    
    if 'capabilities' in existing_tables:
        if index_exists(conn, 'idx_capabilities_name', 'capabilities'):
            op.drop_index('idx_capabilities_name', table_name='capabilities')
        if index_exists(conn, 'idx_capabilities_agent_id', 'capabilities'):
            op.drop_index('idx_capabilities_agent_id', table_name='capabilities')
    
    if 'agents' in existing_tables:
        if index_exists(conn, 'idx_agents_trust_score', 'agents'):
            op.drop_index('idx_agents_trust_score', table_name='agents')
    
    if 'tasks' in existing_tables:
        if index_exists(conn, 'idx_tasks_status_priority', 'tasks'):
            op.drop_index('idx_tasks_status_priority', table_name='tasks')
        if index_exists(conn, 'idx_tasks_priority_created', 'tasks'):
            op.drop_index('idx_tasks_priority_created', table_name='tasks')
        if index_exists(conn, 'idx_tasks_capability_required', 'tasks'):
            op.drop_index('idx_tasks_capability_required', table_name='tasks')
        if index_exists(conn, 'idx_tasks_assigned_agent_id', 'tasks'):
            op.drop_index('idx_tasks_assigned_agent_id', table_name='tasks')
        if index_exists(conn, 'idx_tasks_client_id', 'tasks'):
            op.drop_index('idx_tasks_client_id', table_name='tasks')
        if index_exists(conn, 'idx_tasks_status', 'tasks'):
            op.drop_index('idx_tasks_status', table_name='tasks')
