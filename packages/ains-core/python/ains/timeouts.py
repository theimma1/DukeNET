"""Task timeout monitoring and cancellation"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .db import Task


def check_timeouts(db: Session, limit: int = 50) -> int:
    """
    Check for timed-out tasks and mark them as failed.
    
    This should be called by a background worker periodically.
    
    Args:
        db: Database session
        limit: Maximum number of tasks to check per run
    
    Returns:
        int: Number of tasks timed out
    """
    now = datetime.now(timezone.utc)
    
    # Find active tasks with timeouts that have expired
    timed_out_tasks = db.query(Task).filter(
        Task.status.in_(['ASSIGNED', 'ACTIVE']),
        Task.timeout_seconds.isnot(None),
        Task.started_at.isnot(None)
    ).limit(limit).all()
    
    timed_out_count = 0
    
    for task in timed_out_tasks:
        # Calculate when task should timeout
        timeout_at = task.started_at + timedelta(seconds=task.timeout_seconds)
        
        timeout_at = task.started_at.replace(tzinfo=timezone.utc) + timedelta(seconds=task.timeout_seconds) if task.started_at.tzinfo is None else task.started_at + timedelta(seconds=task.timeout_seconds)
            # Task has timed out
        task.status = 'FAILED'
        task.completed_at = now
        task.updated_at = now
        task.error_message = f"Task timed out after {task.timeout_seconds} seconds"
        timed_out_count += 1
    
    if timed_out_count > 0:
        db.commit()
    
    return timed_out_count


def cancel_task(db: Session, task_id: str, cancelled_by: str, reason: str = "Cancelled by client") -> bool:
    """
    Cancel a task.
    
    Args:
        db: Database session
        task_id: ID of task to cancel
        cancelled_by: Agent/client ID requesting cancellation
        reason: Reason for cancellation
    
    Returns:
        bool: True if cancelled successfully, False otherwise
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        return False
    
    # Can only cancel tasks that are not already terminal
    if task.status in ['COMPLETED', 'FAILED', 'CANCELLED']:
        return False
    
    # Update task status
    task.status = 'CANCELLED'
    task.cancelled_at = datetime.now(timezone.utc)
    task.cancelled_by = cancelled_by
    task.cancellation_reason = reason
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    return True


def set_task_timeout(db: Session, task_id: str, timeout_seconds: int) -> bool:
    """
    Set or update timeout for a task.
    
    Args:
        db: Database session
        task_id: ID of task
        timeout_seconds: Timeout duration in seconds
    
    Returns:
        bool: True if updated successfully
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        return False
    
    # Can only set timeout on non-terminal tasks
    if task.status in ['COMPLETED', 'FAILED', 'CANCELLED']:
        return False
    
    task.timeout_seconds = timeout_seconds
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    return True


def get_timeout_candidates(db: Session, limit: int = 100) -> list[Task]:
    """
    Get tasks that are at risk of timing out soon.
    
    Useful for monitoring and alerting.
    
    Args:
        db: Database session
        limit: Maximum number to return
    
    Returns:
        list: Tasks approaching timeout
    """
    now = datetime.now(timezone.utc)
    
    # Find active tasks with timeouts
    tasks = db.query(Task).filter(
        Task.status.in_(['ASSIGNED', 'ACTIVE']),
        Task.timeout_seconds.isnot(None),
        Task.started_at.isnot(None)
    ).limit(limit).all()
    
    # Filter to those within 10% of timeout
    at_risk = []
    for task in tasks:
        timeout_at = task.started_at + timedelta(seconds=task.timeout_seconds)
        time_remaining = (timeout_at - now).total_seconds()
        time_limit = task.timeout_seconds
        
        # At risk if <10% of time remaining
        if 0 < time_remaining < (time_limit * 0.1):
            at_risk.append(task)
    
    return at_risk
