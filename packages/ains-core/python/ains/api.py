"""AINS FastAPI Application"""
from .performance import get_system_stats, get_database_size, cleanup_old_data
from .webhooks import register_webhook, trigger_webhook_event, get_webhook_deliveries
from .db import Webhook, WebhookDelivery
from .batch import submit_batch_tasks, get_batch_status, cancel_batch_tasks
from .timeouts import cancel_task, set_task_timeout, check_timeouts
import uuid
from .schemas import TaskSubmission, TaskResponse
from .schemas import TaskSubmission as TaskSubmit
from typing import Optional, List
from fastapi import Query
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import func, create_engine, or_
import sys
import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .db import SessionLocal
from .routing import route_pending_tasks
from .queue import PriorityQueue, adjust_priority_by_age




# Add parent directory to path to import aicp if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../aicp-core/python'))

from aicp import KeyPair  # Optional for signature/data management
from .db import Agent, AgentTag, Capability, TrustRecord, Task, get_db, create_tables
from .cache import cache
from .trust import calculate_trust_score, update_trust_score

# Define database URL locally (not imported from db.py)
SQLALCHEMY_DATABASE_URL = "sqlite:///./ains.db"

# Create SessionLocal for background tasks
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AgentRegistration(BaseModel):
    agent_id: str
    public_key: str
    display_name: str
    description: Optional[str] = None
    endpoint: str
    signature: str  # Hex-encoded signature
    tags: Optional[List[str]] = None


class AgentResponse(BaseModel):
    agent_id: str
    public_key: str
    display_name: str
    description: Optional[str] = None
    endpoint: str
    status: str
    created_at: str
    trust_score: float
    tags: List[str] = []


class CapabilityPublish(BaseModel):
    name: str
    description: str
    input_schema: Dict
    output_schema: Dict
    pricing_model: str
    price: float
    latency_p99_ms: int
    availability_percent: float
    signature: str


class Heartbeat(BaseModel):
    timestamp: int  # Unix timestamp seconds
    status: str  # ACTIVE, DEGRADED, OFFLINE
    uptime_ms: int
    metrics: Optional[dict] = None


