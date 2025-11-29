"""Advanced features: dependencies, chaining, routing, scheduling"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import secrets
import random
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .db import Task, Agent, TaskChain, ScheduledTask


# ============================================================================
# TASK DEPENDENCIES
# ============================================================================

def check_dependencies(db: Session, task_id: str) -> bool:
    """
    Check if all dependencies for a task are satisfied.
    
    Returns:
        True if all dependencies are completed, False otherwise
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task or not task.depends_on:
        return True
    
    for dep_id in task.depends_on:
        dep_task = db.query(Task).filter(Task.task_id == dep_id).first()
        if not dep_task or dep_task.status != "COMPLETED":
            return False
    
    return True


def get_dependency_status(db: Session, task_id: str) -> Dict[str, Any]:
    """Get detailed status of task dependencies"""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        return {}
    
    dependencies_status = {}
    for dep_id in (task.depends_on or []):
        dep_task = db.query(Task).filter(Task.task_id == dep_id).first()
        dependencies_status[dep_id] = dep_task.status if dep_task else "NOT_FOUND"
    
    all_completed = all(
        status == "COMPLETED" 
        for status in dependencies_status.values()
    )
    
    return {
        "task_id": task_id,
        "depends_on": task.depends_on or [],
        "dependencies_status": dependencies_status,
        "is_blocked": task.is_blocked,
        "ready_to_run": all_completed and not task.is_blocked
    }


def unblock_dependent_tasks(db: Session, completed_task_id: str):
    """
    Unblock tasks that were waiting on the completed task.
    Called when a task completes successfully.
    """
    # Find all blocked tasks
    blocked_tasks = db.query(Task).filter(
        Task.is_blocked == True,
        Task.status == "PENDING"
    ).all()
    
    for task in blocked_tasks:
        if completed_task_id in (task.depends_on or []):
            # Check if all dependencies are now satisfied
            if check_dependencies(db, task.task_id):
                task.is_blocked = False
                # Task is now ready to be routed
                # The routing will happen in the next routing cycle
    
    db.commit()


def fail_dependent_tasks(db: Session, failed_task_id: str):
    """
    Mark dependent tasks as failed when a dependency fails.
    Called when a task fails.
    """
    # Find all tasks depending on this one
    all_tasks = db.query(Task).filter(
        Task.status == "PENDING"
    ).all()
    
    for task in all_tasks:
        if failed_task_id in (task.depends_on or []):
            task.status = "FAILED"
            task.error_message = f"Dependency task {failed_task_id} failed"
            task.completed_at = datetime.now(timezone.utc)
    
    db.commit()


# ============================================================================
# TASK CHAINING
# ============================================================================

def create_task_chain(
    db: Session,
    name: str,
    client_id: str,
    steps: List[Dict[str, Any]]
) -> TaskChain:
    """Create a new task chain"""
    chain_id = f"chain_{secrets.token_hex(8)}"
    
    chain = TaskChain(
        chain_id=chain_id,
        name=name,
        client_id=client_id,
        steps=steps,
        current_step=0,
        status="PENDING",
        step_results={}
    )
    
    db.add(chain)
    db.commit()
    db.refresh(chain)
    
    # Start the first step
    execute_next_chain_step(db, chain_id)
    
    return chain


def execute_next_chain_step(db: Session, chain_id: str):
    """Execute the next step in a task chain"""
    chain = db.query(TaskChain).filter(TaskChain.chain_id == chain_id).first()
    
    if not chain or chain.status != "PENDING":
        return
    
    if chain.current_step >= len(chain.steps):
        # Chain completed
        chain.status = "COMPLETED"
        chain.completed_at = datetime.now(timezone.utc)
        db.commit()
        return
    
    # Get current step definition
    step = chain.steps[chain.current_step]
    
    # Prepare input data
    input_data = step.get("input_data", {})
    
    # If step uses previous output, merge it
    if step.get("use_previous_output") and chain.current_step > 0:
        prev_step = chain.current_step - 1
        prev_result = chain.step_results.get(str(prev_step), {}).get("data")
        if prev_result:
            input_data = {**input_data, "previous_output": prev_result}
    
    # Create task for this step
    task = Task(
        task_id=f"task_{secrets.token_hex(8)}",
        client_id=chain.client_id,
        task_type=step["task_type"],
        capability_required=step["capability_required"],
        input_data=input_data,
        priority=step.get("priority", 5),
        status="PENDING",
        chain_id=chain_id
    )
    
    db.add(task)
    
    # Update chain status
    if chain.current_step == 0:
        chain.status = "RUNNING"
        chain.started_at = datetime.now(timezone.utc)
    
    db.commit()


