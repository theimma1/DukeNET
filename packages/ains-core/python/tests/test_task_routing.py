"""Test task routing and assignment"""
import os
import tempfile
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db
from ains.routing import find_best_agent_for_task, route_pending_tasks

# Create temporary test database
temp_db_fd, temp_db_path = tempfile.mkstemp()
SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{temp_db_path}"
test_engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create tables
Base.metadata.create_all(bind=test_engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_find_best_agent_with_trust_scores():
    """Test that routing selects agent with highest trust score"""
    # Use API to create agents properly
    agent1_payload = {
        "agent_id": f"agent_{secrets.token_hex(4)}",
        "display_name": "Agent 1",
        "endpoint": "http://localhost:8001",
        "public_key": secrets.token_hex(32),
        "signature": secrets.token_hex(64),
        "tags": ["test"]
    }
    agent2_payload = {
        "agent_id": f"agent_{secrets.token_hex(4)}",
        "display_name": "Agent 2",
        "endpoint": "http://localhost:8002",
        "public_key": secrets.token_hex(32),
        "signature": secrets.token_hex(64),
        "tags": ["test"]
    }
    
    resp1 = client.post("/ains/agents", json=agent1_payload)
    resp2 = client.post("/ains/agents", json=agent2_payload)
    
    agent1_id = resp1.json()["agent_id"]
    agent2_id = resp2.json()["agent_id"]
    
    # Publish capabilities
    cap_payload = {
        "name": "summarization:v1",
        "description": "Summarization",
        "input_schema": {},
        "output_schema": {},
        "pricing_model": "per_request",
        "price": 0.01,
        "latency_p99_ms": 100,
        "availability_percent": 99.0,
        "signature": secrets.token_hex(64)
    }
    
    client.post(f"/ains/agents/{agent1_id}/capabilities", json=cap_payload)
    client.post(f"/ains/agents/{agent2_id}/capabilities", json=cap_payload)
    
    # Update trust scores (they already exist from agent registration)
    db = TestingSessionLocal()
    from ains.db import TrustRecord
    
    trust1 = db.query(TrustRecord).filter(TrustRecord.agent_id == agent1_id).first()
    trust2 = db.query(TrustRecord).filter(TrustRecord.agent_id == agent2_id).first()
    
    trust1.trust_score = 0.7
    trust2.trust_score = 0.9
    
    db.commit()
    
    # Find best agent
    best_agent = find_best_agent_for_task(db, "summarization:v1")
    
    assert best_agent == agent2_id  # Should select agent with higher trust
    
    db.close()


def test_route_pending_tasks():
    """Test that pending tasks get routed to agents"""
    # Create agent via API
    agent_payload = {
        "agent_id": f"agent_{secrets.token_hex(4)}",
        "display_name": "Test Agent",
        "endpoint": "http://localhost:8000",
        "public_key": secrets.token_hex(32),
        "signature": secrets.token_hex(64),
        "tags": ["test"]
    }
    
    resp = client.post("/ains/agents", json=agent_payload)
    agent_id = resp.json()["agent_id"]
    
    # Publish capability
    cap_payload = {
        "name": "translation:v1",
        "description": "Translation",
        "input_schema": {},
        "output_schema": {},
        "pricing_model": "per_request",
        "price": 0.01,
        "latency_p99_ms": 100,
        "availability_percent": 99.0,
        "signature": secrets.token_hex(64)
    }
    
    client.post(f"/ains/agents/{agent_id}/capabilities", json=cap_payload)
    
    # Update trust score (already exists from agent registration)
    db = TestingSessionLocal()
    from ains.db import TrustRecord
    
    trust = db.query(TrustRecord).filter(TrustRecord.agent_id == agent_id).first()
    trust.trust_score = 0.8
    db.commit()
    
    # Create a pending task via API
    task_payload = {
        "client_id": agent_id,
        "task_type": "translation",
        "capability_required": "translation:v1",
        "input_data": {"text": "Hello"},
        "priority": 5
    }
    
    task_resp = client.post("/aitp/tasks", json=task_payload)
    task_id = task_resp.json()["task_id"]
    
    # Route tasks
    routed_count = route_pending_tasks(db, limit=10)
    
    assert routed_count == 1
    
    # Verify task was assigned
    from ains.db import Task
    task = db.query(Task).filter(Task.task_id == task_id).first()
    assert task.status == "ASSIGNED"
    assert task.assigned_agent_id == agent_id
    assert task.assigned_at is not None
    
    db.close()


def test_no_agent_available_for_capability():
    """Test behavior when no agent has required capability"""
    db = TestingSessionLocal()
    
    best_agent = find_best_agent_for_task(db, "nonexistent_capability:v1")
    
    assert best_agent is None
    
    db.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
