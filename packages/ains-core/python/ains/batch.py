"""Batch task operations"""
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import uuid

from .db import Task


def submit_batch_tasks(
    db: Session,
    client_id: str,
    tasks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Submit multiple tasks in a single batch.
    
    Args:
        db: Database session
        client_id: Client submitting the batch
        tasks: List of task specifications
    
    Returns:
        Dict with batch_id, task_ids, and status counts
    """
    batch_id = f"batch_{uuid.uuid4().hex[:16]}"
    task_ids = []
    created_count = 0
    failed_count = 0
    errors = []
    
    for idx, task_spec in enumerate(tasks):
        try:
            task_id = f"task_{uuid.uuid4().hex[:16]}"
            
            new_task = Task(
                task_id=task_id,
                client_id=client_id,
                task_type=task_spec.get('task_type', 'default'),
                capability_required=task_spec['capability_required'],
                input_data=task_spec['input_data'],
                priority=task_spec.get('priority', 5),
                status="PENDING",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                max_retries=task_spec.get('max_retries', 3),
                retry_count=0,
                retry_policy=task_spec.get('retry_policy', 'exponential'),
                timeout_seconds=task_spec.get('timeout_seconds', 300)
            )
            
            db.add(new_task)
            task_ids.append(task_id)
            created_count += 1
            
        except Exception as e:
            failed_count += 1
            errors.append({
                'index': idx,
                'error': str(e)
            })
    
    # Commit all tasks at once
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            'batch_id': batch_id,
            'success': False,
            'error': f"Failed to commit batch: {str(e)}",
            'created': 0,
            'failed': len(tasks)
        }
    
    return {
        'batch_id': batch_id,
        'success': True,
        'created': created_count,
        'failed': failed_count,
        'task_ids': task_ids,
        'errors': errors if errors else None
    }


def get_batch_status(db: Session, task_ids: List[str]) -> Dict[str, Any]:
    """
    Get status of multiple tasks.
    
    Args:
        db: Database session
        task_ids: List of task IDs to check
    
    Returns:
        Dict with status counts and task details
    """
    tasks = db.query(Task).filter(Task.task_id.in_(task_ids)).all()
    
    status_counts = {}
    task_details = []
    
    for task in tasks:
        # Count by status
        status_counts[task.status] = status_counts.get(task.status, 0) + 1
        
        # Add task details
        task_details.append({
            'task_id': task.task_id,
            'status': task.status,
            'priority': task.priority,
            'created_at': task.created_at.isoformat() if task.created_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None
        })
    
    return {
        'total': len(tasks),
        'status_counts': status_counts,
        'tasks': task_details
    }


def cancel_batch_tasks(
    db: Session,
    task_ids: List[str],
    client_id: str,
    reason: str = "Batch cancellation"
) -> Dict[str, Any]:
    """
    Cancel multiple tasks in a batch.
    
    Args:
        db: Database session
        task_ids: List of task IDs to cancel
        client_id: Client requesting cancellation
        reason: Reason for cancellation
    
    Returns:
        Dict with cancellation results
    """
    from .timeouts import cancel_task
    
    cancelled_count = 0
    failed_count = 0
    errors = []
    
    for task_id in task_ids:
        try:
            success = cancel_task(db, task_id, client_id, reason)
            if success:
                cancelled_count += 1
            else:
                failed_count += 1
                errors.append({
                    'task_id': task_id,
                    'error': 'Cannot cancel task'
                })
        except Exception as e:
            failed_count += 1
            errors.append({
                'task_id': task_id,
                'error': str(e)
            })
    
    return {
        'cancelled': cancelled_count,
        'failed': failed_count,
        'errors': errors if errors else None
    }