def on_chain_task_complete(db: Session, task: Task):
    """Called when a task that's part of a chain completes"""
    if not task.chain_id:
        return
    
    chain = db.query(TaskChain).filter(TaskChain.chain_id == task.chain_id).first()
    
    if not chain:
        return
    
    # Store step result
    step_results = chain.step_results or {}
    step_results[str(chain.current_step)] = {
        "status": task.status,
        "data": task.result_data,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }
    chain.step_results = step_results
    
    if task.status == "COMPLETED":
        # Move to next step
        chain.current_step += 1
        db.commit()
        
        # Execute next step
        execute_next_chain_step(db, chain.chain_id)
    
    elif task.status == "FAILED":
        # Chain failed
        chain.status = "FAILED"
        chain.error_message = f"Step {chain.current_step} failed: {task.error_message}"
        chain.completed_at = datetime.now(timezone.utc)
        db.commit()


# ============================================================================
# ROUTING STRATEGIES
# ============================================================================

def route_round_robin(db: Session, task: Task) -> Optional[str]:
    """Round-robin routing: distribute tasks evenly"""
    # Find capable agents
    agents = db.query(Agent).all()
    
    # Filter agents with matching capability
    capable_agents = [
        agent for agent in agents
        if task.capability_required in (agent.tags or [])
    ]
    
    if not capable_agents:
        return None
    
    # Sort by last_assigned_at (nulls first)
    # Use a sentinel value that's timezone-aware
    min_datetime = datetime.min.replace(tzinfo=timezone.utc)
    
    def get_sort_key(agent):
        if agent.last_assigned_at is None:
            return min_datetime
        # Ensure timezone-aware
        if agent.last_assigned_at.tzinfo is None:
            return agent.last_assigned_at.replace(tzinfo=timezone.utc)
        return agent.last_assigned_at
    
    capable_agents.sort(key=get_sort_key)
    
    # Select first agent (least recently assigned)
    selected = capable_agents[0]
    selected.last_assigned_at = datetime.now(timezone.utc)
    db.commit()
    
    return selected.agent_id



def route_least_loaded(db: Session, task: Task) -> Optional[str]:
    """Route to agent with fewest active tasks"""
    # Find capable agents
    agents = db.query(Agent).filter(
        Agent.tags.contains([task.capability_required])
    ).all()
    
    if not agents:
        return None
    
    # Calculate load for each agent
    agent_loads = []
    for agent in agents:
        active_count = db.query(Task).filter(
            Task.assigned_agent_id == agent.agent_id,
            Task.status.in_(["ASSIGNED", "RUNNING"])
        ).count()
        agent_loads.append((agent, active_count))
    
    # Sort by load (ascending) and select least loaded
    agent_loads.sort(key=lambda x: x[1])
    
    selected = agent_loads[0][0]
    selected.last_assigned_at = datetime.now(timezone.utc)
    db.commit()
    
    return selected.agent_id


def route_trust_weighted(db: Session, task: Task) -> Optional[str]:
    """Route based on trust score, favoring highly trusted agents"""
    # Find all agents
    agents = db.query(Agent).all()
    
    # Filter capable agents with minimum trust
    capable_agents = [
        agent for agent in agents
        if task.capability_required in (agent.tags or [])
        and agent.trust_score >= 0.3
    ]
    
    if not capable_agents:
        # Fallback: any capable agent
        capable_agents = [
            agent for agent in agents
            if task.capability_required in (agent.tags or [])
        ]
        
        if not capable_agents:
            return None
    
    # Weight selection by trust score
    weights = [max(agent.trust_score, 0.1) for agent in capable_agents]
    selected = random.choices(capable_agents, weights=weights, k=1)[0]
    
    selected.last_assigned_at = datetime.now(timezone.utc)
    db.commit()
    
    return selected.agent_id

def route_fastest_response(db: Session, task: Task) -> Optional[str]:
    """Route to agent with fastest average completion time"""
    # Find agents with completion time data
    agents = db.query(Agent).filter(
        Agent.tags.contains([task.capability_required]),
        Agent.avg_completion_time_seconds.isnot(None),
        Agent.total_tasks_completed > 0
    ).order_by(Agent.avg_completion_time_seconds.asc()).all()
    
    if not agents:
        # Fallback: any capable agent
        agents = db.query(Agent).filter(
            Agent.tags.contains([task.capability_required])
        ).all()
        
        if not agents:
            return None
    
    selected = agents[0]
    selected.last_assigned_at = datetime.now(timezone.utc)
    db.commit()
    
    return selected.agent_id


def route_task(db: Session, task: Task) -> Optional[str]:
    """
    Route a task to an agent based on the specified routing strategy.
    
    Returns:
        agent_id if routed successfully, None otherwise
    """
    strategy = task.routing_strategy or "round_robin"
    
    routing_functions = {
        "round_robin": route_round_robin,
        "least_loaded": route_least_loaded,
        "trust_weighted": route_trust_weighted,
        "fastest_response": route_fastest_response
    }
    
    route_func = routing_functions.get(strategy, route_round_robin)
    
    return route_func(db, task)


