"""Task routing logic for AINS"""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .db import Task, Agent, Capability, TrustRecord


def find_best_agent_for_task(
    db: Session,
    capability_required: str,
    min_trust_score: float = 0.5
) -> Optional[str]:
    """
    Find the best agent to handle a task based on capability and trust score.
    
    Args:
        db: Database session
        capability_required: Capability name required for the task
        min_trust_score: Minimum trust score threshold (default 0.5)
    
    Returns:
        agent_id of the best agent, or None if no suitable agent found
    """
    # Query agents that have the required capability and are ACTIVE
    agents_with_capability = (
        db.query(Agent.agent_id, TrustRecord.trust_score)
        .join(Capability, Capability.agent_id == Agent.agent_id)
        .outerjoin(TrustRecord, TrustRecord.agent_id == Agent.agent_id)
        .filter(
            and_(
                Capability.name == capability_required,
                Agent.status == "ACTIVE"
            )
        )
        .all()
    )
    
    if not agents_with_capability:
        return None
    
    # Filter by minimum trust score and sort by trust score descending
    eligible_agents = [
        (agent_id, trust_score or 0.0)  # Default to 0.0 if no trust record
        for agent_id, trust_score in agents_with_capability
        if (trust_score or 0.0) >= min_trust_score
    ]
    
    if not eligible_agents:
        return None
    
    # Sort by trust score (highest first)
    eligible_agents.sort(key=lambda x: x[1], reverse=True)
    
    # Return the agent with highest trust score
    return eligible_agents[0][0]


def assign_task_to_agent(
    db: Session,
    task_id: str,
    agent_id: str
) -> bool:
    """
    Assign a task to a specific agent.
    
    Args:
        db: Database session
        task_id: ID of the task to assign
        agent_id: ID of the agent to assign to
    
    Returns:
        True if assignment successful, False otherwise
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        return False
    
    # Get trust score snapshot
    trust_record = db.query(TrustRecord).filter(TrustRecord.agent_id == agent_id).first()
    trust_score = trust_record.trust_score if trust_record else 0.0
    
    # Update task
    task.assigned_agent_id = agent_id
    task.status = "ASSIGNED"
    task.assigned_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    return True


def route_pending_tasks(db: Session, limit: int = 10) -> int:
    """
    Route pending tasks to available agents.
    
    Args:
        db: Database session
        limit: Maximum number of tasks to route in one batch
    
    Returns:
        Number of tasks successfully routed
    """
    # Get pending tasks that haven't expired
    pending_tasks = (
        db.query(Task)
        .filter(
            and_(
                Task.status == "PENDING",
                (Task.expires_at.is_(None) | (Task.expires_at > datetime.now(timezone.utc)))
            )
        )
        .order_by(Task.priority.desc(), Task.created_at.asc())
        .limit(limit)
        .all()
    )
    
    routed_count = 0
    
    for task in pending_tasks:
        # Find best agent for this task
        best_agent = find_best_agent_for_task(
            db,
            capability_required=task.capability_required,
            min_trust_score=0.5
        )
        
        if best_agent:
            # Assign task to agent
            success = assign_task_to_agent(db, task.task_id, best_agent)
            if success:
                routed_count += 1
        else:
            # No suitable agent found - could mark as FAILED or leave PENDING
            # For now, leave as PENDING for retry
            pass
    
    return routed_count
