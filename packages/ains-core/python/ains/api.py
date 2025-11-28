"""AINS FastAPI Application"""
from .trust_system import (
    get_agent_trust_metrics,
    get_trust_history,
    get_leaderboard,
    adjust_trust_score
)
from .db import TrustRecord
from .performance import get_system_stats, get_database_size, cleanup_old_data
from .webhooks import register_webhook, trigger_webhook_event, get_webhook_deliveries
from .db import Webhook, WebhookDelivery
from .batch import submit_batch_tasks, get_batch_status, cancel_batch_tasks
from .timeouts import cancel_task, set_task_timeout, check_timeouts
import uuid
from .schemas import AgentResponse
from .schemas import AgentResponse, AgentRegistration, TaskSubmission, TaskResponse
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
from .task_queue import PriorityQueue, adjust_priority_by_age
import secrets  # Add this if not already present

from .advanced_features import (
    check_dependencies, get_dependency_status, unblock_dependent_tasks,
    create_task_chain, execute_next_chain_step, on_chain_task_complete,
    route_task, calculate_next_run, create_scheduled_task,
    check_and_execute_scheduled_tasks, create_task_template,
    create_task_from_template
)
from .db import TaskChain, ScheduledTask, TaskTemplate

from fastapi.responses import Response as FastAPIResponse
from ains.observability.metrics import get_metrics, initialize_app_info
from ains.observability.middleware import PrometheusMiddleware
from ains.observability.metrics import record_task_created, update_queue_depth

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

# Initialize metrics with app info
initialize_app_info(version="1.0.0", environment="development")

# Add Prometheus middleware
app.add_middleware(PrometheusMiddleware)

# Add metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus exposition format
    """
    return FastAPIResponse(
        content=get_metrics(),
        media_type="text/plain; version=0.0.4"
    )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "DukeNet-AINS",
        "version": "1.0.0"
    }

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

    # Create new agent - using correct field names from Agent model
    new_agent = Agent(
        agent_id=registration.agent_id,
        public_key=registration.public_key,
        display_name=registration.display_name,
        endpoint=registration.endpoint,  # Changed from endpoint_url
        signature=registration.signature,
        tags=registration.tags or [],
        created_at=datetime.now(timezone.utc),
        last_seen_at=datetime.now(timezone.utc),
        trust_score=0.5  # Default trust score (0.0-1.0 range)
    )
    db.add(new_agent)
    
    # Don't add AgentTag separately - tags are stored as JSON in Agent model
    # The Agent model handles tags as a JSON field, not a separate table
    
    db.commit()
    db.refresh(new_agent)

    # Cache agent data
    agent_data = {
        "agent_id": new_agent.agent_id,
        "public_key": new_agent.public_key,
        "display_name": new_agent.display_name,
        "endpoint": new_agent.endpoint,
        "trust_score": float(new_agent.trust_score),
        "created_at": new_agent.created_at.isoformat(),
        "tags": new_agent.tags or []
    }
    cache.set_agent(new_agent.agent_id, agent_data)

    # ========== METRICS: Track agent registration ==========
    from ains.observability.metrics import agents_total, agents_active, update_agent_metrics
    
    # Update agent counts
    total_agents = db.query(Agent).count()
    active_agents = total_agents
    agents_total.set(total_agents)
    agents_active.set(active_agents)
    
    # Update individual agent trust score
    update_agent_metrics(
        agent_id=new_agent.agent_id,
        display_name=new_agent.display_name,
        trust_score=float(new_agent.trust_score)
    )
    # =======================================================

    return AgentResponse(
        agent_id=new_agent.agent_id,
        public_key=new_agent.public_key,
        display_name=new_agent.display_name,
        endpoint=new_agent.endpoint,
        created_at=new_agent.created_at.isoformat(),
        trust_score=float(new_agent.trust_score),
        tags=new_agent.tags or []
    )
# ========== AGENT ENDPOINTS ==========

    

# Trust & Reputation endpoints - ADD THESE BEFORE PARAMETERIZED ROUTES

@app.get("/ains/agents/leaderboard")
def get_agents_leaderboard(
    limit: int = 10,
    min_tasks: int = 0,
    db: Session = Depends(get_db)
):
    """Get top agents by trust score"""
    from .trust_system import get_leaderboard
    return get_leaderboard(db, limit=limit, min_tasks=min_tasks)


@app.get("/ains/agents/{agent_id}/trust")
def get_agent_trust_metrics(agent_id: str, db: Session = Depends(get_db)):
    """Get comprehensive trust metrics for an agent"""
    from .trust_system import get_trust_metrics
    return get_trust_metrics(db, agent_id)


@app.get("/ains/agents/{agent_id}/trust/history")
def get_agent_trust_history(
    agent_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get trust score history for an agent"""
    records = db.query(TrustRecord).filter(
        TrustRecord.agent_id == agent_id
    ).order_by(
        TrustRecord.created_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "record_id": r.record_id,
            "event_type": r.event_type,
            "trust_delta": r.trust_delta,
            "trust_score_before": r.trust_score_before,
            "trust_score_after": r.trust_score_after,
            "reason": r.reason,
            "task_id": r.task_id,
            "created_at": r.created_at.isoformat()
        }
        for r in records
    ]


