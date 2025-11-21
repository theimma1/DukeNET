"""AINS FastAPI Application"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import func, create_engine
import sys
import os

# Add parent directory to path to import aicp if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../aicp-core/python'))

from aicp import KeyPair  # Optional for signature/data management
from .db import Agent, AgentTag, Capability, TrustRecord, get_db, create_tables
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


# Lifespan event handler (replaces @app.on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    create_tables()
    print("✅ AINS API started - Database tables created")
    
    # Start background task for monitoring agent health
    import asyncio
    task = asyncio.create_task(monitor_agent_health_loop())
    
    yield
    
    # Shutdown logic
    try:
        task.cancel()
        await task
    except asyncio.CancelledError:
        pass
    print("AINS API shutting down...")


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
            # Task is being cancelled during shutdown
            break
        except Exception as e:
            print(f"Error in health monitoring: {e}")


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