"""Prometheus metrics for AINS"""
from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from prometheus_client import REGISTRY
import time
from typing import Callable

# Clear any existing metrics to avoid duplicates
try:
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass
except Exception:
    pass

# ============================================================================
# SYSTEM METRICS
# ============================================================================

# HTTP Request metrics
http_requests_total = Counter(
    'ains_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'ains_http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    'ains_http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)

app_info = Info(
    'ains_application',
    'Application information'
)

# ============================================================================
# TASK METRICS
# ============================================================================

tasks_created_total = Counter(
    'ains_tasks_created_total',
    'Total tasks created',
    ['task_type', 'client_id']
)

tasks_completed_total = Counter(
    'ains_tasks_completed_total',
    'Total tasks completed successfully',
    ['task_type', 'agent_id']
)

tasks_failed_total = Counter(
    'ains_tasks_failed_total',
    'Total tasks failed',
    ['task_type', 'failure_reason']
)

task_duration_seconds = Histogram(
    'ains_task_duration_seconds',
    'Task execution time in seconds',
    ['task_type', 'status'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

tasks_in_queue = Gauge(
    'ains_tasks_in_queue',
    'Number of tasks waiting in queue',
    ['priority']
)

task_retries_total = Counter(
    'ains_task_retries_total',
    'Total task retry attempts',
    ['task_type', 'retry_count']
)

task_timeouts_total = Counter(
    'ains_task_timeouts_total',
    'Total task timeouts',
    ['task_type']
)

# ============================================================================
# AGENT METRICS
# ============================================================================

agents_total = Gauge(
    'ains_agents_total',
    'Total number of registered agents'
)

agents_active = Gauge(
    'ains_agents_active',
    'Number of currently active agents'
)

agent_trust_score = Gauge(
    'ains_agent_trust_score',
    'Agent trust score',
    ['agent_id', 'display_name']
)

agent_tasks_completed_total = Counter(
    'ains_agent_tasks_completed_total',
    'Total tasks completed by agent',
    ['agent_id']
)

agent_tasks_failed_total = Counter(
    'ains_agent_tasks_failed_total',
    'Total tasks failed by agent',
    ['agent_id']
)

# ============================================================================
# CHAIN METRICS
# ============================================================================

chains_total = Counter(
    'ains_chains_total',
    'Total number of task chains',
    ['status']
)

chain_steps_total = Counter(
    'ains_chain_steps_total',
    'Total chain steps executed',
    ['step_status']
)

chain_duration_seconds = Histogram(
    'ains_chain_duration_seconds',
    'Chain execution time in seconds',
    ['chain_status'],
    buckets=(10, 30, 60, 120, 300, 600, 1800, 3600)
)

chains_active = Gauge(
    'ains_chains_active',
    'Number of currently active chains'
)

# ============================================================================
# DATABASE METRICS
# ============================================================================

db_connections_active = Gauge(
    'ains_db_connections_active',
    'Number of active database connections'
)

db_queries_total = Counter(
    'ains_db_queries_total',
    'Total database queries',
    ['query_type', 'table']
)

db_query_duration_seconds = Histogram(
    'ains_db_query_duration_seconds',
    'Database query execution time',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# ============================================================================
# WEBHOOK METRICS
# ============================================================================

webhook_deliveries_total = Counter(
    'ains_webhook_deliveries_total',
    'Total webhook deliveries',
    ['event_type', 'status']
)

webhook_delivery_duration_seconds = Histogram(
    'ains_webhook_delivery_duration_seconds',
    'Webhook delivery time',
    ['event_type'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def record_task_created(task_type: str, client_id: str, priority: int):
    """Record task creation"""
    tasks_created_total.labels(task_type=task_type, client_id=client_id).inc()

def record_task_completed(task_type: str, agent_id: str, duration_seconds: float):
    """Record task completion"""
    tasks_completed_total.labels(task_type=task_type, agent_id=agent_id).inc()
    task_duration_seconds.labels(task_type=task_type, status='COMPLETED').observe(duration_seconds)
    agent_tasks_completed_total.labels(agent_id=agent_id).inc()

def record_task_failed(task_type: str, agent_id: str, failure_reason: str, duration_seconds: float):
    """Record task failure"""
    tasks_failed_total.labels(task_type=task_type, failure_reason=failure_reason).inc()
    task_duration_seconds.labels(task_type=task_type, status='FAILED').observe(duration_seconds)
    if agent_id:
        agent_tasks_failed_total.labels(agent_id=agent_id).inc()

def record_task_timeout(task_type: str):
    """Record task timeout"""
    task_timeouts_total.labels(task_type=task_type).inc()

def record_task_retry(task_type: str, retry_count: int):
    """Record task retry"""
    task_retries_total.labels(task_type=task_type, retry_count=str(retry_count)).inc()

def update_agent_metrics(agent_id: str, display_name: str, trust_score: float):
    """Update agent metrics"""
    agent_trust_score.labels(agent_id=agent_id, display_name=display_name).set(trust_score)

def update_queue_depth(priority: int, count: int):
    """Update task queue depth"""
    tasks_in_queue.labels(priority=str(priority)).set(count)

def record_db_query(query_type: str, table: str, duration_seconds: float):
    """Record database query"""
    db_queries_total.labels(query_type=query_type, table=table).inc()
    db_query_duration_seconds.labels(query_type=query_type).observe(duration_seconds)

def update_db_connection_pool(active: int):
    """Update database connection pool metrics"""
    db_connections_active.set(active)

def record_chain_created(status: str):
    """Record chain creation"""
    chains_total.labels(status=status).inc()

def record_chain_completed(status: str, duration_seconds: float):
    """Record chain completion"""
    chain_duration_seconds.labels(chain_status=status).observe(duration_seconds)

def record_webhook_delivery(event_type: str, status: str, duration_seconds: float):
    """Record webhook delivery"""
    webhook_deliveries_total.labels(event_type=event_type, status=status).inc()
    webhook_delivery_duration_seconds.labels(event_type=event_type).observe(duration_seconds)

def initialize_app_info(version: str, environment: str):
    """Initialize application info"""
    app_info.info({
        'version': version,
        'environment': environment,
        'name': 'DukeNet-AINS'
    })

def get_metrics() -> bytes:
    """Get Prometheus metrics in text format"""
    return generate_latest(REGISTRY)
