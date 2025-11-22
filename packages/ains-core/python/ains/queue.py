"""Priority queue management and task routing"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from .db import Task, Agent


class PriorityQueue:
    """Manages task prioritization and fair queuing"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_next_task_for_agent(self, agent_id: str, capability: str) -> Optional[Task]:
        """
        Get next task for agent considering priority and fairness.
        
        Uses weighted fair queuing:
        - High priority tasks (8-10) processed first
        - Medium priority tasks (5-7) prevent starvation
        - Low priority tasks (1-4) guaranteed processing
        
        Args:
            agent_id: Agent requesting task
            capability: Capability the agent can handle
        
        Returns:
            Next task to process, or None if queue empty
        """
        # Get agent's current workload
        active_tasks = self.db.query(Task).filter(
            Task.assigned_agent_id == agent_id,
            Task.status.in_(['ASSIGNED', 'ACTIVE'])
        ).count()
        
        # Don't overload agents (max 5 concurrent tasks)
        if active_tasks >= 5:
            return None
        
        # Priority-based selection with fairness
        # 70% chance to pick high priority, 30% for medium/low to prevent starvation
        import random
        use_strict_priority = random.random() < 0.7
        
        if use_strict_priority:
            # Strict priority ordering
            task = self.db.query(Task).filter(
                Task.status == 'PENDING',
                func.lower(Task.capability_required) == capability.lower()
            ).order_by(
                Task.priority.desc(),
                Task.created_at.asc()
            ).first()
        else:
            # Fair queuing - oldest task from medium/low priority
            task = self.db.query(Task).filter(
                Task.status == 'PENDING',
                func.lower(Task.capability_required) == capability.lower(),
                Task.priority <= 7  # Medium and low priority
            ).order_by(
                Task.created_at.asc()
            ).first()
        
        return task
    
    def get_queue_stats(self) -> dict:
        """
        Get queue statistics by priority level.
        
        Returns:
            Dictionary with queue depth per priority and totals
        """
        # Count tasks by priority
        priority_counts = self.db.query(
            Task.priority,
            func.count(Task.task_id).label('count')
        ).filter(
            Task.status == 'PENDING'
        ).group_by(Task.priority).all()
        
        # Convert to dict
        stats = {
            'by_priority': {p: c for p, c in priority_counts},
            'total_pending': sum(c for _, c in priority_counts),
            'high_priority': sum(c for p, c in priority_counts if p >= 8),
            'medium_priority': sum(c for p, c in priority_counts if 5 <= p < 8),
            'low_priority': sum(c for p, c in priority_counts if p < 5)
        }
        
        return stats
    
    def balance_workload(self) -> dict:
        """
        Get workload distribution across agents.
        
        Returns:
            Dictionary with agent workloads
        """
        workloads = self.db.query(
            Task.assigned_agent_id,
            func.count(Task.task_id).label('active_tasks')
        ).filter(
            Task.status.in_(['ASSIGNED', 'ACTIVE']),
            Task.assigned_agent_id.isnot(None)
        ).group_by(Task.assigned_agent_id).all()
        
        return {
            'agents': [
                {'agent_id': agent_id, 'active_tasks': count}
                for agent_id, count in workloads
            ],
            'total_active': sum(count for _, count in workloads)
        }


def adjust_priority_by_age(db: Session, max_age_hours: int = 24):
    """
    Increase priority of old tasks to prevent starvation.
    
    Tasks older than max_age_hours get priority boost.
    
    Args:
        db: Database session
        max_age_hours: Age threshold for priority boost
    
    Returns:
        Number of tasks updated
    """
    from datetime import timedelta
    
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    
    # Find old low-priority tasks
    old_tasks = db.query(Task).filter(
        Task.status == 'PENDING',
        Task.created_at < cutoff_time,
        Task.priority < 7  # Only boost low/medium priority
    ).all()
    
    updated = 0
    for task in old_tasks:
        # Boost priority by 2, max 9
        task.priority = min(9, task.priority + 2)
        updated += 1
    
    if updated > 0:
        db.commit()
    
    return updated
