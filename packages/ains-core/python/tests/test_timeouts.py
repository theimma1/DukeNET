"""Test task timeout and cancellation"""
import os
import tempfile
import pytest
import secrets
import time
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, Task, Agent, Capability
from ains.timeouts import check_timeouts, cancel_task, set_task_timeout

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


def test_timeout_detection():
    """Test that timed-out tasks are detected"""
    db = TestingSessionLocal()
    
    # Create agent
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32)
    )
    db.add(agent)
    db.commit()
    
    # Create task that has timed out
    task = Task(
        task_id=f"task_{secrets.token_hex(4)}",
        client_id=agent.agent_id,
        task_type="test",
        capability_required="test:v1",
        input_data={"test": "data"},
        status="ACTIVE",
        timeout_seconds=5,
        started_at=datetime.now(timezone.utc) - timedelta(seconds=10),  # Started 10 seconds ago
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(task)
    db.commit()
    
    # Check timeouts
    timed_out = check_timeouts(db)
    
    assert timed_out == 1
    
    # Verify task is now failed
    db.refresh(task)
    assert task.status == "FAILED"
    assert "timed out" in task.error_message.lower()
    
    db.close()


def test_cancel_task_via_api():
    """Test task cancellation via API"""
    # Create agent
    agent_payload = {
        "agent_id": f"agent_{secrets.token_hex(4)}",
        "display_name": "Test Agent",
        "endpoint": "http://localhost:8000",
        "public_key": secrets.token_hex(32),
        "signature": secrets.token_hex(64),
        "tags": ["test"]
    }
    agent_resp = client.post("/ains/agents", json=agent_payload)
    agent_id = agent_resp.json()["agent_id"]
    
    # Create capability
    cap_payload = {
        "name": "test:v1",
        "description": "Test",
        "input_schema": {},
        "output_schema": {},
        "pricing_model": "per_request",
        "price": 0.01,
        "latency_p99_ms": 100,
        "availability_percent": 99.0,
        "signature": secrets.token_hex(64)
    }
    client.post(f"/ains/agents/{agent_id}/capabilities", json=cap_payload)
    
    # Create task
    task_payload = {
        "client_id": agent_id,
        "task_type": "test",
        "capability_required": "test:v1",
        "input_data": {"test": "data"},
        "priority": 5
    }
    task_resp = client.post("/aitp/tasks", json=task_payload)
    task_id = task_resp.json()["task_id"]
    
    # Cancel task
    response = client.delete(
        f"/aitp/tasks/{task_id}?client_id={agent_id}&reason=Test+cancellation"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert "cancelled_at" in data


def test_cannot_cancel_completed_task():
    """Test that completed tasks cannot be cancelled"""
    db = TestingSessionLocal()
    
    # Create agent
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32)
    )
    db.add(agent)
    db.commit()
    
    # Create completed task
    task = Task(
        task_id=f"task_{secrets.token_hex(4)}",
        client_id=agent.agent_id,
        task_type="test",
        capability_required="test:v1",
        input_data={"test": "data"},
        status="COMPLETED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    db.add(task)
    db.commit()
    
    # Attempt to cancel
    success = cancel_task(db, task.task_id, agent.agent_id, "Test")
    
    assert success is False
    
    # Verify task is still completed
    db.refresh(task)
    assert task.status == "COMPLETED"
    
    db.close()


def test_set_task_timeout():
    """Test setting task timeout"""
    # Create agent
    agent_payload = {
        "agent_id": f"agent_{secrets.token_hex(4)}",
        "display_name": "Test Agent",
        "endpoint": "http://localhost:8000",
        "public_key": secrets.token_hex(32),
        "signature": secrets.token_hex(64),
        "tags": ["test"]
    }
    agent_resp = client.post("/ains/agents", json=agent_payload)
    agent_id = agent_resp.json()["agent_id"]
    
    # Create capability
    cap_payload = {
        "name": "test:v1",
        "description": "Test",
        "input_schema": {},
        "output_schema": {},
        "pricing_model": "per_request",
        "price": 0.01,
        "latency_p99_ms": 100,
        "availability_percent": 99.0,
        "signature": secrets.token_hex(64)
    }
    client.post(f"/ains/agents/{agent_id}/capabilities", json=cap_payload)
    
    # Create task
    task_payload = {
        "client_id": agent_id,
        "task_type": "test",
        "capability_required": "test:v1",
        "input_data": {"test": "data"},
        "priority": 5
    }
    task_resp = client.post("/aitp/tasks", json=task_payload)
    task_id = task_resp.json()["task_id"]
    
    # Set timeout
    response = client.put(
        f"/aitp/tasks/{task_id}/timeout?timeout_seconds=600&client_id={agent_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["timeout_seconds"] == 600


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
