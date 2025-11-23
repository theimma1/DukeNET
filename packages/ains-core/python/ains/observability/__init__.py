"""Observability module for monitoring and metrics"""
from .metrics import (
    # Metrics objects
    http_requests_total,
    http_request_duration_seconds,
    tasks_created_total,
    tasks_completed_total,
    tasks_failed_total,
    task_duration_seconds,
    agents_total,
    agents_active,
    
    # Helper functions
    record_task_created,
    record_task_completed,
    record_task_failed,
    update_agent_metrics,
    update_queue_depth,
    initialize_app_info,
    get_metrics,
)

from .middleware import PrometheusMiddleware

__all__ = [
    # Metrics
    'http_requests_total',
    'http_request_duration_seconds',
    'tasks_created_total',
    'tasks_completed_total',
    'tasks_failed_total',
    'task_duration_seconds',
    'agents_total',
    'agents_active',
    
    # Functions
    'record_task_created',
    'record_task_completed',
    'record_task_failed',
    'update_agent_metrics',
    'update_queue_depth',
    'initialize_app_info',
    'get_metrics',
    
    # Middleware
    'PrometheusMiddleware',
]