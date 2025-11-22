"""Task retry logic and scheduling"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session

from .db import Task


def calculate_next_retry(retry_count: int, policy: str = "exponential") -> datetime:
    """Calculate next retry time based on policy
    
    Args:
        retry_count: Current retry attempt number (0-indexed)
        policy: Retry policy - "exponential", "linear", or "fixed"
    
    Returns:
        datetime: When to retry next
    """
    if policy == "exponential":
        # 1s, 2s, 4s, 8s, 16s, 32s (capped at 60s)
        delay_seconds = min(2 ** retry_count, 60)
    elif policy == "linear":
        # 5s, 10s, 15s, 20s, 25s
        delay_seconds = (retry_count + 1) * 5
    elif policy == "fixed":
        # Always 10 seconds
        delay_seconds = 10
    else:
        # Default to exponential
        delay_seconds = min(2 ** retry_count, 60)
    
    return datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)


def should_retry(task: Task, error_message: str) -> bool:
    """Determine if task should be retried based on error type
    
    Args:
        task: Task that failed
        error_message: Error message from failure
    
    Returns:
        bool: True if task should be retried
    """
    # Check if max retries exceeded
    if task.retry_count >= task.max_retries:
        return False
    
    # Define non-retryable error patterns
    non_retryable_errors = [
        "invalid input",
        "authentication failed",
        "permission denied",
        "not found",
        "bad request",
        "validation error"
    ]
    
    # Check if error is non-retryable
    error_lower = error_message.lower()
    for non_retryable in non_retryable_errors:
        if non_retryable in error_lower:
            return False
    
    # Retryable errors (timeouts, network issues, temporary failures)
    return True


def schedule_retry(db: Session, task_id: str) -> bool:
    """Schedule task for retry
    
    Args:
        db: Database session
        task_id: ID of task to retry
    
    Returns:
        bool: True if retry scheduled, False if max retries reached
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        return False
    
    # Check if should retry
    if not should_retry(task, task.error_message or ""):
        # Move to failed state permanently
        task.status = "FAILED"
        db.commit()
        return False
    
    # Increment retry count
    task.retry_count += 1
    
    # Calculate next retry time
    task.next_retry_at = calculate_next_retry(task.retry_count, task.retry_policy)
    
    # Reset to PENDING for retry
    task.status = "PENDING"
    task.assigned_agent_id = None
    task.assigned_at = None
    task.started_at = None
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    return True


def get_tasks_ready_for_retry(db: Session, limit: int = 10) -> list[Task]:
    """Get tasks that are ready to be retried
    
    Args:
        db: Database session
        limit: Maximum number of tasks to return
    
    Returns:
        list: Tasks ready for retry
    """
    now = datetime.now(timezone.utc)
    
    tasks = db.query(Task).filter(
        Task.status == "PENDING",
        Task.retry_count > 0,
        Task.next_retry_at <= now
    ).limit(limit).all()
    
    return tasks


def process_retry_queue(db: Session) -> int:
    """Process tasks in retry queue
    
    This should be called by a background worker periodically
    
    Args:
        db: Database session
    
    Returns:
        int: Number of tasks processed
    """
    from .routing import route_pending_tasks
    
    # Get tasks ready for retry
    retry_tasks = get_tasks_ready_for_retry(db, limit=50)
    
    if not retry_tasks:
        return 0
    
    # Route them like normal pending tasks
    routed = route_pending_tasks(db, limit=len(retry_tasks))
    
    return routed
