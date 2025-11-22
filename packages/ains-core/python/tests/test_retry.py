"""Test task retry logic"""
import os
import tempfile
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, Task
from ains.retry import calculate_next_retry, should_retry, schedule_retry

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


def test_exponential_backoff_calculation():
    """Test exponential backoff retry timing"""
    # First retry: 1 second
    next_retry = calculate_next_retry(0, "exponential")
    assert (next_retry - datetime.now(timezone.utc)).total_seconds() <= 2
    
    # Second retry: 2 seconds
    next_retry = calculate_next_retry(1, "exponential")
    assert 1 <= (next_retry - datetime.now(timezone.utc)).total_seconds() <= 3
    
    # Third retry: 4 seconds
    next_retry = calculate_next_retry(2, "exponential")
    assert 3 <= (next_retry - datetime.now(timezone.utc)).total_seconds() <= 5


def test_linear_backoff_calculation():
    """Test linear backoff retry timing"""
    # First retry: 5 seconds
    next_retry = calculate_next_retry(0, "linear")
    assert 4 <= (next_retry - datetime.now(timezone.utc)).total_seconds() <= 6
    
    # Second retry: 10 seconds
    next_retry = calculate_next_retry(1, "linear")
    assert 9 <= (next_retry - datetime.now(timezone.utc)).total_seconds() <= 11


def test_should_retry_retryable_errors():
    """Test that retryable errors return True"""
    db = TestingSessionLocal()
    
    task = Task(
        task_id="task_test",
        client_id="agent_test",
        task_type="test",
        capability_required="test:v1",
        status="FAILED",
        max_retries=3,
        retry_count=1
    )
    
    # Retryable errors
    assert should_retry(task, "Connection timeout")
    assert should_retry(task, "Service temporarily unavailable")
    assert should_retry(task, "Internal server error")
    
    db.close()


def test_should_not_retry_permanent_errors():
    """Test that permanent errors return False"""
    db = TestingSessionLocal()
    
    task = Task(
        task_id="task_test",
        client_id="agent_test",
        task_type="test",
        capability_required="test:v1",
        status="FAILED",
        max_retries=3,
        retry_count=1
    )
    
    # Non-retryable errors
    assert not should_retry(task, "Invalid input provided")
    assert not should_retry(task, "Authentication failed")
    assert not should_retry(task, "Permission denied")
    assert not should_retry(task, "Not found")
    
    db.close()


def test_should_not_retry_max_retries_exceeded():
    """Test that tasks don't retry after max attempts"""
    db = TestingSessionLocal()
    
    task = Task(
        task_id="task_test",
        client_id="agent_test",
        task_type="test",
        capability_required="test:v1",
        status="FAILED",
        max_retries=3,
        retry_count=3  # Already at max
    )
    
    assert not should_retry(task, "Connection timeout")
    
    db.close()


def test_manual_retry_endpoint():
    """Test manual retry via API"""
    # Create agent and task
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
    
    # Create failed task
    task_payload = {
        "client_id": agent_id,
        "task_type": "test",
        "capability_required": "test:v1",
        "input_data": {"test": "data"},
        "priority": 5
    }
    task_resp = client.post("/aitp/tasks", json=task_payload)
    task_id = task_resp.json()["task_id"]
    
    # Manually fail the task
    db = TestingSessionLocal()
    task = db.query(Task).filter(Task.task_id == task_id).first()
    task.status = "FAILED"
    task.error_message = "Connection timeout"
    db.commit()
    db.close()
    
    # Retry the task
    response = client.post(f"/aitp/tasks/{task_id}/retry")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING"
    assert data["retry_count"] == 1


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
