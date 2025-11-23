"""Trust and reputation system for agents"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import uuid
import math
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from .db import Agent, Task, TrustRecord


def calculate_trust_score(
    db: Session,
    agent_id: str
) -> float:
    """
    Calculate comprehensive trust score for an agent.
    
    Formula:
    trust_score = base_trust + success_bonus + speed_bonus + volume_bonus 
                  - failure_penalty - inactivity_penalty
    
    Args:
        db: Database session
        agent_id: Agent ID
    
    Returns:
        Trust score (0.0 - 1.0)
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        return 0.5  # Default for non-existent agents
    
    # Base trust
    base_trust = 0.5
    
    # Success rate component (max +0.3)
    total_tasks = agent.total_tasks_completed + agent.total_tasks_failed
    if total_tasks > 0:
        success_rate = agent.total_tasks_completed / total_tasks
        success_bonus = success_rate * 0.3
    else:
        success_bonus = 0.0
    
    # Volume component (max +0.1)
    if agent.total_tasks_completed > 0:
        volume_bonus = min(0.1, math.log10(agent.total_tasks_completed + 1) * 0.05)
    else:
        volume_bonus = 0.0
    
    # Speed component (max +0.1)
    # Assume average expected time is 300 seconds
    if agent.avg_completion_time_seconds and agent.avg_completion_time_seconds > 0:
        expected_time = 300
        speed_ratio = expected_time / agent.avg_completion_time_seconds
        speed_bonus = min(0.1, max(0, speed_ratio - 0.5) * 0.2)
    else:
        speed_bonus = 0.0
    
    # Failure penalty (max -0.5)
    if total_tasks > 0:
        failure_rate = agent.total_tasks_failed / total_tasks
        failure_penalty = failure_rate * 0.5
    else:
        failure_penalty = 0.0
    
    # Inactivity penalty (-0.01 per day after 30 days)
    if agent.last_task_completed_at:
        days_since_last = (datetime.now(timezone.utc) - agent.last_task_completed_at).days
        if days_since_last > 30:
            inactivity_penalty = (days_since_last - 30) * 0.01
        else:
            inactivity_penalty = 0.0
    else:
        inactivity_penalty = 0.1  # New agents with no history
    
    # Calculate final score
    calculated_score = (
        base_trust + 
        success_bonus + 
        speed_bonus + 
        volume_bonus - 
        failure_penalty - 
        inactivity_penalty
    )
    
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, calculated_score))


