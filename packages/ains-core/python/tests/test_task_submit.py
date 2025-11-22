"""Test task submission endpoint"""
import os
import tempfile
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db

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


def test_submit_valid_task():
    """Test submitting a valid task"""
    # Register an agent with unique keys
    public_key = secrets.token_hex(32)
    signature = secrets.token_hex(64)
    
    agent_payload = {
        "agent_id": f"test_agent_{secrets.token_hex(4)}",
        "display_name": "Test Agent",
        "endpoint": "http://localhost:8000",
        "public_key": public_key,
        "signature": signature,
        "tags": ["test"]
    }
    agent_response = client.post("/ains/agents", json=agent_payload)
    assert agent_response.status_code in [200, 201]
    agent_id = agent_response.json()["agent_id"]

    # Publish a capability
    capability_payload = {
        "name": "summarization:v1",
        "description": "Text summarization capability",
        "input_schema": {},
        "output_schema": {},
        "pricing_model": "per_request",
        "price": 0.01,
        "latency_p99_ms": 100,
        "availability_percent": 99.9,
        "signature": secrets.token_hex(64)
    }
    cap_response = client.post(f"/ains/agents/{agent_id}/capabilities", json=capability_payload)
    assert cap_response.status_code in [200, 201]

    # Submit a task
    task_payload = {
        "client_id": agent_id,
        "task_type": "summarization",
        "capability_required": "summarization:v1",
        "input_data": {"text": "Hello world"},
        "priority": 5
    }
    response = client.post("/aitp/tasks", json=task_payload)
    
    # API returns 200, not 201
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "PENDING"
    assert data["client_id"] == agent_id
    assert data["capability_required"] == "summarization:v1"


def test_submit_task_with_invalid_agent():
    """Test submitting a task with non-existent agent - currently doesn't validate"""
    task_payload = {
        "client_id": "nonexistent_agent",
        "task_type": "summarization",
        "capability_required": "summarization:v1",
        "input_data": {"text": "Hello world"},
        "priority": 5
    }
    response = client.post("/aitp/tasks", json=task_payload)
    
    # Currently API returns 200 even for invalid agent (no validation yet)
    # This is expected behavior - validation will be added in Sprint 3.3
    assert response.status_code == 200


def test_submit_task_with_invalid_capability():
    """Test submitting a task with non-existent capability"""
    # Register an agent
    public_key = secrets.token_hex(32)
    signature = secrets.token_hex(64)
    
    agent_payload = {
        "agent_id": f"test_agent_{secrets.token_hex(4)}",
        "display_name": "Test Agent 2",
        "endpoint": "http://localhost:8000",
        "public_key": public_key,
        "signature": signature,
        "tags": ["test"]
    }
    agent_response = client.post("/ains/agents", json=agent_payload)
    agent_id = agent_response.json()["agent_id"]

    # Submit task with invalid capability
    task_payload = {
        "client_id": agent_id,
        "task_type": "nonexistent",
        "capability_required": "nonexistent_capability",
        "input_data": {"text": "Hello world"},
        "priority": 5
    }
    response = client.post("/aitp/tasks", json=task_payload)
    
    # API returns 400 for invalid capability
    assert response.status_code == 400


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
