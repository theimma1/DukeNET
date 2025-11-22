"""Performance monitoring and optimization utilities"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from .db import Task, Agent, Capability


def get_system_stats(db: Session) -> Dict[str, Any]:
    """
    Get system-wide performance statistics.
    
    Returns:
        Dict with various performance metrics
    """
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    
    # Task statistics
    total_tasks = db.query(func.count(Task.task_id)).scalar()
    pending_tasks = db.query(func.count(Task.task_id)).filter(
        Task.status == 'PENDING'
    ).scalar()
    active_tasks = db.query(func.count(Task.task_id)).filter(
        Task.status.in_(['ASSIGNED', 'ACTIVE'])
    ).scalar()
    completed_tasks = db.query(func.count(Task.task_id)).filter(
        Task.status == 'COMPLETED'
    ).scalar()
    
    # Recent task throughput (last hour)
    tasks_last_hour = db.query(func.count(Task.task_id)).filter(
        Task.created_at >= one_hour_ago
    ).scalar()
    
    completed_last_hour = db.query(func.count(Task.task_id)).filter(
        Task.completed_at >= one_hour_ago,
        Task.status == 'COMPLETED'
    ).scalar()
    
    # Average task completion time (last 100 completed tasks)
    avg_completion_time = db.query(
        func.avg(
            func.julianday(Task.completed_at) - func.julianday(Task.created_at)
        ) * 86400  # Convert days to seconds
    ).filter(
        Task.status == 'COMPLETED',
        Task.completed_at.isnot(None)
    ).limit(100).scalar()
    
    # Agent statistics
    total_agents = db.query(func.count(Agent.agent_id)).scalar()
    active_agents = db.query(func.count(Agent.agent_id)).scalar()
 
    
    # Capability statistics
    total_capabilities = db.query(func.count(Capability.capability_id)).scalar()
    
    return {
        "tasks": {
            "total": total_tasks or 0,
            "pending": pending_tasks or 0,
            "active": active_tasks or 0,
            "completed": completed_tasks or 0,
            "throughput_last_hour": tasks_last_hour or 0,
            "completed_last_hour": completed_last_hour or 0,
            "avg_completion_time_seconds": float(avg_completion_time) if avg_completion_time else None
        },
        "agents": {
            "total": total_agents or 0,
            "active": active_agents or 0
        },
        "capabilities": {
            "total": total_capabilities or 0
        },
        "timestamp": now.isoformat()
    }


def get_slow_queries(db: Session, threshold_seconds: float = 1.0) -> list:
    """
    Identify slow queries (for monitoring).
    
    This is a placeholder - in production you'd use query logging
    and analysis tools.
    
    Args:
        db: Database session
        threshold_seconds: Threshold for slow queries
    
    Returns:
        List of slow query info
    """
    # In production, this would analyze query logs
    # For now, return empty list
    return []


def get_database_size(db: Session) -> Dict[str, Any]:
    """
    Get database size information.
    
    Returns:
        Dict with table sizes and row counts
    """
    tables = ['tasks', 'agents', 'capabilities', 'webhooks', 'webhook_deliveries', 'trust_records']
    
    stats = {}
    for table in tables:
        try:
            count = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            stats[table] = {"rows": count}
        except:
            stats[table] = {"rows": 0}
    
    return stats


def cleanup_old_data(db: Session, days: int = 30) -> Dict[str, int]:
    """
    Clean up old completed/failed tasks and deliveries.
    
    Args:
        db: Database session
        days: Delete data older than this many days
    
    Returns:
        Dict with deletion counts
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Delete old completed/failed tasks
    deleted_tasks = db.query(Task).filter(
        Task.status.in_(['COMPLETED', 'FAILED', 'CANCELLED']),
        Task.completed_at < cutoff_date
    ).delete()
    
    # Delete old successful webhook deliveries
    from .db import WebhookDelivery
    deleted_deliveries = db.query(WebhookDelivery).filter(
        WebhookDelivery.status == 'success',
        WebhookDelivery.delivered_at < cutoff_date
    ).delete()
    
    db.commit()
    
    return {
        "deleted_tasks": deleted_tasks,
        "deleted_deliveries": deleted_deliveries
    }