@app.post("/ains/agents/{agent_id}/trust/adjust")
def manual_trust_adjustment(
    agent_id: str,
    adjustment: dict,
    db: Session = Depends(get_db)
):
    """Manually adjust an agent's trust score"""
    from .trust_system import adjust_trust_score
    
    record = adjust_trust_score(
        db,
        agent_id,
        "manual_adjustment",
        trust_delta=adjustment.get("trust_delta", 0.0),
        reason=adjustment.get("reason")
    )
    
    return {
        "record_id": record.record_id,
        "new_trust_score": record.trust_score_after,
        "trust_delta": record.trust_delta
    }


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

    try:
        # Map heartbeat status to agent model status
        status_mapping = {
            "ACTIVE": "AVAILABLE",
            "DEGRADED": "BUSY",
            "OFFLINE": "INACTIVE"
        }
        
        # Update timestamp and status
        agent.last_heartbeat = datetime.now(timezone.utc)
        
        # Only update status if the heartbeat status is valid
        if heartbeat.status in status_mapping:
            agent.status = status_mapping[heartbeat.status]
        
        cache.invalidate_agent(agent_id)
        db.commit()
        
        # ========== METRICS: Track agent heartbeat ==========
        from ains.observability.metrics import agents_active, update_agent_metrics
        
        active_agents = db.query(Agent).filter(Agent.status == "AVAILABLE").count()
        agents_active.set(active_agents)
        
        update_agent_metrics(
            agent_id=agent.agent_id,
            display_name=agent.display_name,
            trust_score=float(agent.trust_score)
        )
        
        return {
            "acknowledged": True,
            "next_heartbeat_in": 300,
            "agent_health_status": heartbeat.status,
            "agent_status": agent.status,
            "last_heartbeat": agent.last_heartbeat.isoformat()
        }
    
    except Exception as e:
        print(f"❌ Heartbeat error for agent {agent_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed: {str(e)}")



# ========== TASK ENDPOINTS (AITP - AI Task Protocol) ==========