# Task-related models
class TaskSubmission(BaseModel):
    client_id: str = Field(..., description="Client identifier submitting the task")
    task_type: str = Field(..., description="Type of AI task (e.g., 'text-generation', 'image-analysis')")
    capability_required: str = Field(..., description="Required capability name")
    input_data: Dict[str, Any] = Field(..., description="Task input parameters")
    priority: Optional[int] = Field(5, ge=1, le=10, description="Task priority (1-10, higher = more urgent)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    timeout_seconds: Optional[int] = Field(300, gt=0, description="Task timeout in seconds")
    max_retries: Optional[int] = Field(3, ge=0, description="Maximum retry attempts")
    expires_at: Optional[str] = Field(None, description="ISO format expiration timestamp")


class TaskResponse(BaseModel):
    task_id: str
    client_id: str
    task_type: str
    capability_required: str
    status: str
    priority: int
    assigned_agent_id: Optional[str] = None
    created_at: str
    updated_at: str
    assigned_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int


class TaskUpdateStatus(BaseModel):
    status: str = Field(..., description="New task status (ACTIVE, COMPLETED, FAILED)")
    result_data: Optional[Dict[str, Any]] = Field(None, description="Task result data if completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")


# Lifespan event handler (replaces @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    print("✅ AINS API started - Database tables created")
    
    # Start background task routing worker
    routing_task = asyncio.create_task(task_routing_worker())
    
    yield
    
    # Shutdown
    routing_task.cancel()
    print("AINS API shutting down...")

async def task_routing_worker():
    """Background worker to route pending tasks"""
    while True:
        try:
            db = SessionLocal()
            try:
                routed = route_pending_tasks(db, limit=10)
                if routed > 0:
                    print(f"✅ Routed {routed} tasks")
            except Exception as e:
                print(f"Error in task routing: {e}")
            finally:
                db.close()
        except Exception as e:
            print(f"Task routing worker error: {e}")
        
        # Wait 5 seconds before next routing cycle
        await asyncio.sleep(5)

# Make sure to use this lifespan in your FastAPI app

app = FastAPI(title="AINS API", version="0.1.0", lifespan=lifespan)


async def monitor_agent_health_loop():
    """Background task to monitor agent health"""
    import asyncio
    while True:
        try:
            await asyncio.sleep(60)  # Run every 60 seconds
            session = SessionLocal()
            threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
            stale_agents = session.query(Agent).filter(
                Agent.last_heartbeat < threshold,
                Agent.status == "ACTIVE"
            ).all()
            for agent in stale_agents:
                agent.status = "INACTIVE"
                cache.invalidate_agent(agent.agent_id)
            session.commit()
            session.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in health monitoring: {e}")


async def task_routing_loop():
    """Background task to route pending tasks to suitable agents"""
    import asyncio
    while True:
        try:
            await asyncio.sleep(5)  # Run every 5 seconds
            session = SessionLocal()
            
            # Get pending tasks
            pending_tasks = session.query(Task).filter(
                Task.status == 'PENDING',
                or_(Task.expires_at.is_(None), Task.expires_at > datetime.now(timezone.utc))
            ).order_by(Task.priority.desc(), Task.created_at.asc()).limit(10).all()
            
            for task in pending_tasks:
                # Find suitable agent
                agent = find_suitable_agent(session, task.capability_required)
                
                if agent:
                    # Assign task to agent
                    task.assigned_agent_id = agent.agent_id
                    task.assigned_at = datetime.now(timezone.utc)
                    task.status = 'ASSIGNED'
                    task.updated_at = datetime.now(timezone.utc)
                    print(f"Task {task.task_id} assigned to agent {agent.agent_id}")
            
            session.commit()
            session.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in task routing: {e}")


async def task_monitoring_loop():
    """Background task to monitor task execution and handle timeouts/failures"""
    import asyncio
    while True:
        try:
            await asyncio.sleep(30)  # Run every 30 seconds
            session = SessionLocal()
            
            # Check for expired tasks
            now = datetime.now(timezone.utc)
            expired_tasks = session.query(Task).filter(
                Task.expires_at.isnot(None),
                Task.expires_at < now,
                Task.status.in_(['PENDING', 'ASSIGNED', 'ACTIVE'])
            ).all()
            
            for task in expired_tasks:
                task.status = 'FAILED'
                task.error_message = 'Task expired'
                task.updated_at = now
                print(f"Task {task.task_id} marked as expired")
            
            # Check for timed out tasks
            timeout_tasks = session.query(Task).filter(
                Task.status == 'ACTIVE',
                Task.started_at.isnot(None)
            ).all()
            
            for task in timeout_tasks:
                if task.started_at:
                    elapsed = (now - task.started_at).total_seconds()
                    if elapsed > task.timeout_seconds:
                        # Handle timeout - retry or fail
                        if task.retry_count < task.max_retries:
                            task.status = 'PENDING'
                            task.assigned_agent_id = None
                            task.assigned_at = None
                            task.started_at = None
                            task.retry_count += 1
                            task.updated_at = now
                            print(f"Task {task.task_id} timed out, retrying (attempt {task.retry_count})")
                        else:
                            task.status = 'FAILED'
                            task.error_message = f'Task timed out after {task.retry_count} retries'
                            task.completed_at = now
                            task.updated_at = now
                            print(f"Task {task.task_id} failed after max retries")
            
            session.commit()
            session.close()
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in task monitoring: {e}")


def find_suitable_agent(db: Session, capability_name: str) -> Optional[Agent]:
    """
    Find the most suitable agent for a given capability.
    Uses trust score and capability matching.
    """
    # Find agents with the required capability
    agents = db.query(Agent).join(Capability).filter(
        func.lower(Capability.name) == capability_name.lower(),
        Agent.status == 'ACTIVE',
        Capability.deprecated == False
    ).order_by(Agent.trust_score.desc()).limit(5).all()
    
    if not agents:
        return None
    
    # Return agent with highest trust score
    return agents[0]


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AINS", "version": "0.1.0"}


@app.post("/ains/agents", response_model=AgentResponse)
def register_agent(registration: AgentRegistration, db: Session = Depends(get_db)):
    existing_agent = db.query(Agent).filter(Agent.agent_id == registration.agent_id).first()
    if existing_agent:
        raise HTTPException(status_code=409, detail="Agent already registered")

    try:
        signature_bytes = bytes.fromhex(registration.signature)
        message = f"{registration.agent_id}{registration.endpoint}".encode()
        public_key_bytes = bytes.fromhex(registration.public_key)
        # TODO: Implement Ed25519 signature verification here
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    new_agent = Agent(
        agent_id=registration.agent_id,
        public_key=registration.public_key,
        display_name=registration.display_name,
        description=registration.description,
        endpoint_url=registration.endpoint,
        status='ACTIVE',
        created_at=datetime.now(timezone.utc),
        trust_score=50.0
    )
    db.add(new_agent)

    if registration.tags:
        for tag in registration.tags:
            db.add(AgentTag(agent_id=registration.agent_id, tag=tag))

    trust_record = TrustRecord(
        agent_id=registration.agent_id,
        trust_score=50.0,
        reputation_score=50.0,
        verified_signer=True
    )
    db.add(trust_record)
    db.commit()
    db.refresh(new_agent)

    agent_data = {
        "agent_id": new_agent.agent_id,
        "public_key": new_agent.public_key,
        "display_name": new_agent.display_name,
        "description": new_agent.description,
        "endpoint": new_agent.endpoint_url,
        "status": new_agent.status,
        "trust_score": float(new_agent.trust_score),
        "created_at": new_agent.created_at.isoformat()
    }
    cache.set_agent(new_agent.agent_id, agent_data)

    return AgentResponse(
        agent_id=new_agent.agent_id,
        public_key=new_agent.public_key,
        display_name=new_agent.display_name,
        description=new_agent.description,
        endpoint=new_agent.endpoint_url,
        status=new_agent.status,
        created_at=new_agent.created_at.isoformat(),
        trust_score=float(new_agent.trust_score),
        tags=registration.tags or []
    )


@app.get("/ains/agents/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    cached_agent = cache.get_agent(agent_id)
    if cached_agent:
        return AgentResponse(**cached_agent, tags=[])

    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    tags = db.query(AgentTag).filter(AgentTag.agent_id == agent_id).all()
    tag_list = [tag.tag for tag in tags]

    agent_data = {
        "agent_id": agent.agent_id,
        "public_key": agent.public_key,
        "display_name": agent.display_name,
        "description": agent.description,
        "endpoint": agent.endpoint_url,
        "status": agent.status,
        "trust_score": float(agent.trust_score),
        "created_at": agent.created_at.isoformat()
    }
    cache.set_agent(agent.agent_id, agent_data)

    return AgentResponse(
        agent_id=agent.agent_id,
        public_key=agent.public_key,
        display_name=agent.display_name,
        description=agent.description,
        endpoint=agent.endpoint_url,
        status=agent.status,
        created_at=agent.created_at.isoformat(),
        trust_score=float(agent.trust_score),
        tags=tag_list
    )


@app.get("/ains/agents")
def list_agents(
    status: Optional[str] = None,
    limit: int = Query(10, gt=0),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Agent)
    if status:
        query = query.filter(Agent.status == status)

    total = query.count()
    agents = query.limit(limit).offset(offset).all()

    return {
        "agents": [
            {
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "status": agent.status,
                "trust_score": float(agent.trust_score)
            }
            for agent in agents
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.post("/ains/agents/{agent_id}/capabilities")
def publish_capability(agent_id: str, cap: CapabilityPublish, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cap_id = f"{agent_id}:{cap.name}:{datetime.now(timezone.utc).isoformat()}"
    new_cap = Capability(
        capability_id=cap_id,
        agent_id=agent_id,
        name=cap.name,
        description=cap.description,
        version="v1.0.0",
        input_schema=cap.input_schema,
        output_schema=cap.output_schema,
        pricing_model=cap.pricing_model,
        price=cap.price,
        latency_p99_ms=cap.latency_p99_ms,
        availability_percent=cap.availability_percent,
        deprecated=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(new_cap)
    db.commit()
    db.refresh(new_cap)
    return {"capability_id": new_cap.capability_id, "status": "published"}


@app.get("/ains/agents/{agent_id}/capabilities")
def list_agent_capabilities(agent_id: str, db: Session = Depends(get_db)):
    caps = db.query(Capability).filter(Capability.agent_id == agent_id).all()
    return [
        {
            "capability_id": cap.capability_id,
            "name": cap.name,
            "description": cap.description,
            "pricing_model": cap.pricing_model,
            "price": float(cap.price) if cap.price else None,
            "availability_percent": float(cap.availability_percent),
        }
        for cap in caps
    ]


@app.get("/ains/search")
def search_agents(
    capability: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),  # comma-separated
    min_trust: Optional[float] = Query(0),
    sort_by: str = Query("trust_score"),
    limit: int = Query(10, gt=0),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Agent).join(Capability, Capability.agent_id == Agent.agent_id)

    if capability:
        query = query.filter(func.lower(Capability.name).like(f"%{capability.lower()}%"))
    if tags:
        tag_list = tags.split(",")
        query = query.join(AgentTag).filter(AgentTag.tag.in_(tag_list))
    if min_trust:
        query = query.filter(Agent.trust_score >= min_trust)

    total = query.distinct().count()

    if sort_by == "price":
        query = query.order_by(Capability.price.asc())
    elif sort_by == "latency":
        query = query.order_by(Capability.latency_p99_ms.asc())
    else:
        query = query.order_by(Agent.trust_score.desc())

    agents = query.distinct().limit(limit).offset(offset).all()

    results = []
    for agent in agents:
        caps = [cap.name for cap in agent.capabilities]
        results.append({
            "agent_id": agent.agent_id,
            "display_name": agent.display_name,
            "trust_score": float(agent.trust_score),
            "capabilities": caps,
        })

    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.post("/ains/agents/{agent_id}/heartbeat")
def send_heartbeat(agent_id: str, heartbeat: Heartbeat, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.last_heartbeat = datetime.now(timezone.utc)
    agent.status = heartbeat.status

    # Update uptime and metrics tracking here if needed

    cache.invalidate_agent(agent_id)
    db.commit()
    return {"acknowledged": True, "next_heartbeat_in": 300}


# ========== TASK ENDPOINTS (AITP - AI Task Protocol) ==========

@app.post("/aitp/tasks", response_model=TaskResponse)
def submit_task(task_submission: TaskSubmission, db: Session = Depends(get_db)):
    """
    Submit a new AI task for execution.
    Tasks are validated, queued, and automatically routed to suitable agents.
    """
    # Validate that the client agent exists
    client = db.query(Agent).filter(Agent.agent_id == task_submission.client_id).first()
    if not client:
        raise HTTPException(
            status_code=400,
            detail=f"Client agent '{task_submission.client_id}' not found"
        )
    
    # Validate that the required capability exists
    capability_exists = db.query(Capability).filter(
        func.lower(Capability.name) == task_submission.capability_required.lower(),
        Capability.deprecated == False
    ).first()
    
    if not capability_exists:
        raise HTTPException(
            status_code=400,
            detail=f"No agents provide capability '{task_submission.capability_required}'"
        )
    
    # Generate unique task ID
    task_id = f"task_{uuid.uuid4().hex[:16]}"
    
    # Parse expiration timestamp if provided
    expires_at = None
    if task_submission.expires_at:
        try:
            expires_at = datetime.fromisoformat(task_submission.expires_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at timestamp format")
    
    # Create new task
    new_task = Task(
        task_id=task_id,
        client_id=task_submission.client_id,
        task_type=task_submission.task_type,
        capability_required=task_submission.capability_required,
        input_data=task_submission.input_data,
        priority=task_submission.priority,
        expires_at=expires_at,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        # Retry fields (from Sprint 4.1)
        max_retries=getattr(task_submission, 'max_retries', 3),
        retry_count=0,
        retry_policy=getattr(task_submission, 'retry_policy', 'exponential')
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Return the created task
    return TaskResponse(
        task_id=new_task.task_id,
        client_id=new_task.client_id,
        task_type=new_task.task_type,
        capability_required=new_task.capability_required,
        status=new_task.status,
        priority=new_task.priority,
        assigned_agent_id=new_task.assigned_agent_id,
        created_at=new_task.created_at.isoformat(),
        updated_at=new_task.updated_at.isoformat(),
        assigned_at=new_task.assigned_at.isoformat() if new_task.assigned_at else None,
        started_at=new_task.started_at.isoformat() if new_task.started_at else None,
        completed_at=new_task.completed_at.isoformat() if new_task.completed_at else None,
        result_data=new_task.result_data,
        error_message=new_task.error_message,
        retry_count=new_task.retry_count
    )
    


@app.post("/aitp/tasks", response_model=TaskResponse)
def submit_task(task_submission: TaskSubmission, db: Session = Depends(get_db)):
    """
    Submit a new AI task for execution.
    Tasks are validated, queued, and automatically routed to suitable agents.
    """
    # Validate that the client agent exists
    client = db.query(Agent).filter(Agent.agent_id == task_submission.client_id).first()
    if not client:
        raise HTTPException(
            status_code=400,
            detail=f"Client agent '{task_submission.client_id}' not found"
        )
    
    # Validate that the required capability exists
    capability_exists = db.query(Capability).filter(
        func.lower(Capability.name) == task_submission.capability_required.lower(),
        Capability.deprecated == False
    ).first()
    
    if not capability_exists:
        raise HTTPException(
            status_code=400,
            detail=f"No agents provide capability '{task_submission.capability_required}'"
        )
    
    # Generate unique task ID
    task_id = f"task_{uuid.uuid4().hex[:16]}"
    
    # Parse expiration timestamp if provided
    expires_at = None
    if task_submission.expires_at:
        try:
            expires_at = datetime.fromisoformat(task_submission.expires_at.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expires_at timestamp format")
    
    # Create new task with retry fields (optional - use defaults if not provided)
    new_task = Task(
        task_id=task_id,
        client_id=task_submission.client_id,
        task_type=task_submission.task_type,
        capability_required=task_submission.capability_required,
        input_data=task_submission.input_data,
        priority=task_submission.priority,
        expires_at=expires_at,
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        # Retry fields - use getattr with defaults for backward compatibility
        max_retries=getattr(task_submission, 'max_retries', 3),
        retry_count=0,
        retry_policy=getattr(task_submission, 'retry_policy', 'exponential')
    )
    
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    
    # Return the created task as TaskResponse
    return TaskResponse(
        task_id=new_task.task_id,
        client_id=new_task.client_id,
        task_type=new_task.task_type,
        capability_required=new_task.capability_required,
        status=new_task.status,
        priority=new_task.priority,
        assigned_agent_id=new_task.assigned_agent_id,
        created_at=new_task.created_at.isoformat(),
        updated_at=new_task.updated_at.isoformat(),
        assigned_at=new_task.assigned_at.isoformat() if new_task.assigned_at else None,
        started_at=new_task.started_at.isoformat() if new_task.started_at else None,
        completed_at=new_task.completed_at.isoformat() if new_task.completed_at else None,
        result_data=new_task.result_data,
        error_message=new_task.error_message,
        retry_count=new_task.retry_count
    )



@app.get("/aitp/tasks")
def list_tasks(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    assigned_agent_id: Optional[str] = Query(None),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    List tasks with optional filtering.
    """
    query = db.query(Task)
    
    if client_id:
        query = query.filter(Task.client_id == client_id)
    if status:
        query = query.filter(Task.status == status)
    if task_type:
        query = query.filter(Task.task_type == task_type)
    if assigned_agent_id:
        query = query.filter(Task.assigned_agent_id == assigned_agent_id)
    
    total = query.count()
    tasks = query.order_by(Task.created_at.desc()).limit(limit).offset(offset).all()
    
    return {
        "tasks": [
            {
                "task_id": task.task_id,
                "client_id": task.client_id,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
                "assigned_agent_id": task.assigned_agent_id,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat()
            }
            for task in tasks
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@app.put("/aitp/tasks/{task_id}/status")
def update_task_status(
    task_id: str,
    agent_id: str,
    status_update: TaskUpdateStatus,
    db: Session = Depends(get_db)
):
    """
    Update task status (used by agents to report progress/completion).
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify the agent is assigned to this task
    if task.assigned_agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Agent not assigned to this task")
    
    now = datetime.now(timezone.utc)
    
    # Update status based on the new status
    if status_update.status == 'ACTIVE':
        if task.status not in ['ASSIGNED']:
            raise HTTPException(status_code=400, detail="Can only start ASSIGNED tasks")
        task.status = 'ACTIVE'
        task.started_at = now
        
    elif status_update.status == 'COMPLETED':
        if task.status not in ['ACTIVE']:
            raise HTTPException(status_code=400, detail="Can only complete ACTIVE tasks")
        task.status = 'COMPLETED'
        task.completed_at = now
        task.result_data = status_update.result_data
        
        # Update agent trust score on successful completion
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if agent and agent.trust_record:
            agent.trust_record.successful_transactions += 1
            # Recalculate trust score (simple increment for now)
            if agent.trust_score < 100:
                agent.trust_score = min(100.0, float(agent.trust_score) + 0.5)
        
    elif status_update.status == 'FAILED':
        if task.status not in ['ACTIVE', 'ASSIGNED']:
            raise HTTPException(status_code=400, detail="Invalid status transition to FAILED")
        
        # Check if we should retry
        if task.retry_count < task.max_retries:
            task.status = 'PENDING'
            task.assigned_agent_id = None
            task.assigned_at = None
            task.started_at = None
            task.retry_count += 1
            task.error_message = status_update.error_message
        else:
            task.status = 'FAILED'
            task.completed_at = now
            task.error_message = status_update.error_message
            
            # Update agent trust score on failure
            agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
            if agent and agent.trust_record:
                agent.trust_record.failed_transactions += 1
                # Decrease trust score
                if agent.trust_score > 0:
                    agent.trust_score = max(0.0, float(agent.trust_score) - 1.0)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_update.status}")
    
    task.updated_at = now
    db.commit()
    db.refresh(task)
    
    return {
        "task_id": task.task_id,
        "status": task.status,
        "retry_count": task.retry_count,
        "updated_at": task.updated_at.isoformat()
    }


@app.delete("/aitp/tasks/{task_id}")
def cancel_task_endpoint(
    task_id: str,
    client_id: str = Query(...),
    reason: str = Query("Cancelled by client"),
    db: Session = Depends(get_db)
):
    """
    Cancel a task.
    
    Only the task creator can cancel their tasks.
    Tasks can only be cancelled if not already completed/failed.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify client owns this task
    if task.client_id != client_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")
    
    # Attempt cancellation using the imported function
    from .timeouts import cancel_task
    success = cancel_task(db, task_id, client_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in {task.status} status"
        )
    
    # Refresh to get updated values
    db.refresh(task)
    
    return {
        "task_id": task_id,
        "status": "CANCELLED",
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,
        "reason": reason
    }


@app.get("/health/aitp")
async def aitp_health_check(db: Session = Depends(get_db)):
    """AITP health check with task queue metrics"""
    from sqlalchemy import func
    
    # Get task counts by status
    status_counts = db.query(
        Task.status,
        func.count(Task.task_id).label('count')
    ).group_by(Task.status).all()
    
    status_summary = {status: count for status, count in status_counts}
    
    # Calculate failure rate
    total_completed = status_summary.get('COMPLETED', 0) + status_summary.get('FAILED', 0)
    failure_rate = (status_summary.get('FAILED', 0) / total_completed * 100) if total_completed > 0 else 0
    
    return {
        "status": "healthy",
        "service": "AITP",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            "queue_depth": status_summary.get('PENDING', 0),
            "active_tasks": status_summary.get('ACTIVE', 0),
            "assigned_tasks": status_summary.get('ASSIGNED', 0),
            "completed_tasks": status_summary.get('COMPLETED', 0),
            "failed_tasks": status_summary.get('FAILED', 0),
            "failure_rate_percent": round(failure_rate, 2)
        }
    }
# Add this endpoint to your api.py

@app.post("/aitp/tasks/{task_id}/retry")
async def manually_retry_task(task_id: str, db: Session = Depends(get_db)):
    """Manually trigger a task retry
    
    This allows clients to retry a failed task immediately
    """
    from .retry import schedule_retry
    
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Only retry failed tasks
    if task.status not in ["FAILED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only retry FAILED tasks, current status: {task.status}"
        )
    
    # Schedule retry
    success = schedule_retry(db, task_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Task has exceeded maximum retries or is not retryable"
        )
    
    return {
        "task_id": task_id,
        "status": "PENDING",
        "retry_count": task.retry_count,
        "next_retry_at": task.next_retry_at
    }

@app.get("/aitp/queue/stats")
def get_queue_stats(db: Session = Depends(get_db)):
    """
    Get queue statistics by priority level.
    
    Returns queue depth, priority distribution, and workload balance.
    """
    queue = PriorityQueue(db)
    
    stats = queue.get_queue_stats()
    workload = queue.balance_workload()
    
    return {
        "queue": stats,
        "workload": workload,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.put("/aitp/tasks/{task_id}/priority")
def adjust_task_priority(
    task_id: str,
    new_priority: int = Query(..., ge=1, le=10),
    client_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Adjust task priority.
    
    Only the task creator can adjust priority.
    Priority must be between 1-10 (10=highest).
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify client owns this task
    if task.client_id != client_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this task")
    
    # Can only adjust priority of pending/assigned tasks
    if task.status not in ['PENDING', 'ASSIGNED']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot adjust priority of {task.status} task"
        )
    
    old_priority = task.priority
    task.priority = new_priority
    task.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(task)
    
    return {
        "task_id": task_id,
        "old_priority": old_priority,
        "new_priority": new_priority,
        "status": task.status
    }
@app.delete("/aitp/tasks/{task_id}")
def cancel_task_endpoint(
    task_id: str,
    client_id: str = Query(...),
    reason: str = Query("Cancelled by client"),
    db: Session = Depends(get_db)
):
    """Cancel a task"""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify client owns this task
    if task.client_id != client_id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this task")
    
    # Attempt cancellation
    success = cancel_task(db, task_id, client_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task in {task.status} status"
        )
    
    # Refresh to get updated values
    db.refresh(task)
    
    return {
        "task_id": task_id,
        "status": "CANCELLED",
        "cancelled_at": task.cancelled_at.isoformat() if task.cancelled_at else None,  # ← ADD THIS
        "reason": reason
    }



@app.put("/aitp/tasks/{task_id}/timeout")
def set_timeout_endpoint(
    task_id: str,
    timeout_seconds: int = Query(..., gt=0, le=86400),  # Max 24 hours
    client_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Set or update task timeout.
    
    Only the task creator can set timeouts.
    Timeout must be between 1 second and 24 hours.
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify client owns this task
    if task.client_id != client_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this task")
    
    # Set timeout
    success = set_task_timeout(db, task_id, timeout_seconds)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot set timeout on {task.status} task"
        )
    
    return {
        "task_id": task_id,
        "timeout_seconds": timeout_seconds,
        "status": task.status
    }


@app.post("/aitp/maintenance/check-timeouts")
def check_timeouts_endpoint(db: Session = Depends(get_db)):
    """
    Manually trigger timeout check.
    
    In production, this would run as a background worker.
    For testing/debugging, can be triggered manually.
    """
    timed_out = check_timeouts(db, limit=100)
    
    return {
        "timed_out_count": timed_out,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

class BatchTaskSpec(BaseModel):
    """Specification for a single task in a batch"""
    task_type: str
    capability_required: str
    input_data: Dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_policy: str = Field(default="exponential")
    timeout_seconds: int = Field(default=300)


class BatchTaskSubmission(BaseModel):
    """Batch task submission request"""
    client_id: str
    tasks: List[BatchTaskSpec]


@app.post("/aitp/tasks/batch")
def submit_batch_tasks_endpoint(
    batch: BatchTaskSubmission,
    db: Session = Depends(get_db)
):
    """
    Submit multiple tasks in a single batch.
    
    Maximum 1000 tasks per batch.
    All tasks are committed atomically.
    """
    if len(batch.tasks) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 tasks per batch"
        )
    
    if len(batch.tasks) == 0:
        raise HTTPException(
            status_code=400,
            detail="Batch must contain at least one task"
        )
    
    # Convert to dict format
    tasks_dict = [task.model_dump() for task in batch.tasks]

    
    result = submit_batch_tasks(db, batch.client_id, tasks_dict)
    
    return result


@app.get("/aitp/tasks/batch/status")
def get_batch_status_endpoint(
    task_ids: str = Query(..., description="Comma-separated task IDs"),
    db: Session = Depends(get_db)
):
    """
    Get status of multiple tasks.
    
    Pass task IDs as comma-separated string.
    Example: ?task_ids=task_123,task_456,task_789
    """
    task_id_list = [tid.strip() for tid in task_ids.split(',')]
    
    if len(task_id_list) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 tasks per request"
        )
    
    result = get_batch_status(db, task_id_list)
    
    return result


@app.post("/aitp/tasks/batch/cancel")  # ← Use POST instead of DELETE for batch operations
def cancel_batch_tasks_endpoint(
    task_ids: str = Query(..., description="Comma-separated task IDs"),
    client_id: str = Query(...),
    reason: str = Query("Batch cancellation"),
    db: Session = Depends(get_db)
):
    """
    Cancel multiple tasks in a batch.
    
    Pass task IDs as comma-separated string.
    """
    task_id_list = [tid.strip() for tid in task_ids.split(',')]
    
    if len(task_id_list) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 tasks per request"
        )
    
    result = cancel_batch_tasks(db, task_id_list, client_id, reason)
    
    return result

class WebhookRegistration(BaseModel):
    """Webhook registration request"""
    agent_id: str
    url: str
    events: List[str]
    secret: Optional[str] = None


@app.post("/ains/webhooks")
def register_webhook_endpoint(
    webhook: WebhookRegistration,
    db: Session = Depends(get_db)
):
    """
    Register a webhook for event notifications.
    
    Events:
    - task.created
    - task.assigned
    - task.started
    - task.completed
    - task.failed
    - task.cancelled
    """
    result = register_webhook(
        db,
        webhook.agent_id,
        webhook.url,
        webhook.events,
        webhook.secret
    )
    
    return {
        "webhook_id": result.webhook_id,
        "agent_id": result.agent_id,
        "url": result.url,
        "events": json.loads(result.events),
        "active": result.active,
        "created_at": result.created_at.isoformat()
    }


@app.get("/ains/webhooks/{webhook_id}")
def get_webhook_endpoint(
    webhook_id: str,
    db: Session = Depends(get_db)
):
    """Get webhook details"""
    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == webhook_id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {
        "webhook_id": webhook.webhook_id,
        "agent_id": webhook.agent_id,
        "url": webhook.url,
        "events": json.loads(webhook.events),
        "active": webhook.active,
        "created_at": webhook.created_at.isoformat(),
        "updated_at": webhook.updated_at.isoformat()
    }


@app.delete("/ains/webhooks/{webhook_id}")
def delete_webhook_endpoint(
    webhook_id: str,
    agent_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Delete/deactivate a webhook"""
    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == webhook_id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    if webhook.agent_id != agent_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    webhook.active = False
    webhook.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"webhook_id": webhook_id, "status": "deactivated"}


@app.get("/ains/webhooks/{webhook_id}/deliveries")
def get_webhook_deliveries_endpoint(
    webhook_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """Get webhook delivery history"""
    deliveries = get_webhook_deliveries(db, webhook_id, limit)
    
    return {
        "webhook_id": webhook_id,
        "deliveries": [
            {
                "delivery_id": d.delivery_id,
                "event_type": d.event_type,
                "status": d.status,
                "attempt_count": d.attempt_count,
                "response_code": d.response_code,
                "created_at": d.created_at.isoformat(),
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None
            }
            for d in deliveries
        ]
    }

@app.get("/ains/stats")
def get_stats_endpoint(db: Session = Depends(get_db)):
    """
    Get system-wide performance statistics.
    
    Returns metrics on tasks, agents, throughput, and performance.
    """
    stats = get_system_stats(db)
    return stats


@app.get("/ains/stats/database")
def get_database_stats_endpoint(db: Session = Depends(get_db)):
    """Get database size and table information"""
    stats = get_database_size(db)
    return stats


@app.post("/ains/maintenance/cleanup")
def cleanup_old_data_endpoint(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db)
):
    """
    Clean up old completed/failed tasks and deliveries.
    
    Deletes data older than specified days (default: 30 days).
    Minimum: 7 days, Maximum: 365 days.
    """
    result = cleanup_old_data(db, days)
    return result