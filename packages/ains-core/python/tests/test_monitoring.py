"""Test monitoring and alerting endpoints"""
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


def test_aitp_health_check():
    """Test AITP health check endpoint"""
    response = client.get("/health/aitp")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert data["service"] == "AITP"
    assert "timestamp" in data
    assert "metrics" in data


def test_aitp_health_metrics():
    """Test that health check returns correct metrics"""
    # Create some tasks
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
    
    # Publish capability
    cap_payload = {
        "name": "test_cap:v1",
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
    
    # Create 3 tasks
    for _ in range(3):
        task_payload = {
            "client_id": agent_id,
            "task_type": "test",
            "capability_required": "test_cap:v1",
            "input_data": {"test": "data"},
            "priority": 5
        }
        client.post("/aitp/tasks", json=task_payload)
    
    # Check health metrics
    response = client.get("/health/aitp")
    data = response.json()
    
    metrics = data["metrics"]
    assert "queue_depth" in metrics
    assert "active_tasks" in metrics
    assert "completed_tasks" in metrics
    assert "failed_tasks" in metrics
    assert "failure_rate_percent" in metrics
    
    # Should have at least 3 pending tasks
    assert metrics["queue_depth"] >= 3


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