@app.post("/ains/tasks")
def create_task(
    task_data: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new task.
    
    Request body:
    {
        "client_id": "client_1",
        "task_type": "analysis",
        "capability_required": "data:v1",
        "input_data": {"key": "value"},
        "priority": 5,
        "timeout_seconds": 300,
        "depends_on": ["task_001", "task_002"],  // Optional
        "routing_strategy": "round_robin"  // Optional
    }
    """
    task_id = f"task_{secrets.token_hex(8)}"
    
    # Check if depends_on tasks exist
    depends_on = task_data.get("depends_on", [])
    is_blocked = False
    
    if depends_on:
        for dep_id in depends_on:
            dep_task = db.query(Task).filter(Task.task_id == dep_id).first()
            if not dep_task:
                raise HTTPException(status_code=404, detail=f"Dependency task {dep_id} not found")
            if dep_task.status != "COMPLETED":
                is_blocked = True
    
    # Create task
    task = Task(
        task_id=task_id,
        client_id=task_data["client_id"],
        task_type=task_data["task_type"],
        capability_required=task_data["capability_required"],
        input_data=task_data["input_data"],
        priority=task_data.get("priority", 5),
        timeout_seconds=task_data.get("timeout_seconds", 300),
        max_retries=task_data.get("max_retries", 3),
        depends_on=depends_on,
        is_blocked=is_blocked,
        routing_strategy=task_data.get("routing_strategy", "round_robin"),
        status="PENDING"
    )
        
    db.add(task)
    db.commit()
    db.refresh(task)

    # ========== METRICS: Track task creation ==========
    from ains.observability.metrics import record_task_created, update_queue_depth
    record_task_created(
        task_type=task.task_type,
        client_id=task.client_id,
        priority=task.priority
    )
    
    # Update queue depth
    pending_count = db.query(Task).filter(Task.status == "PENDING").count()
    update_queue_depth(priority=task.priority, count=pending_count)
    # ===============================================
    
    # If not blocked, attempt to route the task
    if not is_blocked:
        agent_id = route_task(db, task)
        if agent_id:
            task.assigned_agent_id = agent_id
            task.status = "ASSIGNED"
            task.assigned_at = datetime.now(timezone.utc)
            db.commit()
    
    return {
        "task_id": task.task_id,
        "status": task.status,
        "priority": task.priority,
        "depends_on": task.depends_on,
        "is_blocked": task.is_blocked,
        "routing_strategy": task.routing_strategy,
        "assigned_agent_id": task.assigned_agent_id,
        "created_at": task.created_at.isoformat()
    }




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

    # ========== METRICS: Track task creation ==========
    from ains.observability.metrics import record_task_created, update_queue_depth
    record_task_created(
        task_type=new_task.task_type,
        client_id=new_task.client_id,
        priority=new_task.priority
    )
    
    # Update queue depth
    pending_count = db.query(Task).filter(Task.status == "PENDING").count()
    update_queue_depth(priority=new_task.priority, count=pending_count)
    # ==================================================

    
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
    
    # ========== METRICS: Track task completion/failure ==========
    from ains.observability.metrics import record_task_completed, record_task_failed, record_task_retry
    
    # Calculate duration if task is completed or failed
    if task.status in ["COMPLETED", "FAILED"]:
        if task.started_at:
            duration = (now - task.started_at).total_seconds()
        else:
            duration = 0
        
        if task.status == "COMPLETED":
            record_task_completed(
                task_type=task.task_type,
                agent_id=agent_id,
                duration_seconds=duration
            )
        elif task.status == "FAILED":
            record_task_failed(
                task_type=task.task_type,
                agent_id=agent_id,
                failure_reason=task.error_message[:50] if task.error_message else "unknown",
                duration_seconds=duration
            )
    
    # Track retry if task was retried
    if status_update.status == 'FAILED' and task.retry_count > 0 and task.status == 'PENDING':
        record_task_retry(
            task_type=task.task_type,
            retry_count=task.retry_count
        )
    # ============================================================
    
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

@app.get("/ains/agents/{agent_id}/trust")
def get_agent_trust_endpoint(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """
    Get trust score and performance metrics for an agent.
    
    Returns comprehensive trust metrics including:
    - Current trust score and level
    - Total tasks completed/failed
    - Success rate
    - Average completion time
    - Recent activity (last 30 days)
    """
    try:
        metrics = get_agent_trust_metrics(db, agent_id)
        return metrics
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/ains/agents/{agent_id}/trust/history")
def get_agent_trust_history_endpoint(
    agent_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Get trust score history for an agent.
    
    Shows all trust adjustments with reasons and deltas.
    """
    history = get_trust_history(db, agent_id, limit)
    
    return {
        "agent_id": agent_id,
        "history": [
            {
                "record_id": record.record_id,
                "event_type": record.event_type,
                "task_id": record.task_id,
                "trust_delta": round(record.trust_delta, 3),
                "trust_score_before": round(record.trust_score_before, 3),
                "trust_score_after": round(record.trust_score_after, 3),
                "reason": record.reason,
                "created_at": record.created_at.isoformat()
            }
            for record in history
        ]
    }


@app.get("/ains/agents/leaderboard")
def get_leaderboard_endpoint(
    limit: int = Query(10, ge=1, le=100),
    min_tasks: int = Query(10, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    from .trust_system import get_leaderboard
    return get_leaderboard(db, limit=limit, min_tasks=min_tasks)
    


@app.post("/ains/agents/{agent_id}/trust/adjust")
def adjust_trust_manual_endpoint(
    agent_id: str,
    trust_delta: float = Query(..., ge=-1.0, le=1.0),
    reason: str = Query(...),
    admin_key: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Manually adjust agent trust score (admin only).
    
    Requires admin authentication key.
    Used for policy violations, fraud, or exceptional service.
    """
    # TODO: Implement proper admin authentication
    # For now, use a simple check
    if admin_key != "admin_secret_key_123":  # Replace with proper auth
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    try:
        record = adjust_trust_score(
            db, agent_id, "manual_adjustment",
            trust_delta, reason=reason
        )
        
        return {
            "record_id": record.record_id,
            "agent_id": agent_id,
            "trust_delta": round(trust_delta, 3),
            "trust_score_before": round(record.trust_score_before, 3),
            "trust_score_after": round(record.trust_score_after, 3),
            "reason": reason
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Add these imports at the top
from .auth import (
    generate_api_key, hash_api_key, require_api_key, 
    log_security_event, check_rate_limit
)
from .db import APIKey, AuditLog, RateLimitTracker

# Add these endpoints (place them appropriately in your api.py file)

# ============================================================================
# API KEY MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/ains/api-keys")
def create_api_key(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new API key.
    
    Request body:
    {
        "client_id": "client_123",
        "name": "Production Key",
        "description": "Main production API key",
        "scopes": ["task:read", "task:write", "agent:read"],
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000,
        "expires_in_days": 365
    }
    """
    # Generate new key
    key_id, api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Calculate expiration
    expires_at = None
    if request.get("expires_in_days"):
        expires_at = datetime.now(timezone.utc) + timedelta(days=request["expires_in_days"])
    
    # Create API key record
    api_key_record = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        client_id=request["client_id"],
        name=request["name"],
        description=request.get("description"),
        scopes=request.get("scopes", []),
        rate_limit_per_minute=request.get("rate_limit_per_minute", 60),
        rate_limit_per_hour=request.get("rate_limit_per_hour", 1000),
        expires_at=expires_at,
        created_by=request.get("created_by")
    )
    
    db.add(api_key_record)
    db.commit()
    db.refresh(api_key_record)
    
    # Log key creation
    log_security_event(
        db, "api_key_created", "create_api_key", True,
        client_id=request["client_id"],
        key_id=key_id,
        extra_metadata={"name": request["name"]}
    )
    
    # Return the actual key (only time it's shown!)
    return {
        "key_id": key_id,
        "api_key": api_key,  # ⚠️ ONLY SHOWN ONCE
        "client_id": api_key_record.client_id,
        "name": api_key_record.name,
        "scopes": api_key_record.scopes,
        "rate_limit_per_minute": api_key_record.rate_limit_per_minute,
        "rate_limit_per_hour": api_key_record.rate_limit_per_hour,
        "expires_at": api_key_record.expires_at.isoformat() if api_key_record.expires_at else None,
        "created_at": api_key_record.created_at.isoformat(),
        "warning": "Save this API key securely. It will not be shown again."
    }


@app.get("/ains/api-keys")
def list_api_keys(
    client_id: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all API keys (with filters)"""
    query = db.query(APIKey)
    
    if client_id:
        query = query.filter(APIKey.client_id == client_id)
    
    if active_only:
        query = query.filter(APIKey.active == True)
    
    keys = query.order_by(APIKey.created_at.desc()).all()
    
    return [
        {
            "key_id": key.key_id,
            "client_id": key.client_id,
            "name": key.name,
            "description": key.description,
            "scopes": key.scopes,
            "active": key.active,
            "rate_limit_per_minute": key.rate_limit_per_minute,
            "rate_limit_per_hour": key.rate_limit_per_hour,
            "created_at": key.created_at.isoformat(),
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None
        }
        for key in keys
    ]


@app.get("/ains/api-keys/{key_id}")
def get_api_key(
    key_id: str,
    db: Session = Depends(get_db)
):
    """Get details of a specific API key"""
    api_key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {
        "key_id": api_key.key_id,
        "client_id": api_key.client_id,
        "name": api_key.name,
        "description": api_key.description,
        "scopes": api_key.scopes,
        "active": api_key.active,
        "rate_limit_per_minute": api_key.rate_limit_per_minute,
        "rate_limit_per_hour": api_key.rate_limit_per_hour,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None
    }


@app.patch("/ains/api-keys/{key_id}")
def update_api_key(
    key_id: str,
    updates: dict,
    db: Session = Depends(get_db)
):
    """Update API key settings"""
    api_key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Update allowed fields
    if "name" in updates:
        api_key.name = updates["name"]
    if "description" in updates:
        api_key.description = updates["description"]
    if "scopes" in updates:
        api_key.scopes = updates["scopes"]
    if "rate_limit_per_minute" in updates:
        api_key.rate_limit_per_minute = updates["rate_limit_per_minute"]
    if "rate_limit_per_hour" in updates:
        api_key.rate_limit_per_hour = updates["rate_limit_per_hour"]
    if "active" in updates:
        api_key.active = updates["active"]
    
    db.commit()
    db.refresh(api_key)
    
    # Log update
    log_security_event(
        db, "api_key_updated", "update_api_key", True,
        client_id=api_key.client_id,
        key_id=key_id,
        extra_metadata=updates
    )
    
    return {
        "key_id": api_key.key_id,
        "message": "API key updated successfully"
    }


@app.delete("/ains/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    db: Session = Depends(get_db)
):
    """Revoke (deactivate) an API key"""
    api_key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.active = False
    db.commit()
    
    # Log revocation
    log_security_event(
        db, "api_key_revoked", "revoke_api_key", True,
        client_id=api_key.client_id,
        key_id=key_id
    )
    
    return {
        "key_id": key_id,
        "message": "API key revoked successfully"
    }


@app.get("/ains/api-keys/{key_id}/usage")
def get_api_key_usage(
    key_id: str,
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """Get usage statistics for an API key"""
    api_key = db.query(APIKey).filter(APIKey.key_id == key_id).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Get recent rate limit entries
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    usage_data = db.query(RateLimitTracker).filter(
        RateLimitTracker.key_id == key_id,
        RateLimitTracker.window_start >= cutoff
    ).order_by(RateLimitTracker.window_start.desc()).all()
    
    # Calculate total requests
    total_requests = sum(entry.request_count for entry in usage_data)
    
    # Get hourly breakdown
    hourly_usage = {}
    for entry in usage_data:
        if entry.window_type == "hour":
            hour_key = entry.window_start.strftime("%Y-%m-%d %H:00")
            hourly_usage[hour_key] = entry.request_count
    
    return {
        "key_id": key_id,
        "client_id": api_key.client_id,
        "period_hours": hours,
        "total_requests": total_requests,
        "rate_limit_per_minute": api_key.rate_limit_per_minute,
        "rate_limit_per_hour": api_key.rate_limit_per_hour,
        "hourly_usage": hourly_usage,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None
    }


# ============================================================================
# AUDIT LOG ENDPOINTS
# ============================================================================

@app.get("/ains/audit-logs")
def get_audit_logs(
    client_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get security audit logs"""
    query = db.query(AuditLog)
    
    if client_id:
        query = query.filter(AuditLog.client_id == client_id)
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "action": log.action,
            "client_id": log.client_id,
            "key_id": log.key_id,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "success": log.success,
            "error_message": log.error_message,
            "extra_metadata": log.extra_metadata,  # Changed from metadata
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]



# ============================================================================
# PROTECTED ENDPOINT EXAMPLE
# ============================================================================

@app.get("/ains/protected/test")
def protected_test_endpoint(api_key: APIKey = Depends(require_api_key)):
    """Example protected endpoint requiring API key authentication"""
    return {
        "message": "Authentication successful!",
        "client_id": api_key.client_id,
        "key_name": api_key.name,
        "scopes": api_key.scopes
    }
# ============================================================================
# TASK DEPENDENCIES
# ============================================================================

@app.get("/ains/tasks/{task_id}/dependencies")
def get_task_dependencies(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get dependency status for a task"""
    return get_dependency_status(db, task_id)


@app.get("/ains/tasks/{task_id}/dependents")
def get_task_dependents(
    task_id: str,
    db: Session = Depends(get_db)
):
    """Get tasks that depend on this task"""
    # Find all tasks that list this task in their depends_on
    all_tasks = db.query(Task).filter(Task.status == "PENDING").all()
    
    dependents = []
    for task in all_tasks:
        if task_id in (task.depends_on or []):
            dependents.append({
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "is_blocked": task.is_blocked
            })
    
    return {
        "task_id": task_id,
        "dependent_tasks": dependents,
        "dependent_count": len(dependents)
    }


# ============================================================================
# TASK CHAINS
# ============================================================================

@app.post("/ains/task-chains")
def create_chain(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new task chain.
    
    Request body:
    {
        "name": "Data Processing Pipeline",
        "client_id": "client_1",
        "steps": [
            {
                "name": "fetch_data",
                "task_type": "fetch",
                "capability_required": "api:v1",
                "input_data": {"source": "database"}
            },
            {
                "name": "process_data",
                "task_type": "process",
                "capability_required": "data:v1",
                "input_data": {"operation": "transform"},
                "use_previous_output": true
            }
        ]
    }
    """
    chain = create_task_chain(
        db,
        name=request["name"],
        client_id=request["client_id"],
        steps=request["steps"]
    )
    
    return {
        "chain_id": chain.chain_id,
        "name": chain.name,
        "status": chain.status,
        "total_steps": len(chain.steps),
        "current_step": chain.current_step,
        "created_at": chain.created_at.isoformat()
    }


@app.get("/ains/task-chains/{chain_id}")
def get_chain(
    chain_id: str,
    db: Session = Depends(get_db)
):
    """Get task chain status"""
    chain = db.query(TaskChain).filter(TaskChain.chain_id == chain_id).first()
    
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    return {
        "chain_id": chain.chain_id,
        "name": chain.name,
        "client_id": chain.client_id,
        "status": chain.status,
        "current_step": chain.current_step,
        "total_steps": len(chain.steps),
        "steps": chain.steps,
        "step_results": chain.step_results,
        "created_at": chain.created_at.isoformat(),
        "started_at": chain.started_at.isoformat() if chain.started_at else None,
        "completed_at": chain.completed_at.isoformat() if chain.completed_at else None,
        "error_message": chain.error_message
    }


@app.get("/ains/task-chains")
def list_chains(
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List task chains"""
    query = db.query(TaskChain)
    
    if client_id:
        query = query.filter(TaskChain.client_id == client_id)
    
    if status:
        query = query.filter(TaskChain.status == status)
    
    chains = query.order_by(TaskChain.created_at.desc()).limit(limit).all()
    
    return [
        {
            "chain_id": chain.chain_id,
            "name": chain.name,
            "status": chain.status,
            "current_step": chain.current_step,
            "total_steps": len(chain.steps),
            "created_at": chain.created_at.isoformat()
        }
        for chain in chains
    ]


@app.post("/ains/task-chains/{chain_id}/cancel")
def cancel_chain(
    chain_id: str,
    db: Session = Depends(get_db)
):
    """Cancel a running task chain"""
    chain = db.query(TaskChain).filter(TaskChain.chain_id == chain_id).first()
    
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    
    if chain.status not in ["PENDING", "RUNNING"]:
        raise HTTPException(status_code=400, detail="Chain already completed or failed")
    
    chain.status = "CANCELLED"
    chain.completed_at = datetime.now(timezone.utc)
    chain.error_message = "Cancelled by user"
    
    # Cancel any running tasks in this chain
    db.query(Task).filter(
        Task.chain_id == chain_id,
        Task.status.in_(["PENDING", "ASSIGNED", "RUNNING"])
    ).update({
        "status": "CANCELLED",
        "cancelled_at": datetime.now(timezone.utc),
        "cancellation_reason": "Parent chain cancelled"
    })
    
    db.commit()
    
    return {"chain_id": chain_id, "message": "Chain cancelled successfully"}


# ============================================================================
# ROUTING STRATEGIES
# ============================================================================

@app.get("/ains/routing/strategies")
def list_routing_strategies():
    """List available routing strategies"""
    return {
        "strategies": [
            {
                "name": "round_robin",
                "description": "Distribute tasks evenly across all capable agents"
            },
            {
                "name": "least_loaded",
                "description": "Route to agent with fewest active tasks"
            },
            {
                "name": "trust_weighted",
                "description": "Route based on agent trust score (favors higher trust)"
            },
            {
                "name": "fastest_response",
                "description": "Route to agent with lowest average completion time"
            }
        ],
        "default": "round_robin"
    }


@app.post("/ains/routing/test")
def test_routing_strategy(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Test a routing strategy to see which agent would be selected.
    
    Request body:
    {
        "capability_required": "data:v1",
        "routing_strategy": "trust_weighted"
    }
    """
    # Create a mock task for testing
    mock_task = Task(
        task_id="test",
        client_id="test",
        task_type="test",
        capability_required=request["capability_required"],
        routing_strategy=request.get("routing_strategy", "round_robin"),
        status="PENDING"
    )
    
    agent_id = route_task(db, mock_task)
    
    if agent_id:
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        return {
            "selected_agent": {
                "agent_id": agent.agent_id,
                "display_name": agent.display_name,
                "trust_score": agent.trust_score,
                "total_tasks": agent.total_tasks_completed
            },
            "strategy_used": request.get("routing_strategy", "round_robin")
        }
    else:
        return {
            "selected_agent": None,
            "message": "No capable agents found",
            "strategy_used": request.get("routing_strategy", "round_robin")
        }


# ============================================================================
# SCHEDULED TASKS
# ============================================================================

@app.post("/ains/scheduled-tasks")
def create_schedule(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new scheduled task.
    
    Request body:
    {
        "name": "Daily Data Sync",
        "client_id": "client_1",
        "cron_expression": "0 2 * * *",
        "timezone": "America/New_York",
        "task_type": "sync",
        "capability_required": "sync:v1",
        "input_data": {"source": "api"},
        "priority": 7,
        "timeout_seconds": 600
    }
    """
    schedule = create_scheduled_task(
        db,
        name=request["name"],
        client_id=request["client_id"],
        cron_expression=request["cron_expression"],
        task_type=request["task_type"],
        capability_required=request["capability_required"],
        input_data=request["input_data"],
        priority=request.get("priority", 5),
        timeout_seconds=request.get("timeout_seconds", 300),
        tz=request.get("timezone", "UTC")
    )
    
    return {
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "cron_expression": schedule.cron_expression,
        "active": schedule.active,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "created_at": schedule.created_at.isoformat()
    }


@app.get("/ains/scheduled-tasks")
def list_schedules(
    client_id: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List scheduled tasks"""
    query = db.query(ScheduledTask)
    
    if client_id:
        query = query.filter(ScheduledTask.client_id == client_id)
    
    if active_only:
        query = query.filter(ScheduledTask.active == True)
    
    schedules = query.order_by(ScheduledTask.created_at.desc()).all()
    
    return {
        "schedules": [
            {
                "schedule_id": sched.schedule_id,
                "name": sched.name,
                "cron_expression": sched.cron_expression,
                "task_type": sched.task_type,
                "active": sched.active,
                "last_run_at": sched.last_run_at.isoformat() if sched.last_run_at else None,
                "next_run_at": sched.next_run_at.isoformat() if sched.next_run_at else None,
                "total_runs": sched.total_runs,
                "successful_runs": sched.successful_runs,
                "failed_runs": sched.failed_runs
            }
            for sched in schedules
        ]
    }


@app.get("/ains/scheduled-tasks/{schedule_id}")
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db)
):
    """Get scheduled task details"""
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "client_id": schedule.client_id,
        "cron_expression": schedule.cron_expression,
        "timezone": schedule.timezone,
        "task_type": schedule.task_type,
        "capability_required": schedule.capability_required,
        "input_data": schedule.input_data,
        "priority": schedule.priority,
        "timeout_seconds": schedule.timeout_seconds,
        "active": schedule.active,
        "created_at": schedule.created_at.isoformat(),
        "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
        "total_runs": schedule.total_runs,
        "successful_runs": schedule.successful_runs,
        "failed_runs": schedule.failed_runs
    }


@app.patch("/ains/scheduled-tasks/{schedule_id}")
def update_schedule(
    schedule_id: str,
    updates: dict,
    db: Session = Depends(get_db)
):
    """Update scheduled task settings"""
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Update allowed fields
    if "active" in updates:
        schedule.active = updates["active"]
    if "cron_expression" in updates:
        schedule.cron_expression = updates["cron_expression"]
        # Recalculate next run
        schedule.next_run_at = calculate_next_run(updates["cron_expression"])
    if "priority" in updates:
        schedule.priority = updates["priority"]
    if "timeout_seconds" in updates:
        schedule.timeout_seconds = updates["timeout_seconds"]
    
    db.commit()
    db.refresh(schedule)
    
    return {
        "schedule_id": schedule_id,
        "message": "Schedule updated successfully"
    }


@app.delete("/ains/scheduled-tasks/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db)
):
    """Delete a scheduled task"""
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    
    return {
        "schedule_id": schedule_id,
        "message": "Schedule deleted successfully"
    }


@app.post("/ains/scheduled-tasks/{schedule_id}/run-now")
def trigger_schedule_now(
    schedule_id: str,
    db: Session = Depends(get_db)
):
    """Manually trigger a scheduled task to run immediately"""
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
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
    db.commit()
    db.refresh(task)
    
    return {
        "message": "Task triggered successfully",
        "task_id": task.task_id,
        "schedule_id": schedule_id
    }


# ============================================================================
# TASK TEMPLATES
# ============================================================================

@app.post("/ains/task-templates")
def create_template(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Create a new task template.
    
    Request body:
    {
        "name": "Standard Data Analysis",
        "description": "Template for basic data analysis tasks",
        "client_id": "client_1",
        "task_type": "analysis",
        "capability_required": "data:v1",
        "default_input_data": {
            "algorithm": "standard",
            "output_format": "json"
        },
        "default_priority": 6,
        "default_timeout": 600
    }
    """
    template = create_task_template(
        db,
        name=request["name"],
        client_id=request["client_id"],
        task_type=request["task_type"],
        capability_required=request["capability_required"],
        default_input_data=request["default_input_data"],
        description=request.get("description"),
        default_priority=request.get("default_priority", 5),
        default_timeout=request.get("default_timeout", 300),
        default_max_retries=request.get("default_max_retries", 3)
    )
    
    return {
        "template_id": template.template_id,
        "name": template.name,
        "task_type": template.task_type,
        "created_at": template.created_at.isoformat()
    }


@app.get("/ains/task-templates")
def list_templates(
    client_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List task templates"""
    query = db.query(TaskTemplate)
    
    if client_id:
        query = query.filter(TaskTemplate.client_id == client_id)
    
    templates = query.order_by(TaskTemplate.created_at.desc()).all()
    
    return [
        {
            "template_id": tmpl.template_id,
            "name": tmpl.name,
            "description": tmpl.description,
            "task_type": tmpl.task_type,
            "times_used": tmpl.times_used,
            "created_at": tmpl.created_at.isoformat()
        }
        for tmpl in templates
    ]


@app.get("/ains/task-templates/{template_id}")
def get_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """Get task template details"""
    template = db.query(TaskTemplate).filter(
        TaskTemplate.template_id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "template_id": template.template_id,
        "name": template.name,
        "description": template.description,
        "client_id": template.client_id,
        "task_type": template.task_type,
        "capability_required": template.capability_required,
        "default_input_data": template.default_input_data,
        "default_priority": template.default_priority,
        "default_timeout": template.default_timeout,
        "default_max_retries": template.default_max_retries,
        "times_used": template.times_used,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat() if template.updated_at else None
    }


@app.post("/ains/tasks/from-template")
def create_task_from_template_endpoint(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Create a task from a template.
    
    Request body:
    {
        "template_id": "tmpl_123",
        "input_data": {
            "file": "data.csv",
            "algorithm": "advanced"
        },
        "priority": 8
    }
    """
    task = create_task_from_template(
        db,
        template_id=request["template_id"],
        input_data=request.get("input_data"),
        priority=request.get("priority"),
        timeout_seconds=request.get("timeout_seconds")
    )
    
    return {
        "task_id": task.task_id,
        "template_id": request["template_id"],
        "status": task.status,
        "created_at": task.created_at.isoformat()
    }


@app.patch("/ains/task-templates/{template_id}")
def update_template(
    template_id: str,
    updates: dict,
    db: Session = Depends(get_db)
):
    """Update task template"""
    template = db.query(TaskTemplate).filter(
        TaskTemplate.template_id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Update allowed fields
    if "name" in updates:
        template.name = updates["name"]
    if "description" in updates:
        template.description = updates["description"]
    if "default_input_data" in updates:
        template.default_input_data = updates["default_input_data"]
    if "default_priority" in updates:
        template.default_priority = updates["default_priority"]
    if "default_timeout" in updates:
        template.default_timeout = updates["default_timeout"]
    
    db.commit()
    
    return {
        "template_id": template_id,
        "message": "Template updated successfully"
    }


@app.delete("/ains/task-templates/{template_id}")
def delete_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """Delete a task template"""
    template = db.query(TaskTemplate).filter(
        TaskTemplate.template_id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    db.delete(template)
    db.commit()
    
    return {
        "template_id": template_id,
        "message": "Template deleted successfully"
    }