# ============================================================================
# SCHEDULED TASKS
# ============================================================================

def calculate_next_run(cron_expr: str, base_time: Optional[datetime] = None) -> datetime:
    """Calculate next run time from cron expression"""
    try:
        from croniter import croniter
        
        if base_time is None:
            base_time = datetime.now(timezone.utc)
        
        cron = croniter(cron_expr, base_time)
        next_time = cron.get_next(datetime)
        
        # Ensure timezone aware
        if next_time.tzinfo is None:
            next_time = next_time.replace(tzinfo=timezone.utc)
        
        return next_time
    
    except Exception as e:
        # Fallback: 1 hour from now
        return (base_time or datetime.now(timezone.utc)) + timedelta(hours=1)


def create_scheduled_task(
    db: Session,
    name: str,
    client_id: str,
    cron_expression: str,
    task_type: str,
    capability_required: str,
    input_data: Dict[str, Any],
    priority: int = 5,
    timeout_seconds: int = 300,
    tz: str = "UTC"
) -> ScheduledTask:
    """Create a new scheduled task"""
    schedule_id = f"sched_{secrets.token_hex(8)}"
    
    # Calculate first run time
    next_run = calculate_next_run(cron_expression)
    
    schedule = ScheduledTask(
        schedule_id=schedule_id,
        name=name,
        client_id=client_id,
        cron_expression=cron_expression,
        timezone=tz,
        task_type=task_type,
        capability_required=capability_required,
        input_data=input_data,
        priority=priority,
        timeout_seconds=timeout_seconds,
        active=True,
        next_run_at=next_run
    )
    
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    
    return schedule


def check_and_execute_scheduled_tasks(db: Session):
    """
    Check for scheduled tasks that need to run and execute them.
    Should be called periodically (e.g., every minute).
    """
    now = datetime.now(timezone.utc)
    
    # Find schedules that are due
    due_schedules = db.query(ScheduledTask).filter(
        ScheduledTask.active == True,
        ScheduledTask.next_run_at <= now
    ).all()
    
    for schedule in due_schedules:
        # Create task from schedule
        task = Task(
            task_id=f"task_{secrets.token_hex(8)}",
            client_id=schedule.client_id,
            task_type=schedule.task_type,
            capability_required=schedule.capability_required,
            input_data=schedule.input_data,
            priority=schedule.priority,
            timeout_seconds=schedule.timeout_seconds,
            status="PENDING"
        )
        db.add(task)
        
        # Update schedule
        schedule.last_run_at = now
        schedule.next_run_at = calculate_next_run(schedule.cron_expression, now)
        schedule.total_runs += 1
        
        db.commit()


# ============================================================================
# TASK TEMPLATES
# ============================================================================

def create_task_template(
    db: Session,
    name: str,
    client_id: str,
    task_type: str,
    capability_required: str,
    default_input_data: Dict[str, Any],
    description: Optional[str] = None,
    default_priority: int = 5,
    default_timeout: int = 300,
    default_max_retries: int = 3
) -> dict:
    """Create a reusable task template"""
    template_id = f"tmpl_{secrets.token_hex(8)}"
    
    template = dict(
        template_id=template_id,
        name=name,
        description=description,
        client_id=client_id,
        task_type=task_type,
        capability_required=capability_required,
        default_input_data=default_input_data,
        default_priority=default_priority,
        default_timeout=default_timeout,
        default_max_retries=default_max_retries,
        times_used=0
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


def create_task_from_template(
    db: Session,
    template_id: str,
    input_data: Optional[Dict[str, Any]] = None,
    priority: Optional[int] = None,
    timeout_seconds: Optional[int] = None
) -> Task:
    """Create a task instance from a template"""
    template = db.query(TaskTemplate).filter(
        TaskTemplate.template_id == template_id
    ).first()
    
    if not template:
        raise ValueError(f"Template {template_id} not found")
    
    # Merge template defaults with provided values
    final_input_data = {**template.default_input_data, **(input_data or {})}
    
    task = Task(
        task_id=f"task_{secrets.token_hex(8)}",
        client_id=template.client_id,
        task_type=template.task_type,
        capability_required=template.capability_required,
        input_data=final_input_data,
        priority=priority or template.default_priority,
        timeout_seconds=timeout_seconds or template.default_timeout,
        max_retries=template.default_max_retries,
        template_id=template_id,
        status="PENDING"
    )
    
    db.add(task)
    
    # Update usage counter
    template.times_used += 1
    
    db.commit()
    db.refresh(task)
    
    return task
