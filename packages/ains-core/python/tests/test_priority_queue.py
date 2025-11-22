"""Test priority queue and task prioritization"""
import os
import tempfile
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, Task, Agent, Capability
from ains.queue import PriorityQueue, adjust_priority_by_age

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


def test_priority_based_ordering():
    """Test that high priority tasks are selected first"""
    db = TestingSessionLocal()
    
    # Create agent with only valid fields
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32)
    )
    db.add(agent)
    
    # Create capability
    cap = Capability(
        capability_id=f"cap_{secrets.token_hex(4)}",
        agent_id=agent.agent_id,
        name="test:v1",
        description="Test",
        input_schema={},
        output_schema={},
        pricing_model="per_request",
        price=0.01
    )
    db.add(cap)
    db.commit()
    
    # Create tasks with different priorities
    tasks = []
    for priority in [3, 8, 5, 10, 1]:
        task = Task(
            task_id=f"task_{secrets.token_hex(4)}",
            client_id=agent.agent_id,
            task_type="test",
            capability_required="test:v1",
            input_data={"test": "data"},
            priority=priority,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(task)
        tasks.append(task)
    
    db.commit()
    
    # Get next task (should prioritize high priority with some fairness)
    queue = PriorityQueue(db)
    next_task = queue.get_next_task_for_agent(agent.agent_id, "test:v1")
    
    # Should get high priority task most of the time
    assert next_task is not None
    assert next_task.priority >= 5  # At least medium priority
    
    db.close()


def test_queue_stats_endpoint():
    """Test queue statistics endpoint"""
    # Clean up any existing pending tasks first
    db = TestingSessionLocal()
    db.query(Task).filter(Task.status == 'PENDING').delete()
    db.commit()
    db.close()
    
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
    
    # Create tasks with various priorities
    for priority in [2, 5, 8, 10]:
        task_payload = {
            "client_id": agent_id,
            "task_type": "test",
            "capability_required": "test:v1",
            "input_data": {"test": "data"},
            "priority": priority
        }
        client.post("/aitp/tasks", json=task_payload)
    
    # Get queue stats
    response = client.get("/aitp/queue/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "queue" in data
    assert "workload" in data
    assert data["queue"]["total_pending"] == 4
    assert data["queue"]["high_priority"] >= 1  # At least one high priority task


def test_adjust_task_priority():
    """Test adjusting task priority"""
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
    
    # Adjust priority
    response = client.put(
        f"/aitp/tasks/{task_id}/priority?new_priority=9&client_id={agent_id}"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["old_priority"] == 5
    assert data["new_priority"] == 9


def test_priority_age_adjustment():
    """Test automatic priority boost for old tasks"""
    db = TestingSessionLocal()
    
    # Create agent with only valid fields
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32)
    )
    db.add(agent)
    db.commit()
    
    # Create old low-priority task
    old_task = Task(
        task_id=f"task_{secrets.token_hex(4)}",
        client_id=agent.agent_id,
        task_type="test",
        capability_required="test:v1",
        input_data={"test": "data"},
        priority=3,
        status="PENDING",
        created_at=datetime.now(timezone.utc) - timedelta(hours=25),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(old_task)
    db.commit()
    
    # Adjust priorities based on age
    updated = adjust_priority_by_age(db, max_age_hours=24)
    
    assert updated == 1
    
    # Verify priority was boosted
    db.refresh(old_task)
    assert old_task.priority == 5  # 3 + 2 = 5
    
    db.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