def adjust_trust_score(
    db: Session,
    agent_id: str,
    event_type: str,
    trust_delta: float = 0.0,
    task_id: Optional[str] = None,
    reason: Optional[str] = None
) -> TrustRecord:
    """
    Adjust an agent's trust score and create an audit record.
    
    Args:
        db: Database session
        agent_id: Agent identifier
        event_type: Type of event causing trust change
        trust_delta: Change in trust score (can be positive or negative)
        task_id: Optional associated task ID
        reason: Optional reason for the adjustment
    
    Returns:
        TrustRecord: The created trust record
    """
    # Get agent
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    
    # Calculate new trust score
    trust_before = agent.trust_score
    trust_after = max(0.0, min(1.0, trust_before + trust_delta))  # Clamp between 0 and 1
    
    # Update agent's trust score
    agent.trust_score = trust_after
    
    # Create audit record
    record = TrustRecord(
        record_id=f"trust_{uuid.uuid4().hex[:16]}",
        agent_id=agent_id,
        event_type=event_type,
        task_id=task_id,
        trust_delta=trust_delta,
        trust_score_before=trust_before,
        trust_score_after=trust_after,
        reason=reason or f"Trust adjusted due to {event_type}",
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return record



def update_agent_metrics_on_task_completion(
    db: Session,
    agent_id: str,
    task: Task,
    success: bool
) -> None:
    """
    Update agent metrics after task completion.
    
    Args:
        db: Database session
        agent_id: Agent ID
        task: Completed task
        success: Whether task completed successfully
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        return
    
    # Update counters
    if success:
        agent.total_tasks_completed += 1
        
        # Calculate trust adjustment
        trust_delta = 0.02  # Base success bonus
        
        # Bonus for early completion
        if task.started_at and task.completed_at:
            completion_time = (task.completed_at - task.started_at).total_seconds()
            if task.timeout_seconds and completion_time < (task.timeout_seconds * 0.5):
                trust_delta += 0.03  # Early delivery bonus
        
        adjust_trust_score(
            db, agent_id, "task_completed", trust_delta,
            task_id=task.task_id,
            reason="Task completed successfully"
        )
    else:
        agent.total_tasks_failed += 1
        
        # Penalty for failure
        trust_delta = -0.05
        
        adjust_trust_score(
            db, agent_id, "task_failed", trust_delta,
            task_id=task.task_id,
            reason=f"Task failed: {task.error_message or 'Unknown error'}"
        )
    
    # Update average completion time
    if success and task.started_at and task.completed_at:
        completion_time = (task.completed_at - task.started_at).total_seconds()
        
        if agent.avg_completion_time_seconds:
            # Weighted average (70% old, 30% new)
            agent.avg_completion_time_seconds = (
                agent.avg_completion_time_seconds * 0.7 + 
                completion_time * 0.3
            )
        else:
            agent.avg_completion_time_seconds = completion_time
    
    # Update last completed timestamp
    if success:
        agent.last_task_completed_at = datetime.now(timezone.utc)
    
    db.commit()


def get_trust_level(trust_score: float) -> str:
    """Get trust level label from score"""
    if trust_score >= 0.9:
        return "excellent"
    elif trust_score >= 0.7:
        return "high"
    elif trust_score >= 0.5:
        return "medium"
    elif trust_score >= 0.3:
        return "low"
    else:
        return "very_low"


def get_agent_trust_metrics(db: Session, agent_id: str) -> Dict[str, Any]:
    """
    Get comprehensive trust metrics for an agent.
    
    Returns:
        Dict with trust score, level, and performance metrics
    """
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    
    # Calculate success rate
    total_tasks = agent.total_tasks_completed + agent.total_tasks_failed
    success_rate = agent.total_tasks_completed / total_tasks if total_tasks > 0 else 0.0
    
    # Tasks in last 30 days
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_tasks = db.query(func.count(Task.task_id)).filter(
        Task.assigned_agent_id == agent_id,
        Task.completed_at >= thirty_days_ago,
        Task.status == 'COMPLETED'
    ).scalar() or 0
    
    return {
        "agent_id": agent_id,
        "trust_score": round(agent.trust_score, 3),
        "trust_level": get_trust_level(agent.trust_score),
        "metrics": {
            "total_tasks_completed": agent.total_tasks_completed,
            "total_tasks_failed": agent.total_tasks_failed,
            "success_rate": round(success_rate, 3),
            "avg_completion_time_seconds": round(agent.avg_completion_time_seconds, 2) if agent.avg_completion_time_seconds else None,
            "tasks_last_30_days": recent_tasks,
            "last_task_completed_at": agent.last_task_completed_at.isoformat() if agent.last_task_completed_at else None
        }
    }


def get_trust_history(
    db: Session,
    agent_id: str,
    limit: int = 50
) -> list[TrustRecord]:
    """Get trust score history for an agent"""
    return db.query(TrustRecord).filter(
        TrustRecord.agent_id == agent_id
    ).order_by(
        TrustRecord.created_at.desc()
    ).limit(limit).all()


def get_leaderboard(db: Session, limit: int = 10, min_tasks: int = 0) -> dict:
    """
    Get top agents by trust score.
    
    Args:
        db: Database session
        limit: Maximum number of agents to return
        min_tasks: Minimum number of completed tasks required
    
    Returns:
        dict: Leaderboard with agents list
    """
    query = db.query(Agent).filter(
        Agent.total_tasks_completed >= min_tasks
    ).order_by(
        Agent.trust_score.desc()
    ).limit(limit)
    
    agents = query.all()
    
    leaderboard = []
    for agent in agents:
        total_tasks = agent.total_tasks_completed + agent.total_tasks_failed
        success_rate = agent.total_tasks_completed / total_tasks if total_tasks > 0 else 0.0
        
        leaderboard.append({
            "agent_id": agent.agent_id,
            "display_name": agent.display_name,
            "trust_score": agent.trust_score,
            "total_tasks_completed": agent.total_tasks_completed,
            "total_tasks_failed": agent.total_tasks_failed,
            "success_rate": success_rate
        })
    
    return {"leaderboard": leaderboard}


def get_trust_metrics(db: Session, agent_id: str) -> dict:
    """Get comprehensive trust metrics for an agent"""
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    
    total_tasks = agent.total_tasks_completed + agent.total_tasks_failed
    success_rate = agent.total_tasks_completed / total_tasks if total_tasks > 0 else 0.0
    
    # Calculate trust level based on trust score
    trust_score = agent.trust_score
    if trust_score >= 0.8:
        trust_level = "high"
    elif trust_score >= 0.5:
        trust_level = "medium"
    else:
        trust_level = "low"
    
    return {
        "agent_id": agent.agent_id,
        "trust_score": agent.trust_score,
        "trust_level": trust_level,  # Add this field
        "total_tasks_completed": agent.total_tasks_completed,
        "total_tasks_failed": agent.total_tasks_failed,
        "success_rate": success_rate,
        "avg_completion_time_seconds": agent.avg_completion_time_seconds,
        "last_task_completed_at": agent.last_task_completed_at.isoformat() if agent.last_task_completed_at else None
    }
