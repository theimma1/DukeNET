"""Test batch task operations"""
import os
import tempfile
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db
from ains.batch import submit_batch_tasks, get_batch_status, cancel_batch_tasks

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


def test_submit_batch_tasks():
    """Test submitting multiple tasks in a batch"""
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
    
    # Submit batch of tasks
    batch_payload = {
        "client_id": agent_id,
        "tasks": [
            {
                "task_type": "test",
                "capability_required": "test:v1",
                "input_data": {"index": i},
                "priority": 5
            }
            for i in range(10)
        ]
    }
    
    response = client.post("/aitp/tasks/batch", json=batch_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["created"] == 10
    assert len(data["task_ids"]) == 10


def test_get_batch_status():
    """Test getting status of multiple tasks"""
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
    
    # Submit batch
    batch_payload = {
        "client_id": agent_id,
        "tasks": [
            {
                "task_type": "test",
                "capability_required": "test:v1",
                "input_data": {"index": i},
                "priority": 5
            }
            for i in range(5)
        ]
    }
    
    batch_resp = client.post("/aitp/tasks/batch", json=batch_payload)
    task_ids = batch_resp.json()["task_ids"]
    
    # Get batch status
    task_ids_str = ",".join(task_ids)
    response = client.get(f"/aitp/tasks/batch/status?task_ids={task_ids_str}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert "PENDING" in data["status_counts"]


def test_cancel_batch_tasks():
    """Test cancelling multiple tasks"""
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
    
    # Submit batch
    batch_payload = {
        "client_id": agent_id,
        "tasks": [
            {
                "task_type": "test",
                "capability_required": "test:v1",
                "input_data": {"index": i},
                "priority": 5
            }
            for i in range(3)
        ]
    }
    
    batch_resp = client.post("/aitp/tasks/batch", json=batch_payload)
    task_ids = batch_resp.json()["task_ids"]
    
    # Cancel batch
    task_ids_str = ",".join(task_ids)
    response = client.post(
        f"/aitp/tasks/batch/cancel?task_ids={task_ids_str}&client_id={agent_id}&reason=Test"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["cancelled"] == 3


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
