"""Test trust and reputation system"""
import os
import tempfile
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, Agent, Task
from ains.trust_system import (
    calculate_trust_score,
    adjust_trust_score,
    update_agent_metrics_on_task_completion,
    get_agent_trust_metrics,
    get_leaderboard
)

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


def test_initial_trust_score():
    """Test that new agents start with default trust score"""
    # Create agent via API
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
    
    # Get trust metrics
    response = client.get(f"/ains/agents/{agent_id}/trust")
    
    assert response.status_code == 200
    data = response.json()
    assert data["trust_score"] == 0.5  # Default trust
    assert data["trust_level"] == "medium"


def test_trust_adjustment():
    """Test manual trust score adjustment"""
    db = TestingSessionLocal()
    
    # Create agent
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32),
        trust_score=0.5
    )
    db.add(agent)
    db.commit()
    
    # Adjust trust
    record = adjust_trust_score(
        db, agent.agent_id, "manual_adjustment",
        trust_delta=0.1, reason="Test adjustment"
    )
    
    assert record.trust_delta == 0.1
    assert record.trust_score_before == 0.5
    assert record.trust_score_after == 0.6
    
    # Verify agent updated
    db.refresh(agent)
    assert agent.trust_score == 0.6
    
    db.close()


def test_task_completion_updates_trust():
    """Test that successful task completion increases trust"""
    db = TestingSessionLocal()
    
    # Create agent
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32),
        trust_score=0.5,
        total_tasks_completed=0,
        total_tasks_failed=0
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
        assigned_agent_id=agent.agent_id,
        started_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        completed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(task)
    db.commit()
    
    # Update metrics
    initial_trust = agent.trust_score
    update_agent_metrics_on_task_completion(db, agent.agent_id, task, success=True)
    
    # Verify trust increased
    db.refresh(agent)
    assert agent.trust_score > initial_trust
    assert agent.total_tasks_completed == 1
    assert agent.total_tasks_failed == 0
    
    db.close()


def test_task_failure_decreases_trust():
    """Test that task failure decreases trust"""
    db = TestingSessionLocal()
    
    # Create agent
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32),
        trust_score=0.7,
        total_tasks_completed=0,
        total_tasks_failed=0
    )
    db.add(agent)
    db.commit()
    
    # Create failed task
    task = Task(
        task_id=f"task_{secrets.token_hex(4)}",
        client_id=agent.agent_id,
        task_type="test",
        capability_required="test:v1",
        input_data={"test": "data"},
        status="FAILED",
        assigned_agent_id=agent.agent_id,
        error_message="Task failed",
        started_at=datetime.now(timezone.utc) - timedelta(seconds=60),
        completed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(task)
    db.commit()
    
    # Update metrics
    initial_trust = agent.trust_score
    update_agent_metrics_on_task_completion(db, agent.agent_id, task, success=False)
    
    # Verify trust decreased
    db.refresh(agent)
    assert agent.trust_score < initial_trust
    assert agent.total_tasks_completed == 0
    assert agent.total_tasks_failed == 1
    
    db.close()


def test_get_trust_history():
    """Test retrieving trust history"""
    db = TestingSessionLocal()
    
    # Create agent
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32),
        trust_score=0.5
    )
    db.add(agent)
    db.commit()
    
    # Store agent_id before closing session
    agent_id = agent.agent_id
    
    # Make several adjustments
    for i in range(3):
        adjust_trust_score(
            db, agent_id, "test_event",
            trust_delta=0.01, reason=f"Test {i}"
        )
    
    db.close()
    
    # Get history via API
    response = client.get(f"/ains/agents/{agent_id}/trust/history")  # Use stored agent_id
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3



def test_leaderboard():
    """Test getting top agents leaderboard"""
    db = TestingSessionLocal()
    
    # Create multiple agents with different trust scores
    for i in range(5):
        agent = Agent(
            agent_id=f"agent_{secrets.token_hex(4)}",
            display_name=f"Agent {i}",
            public_key=secrets.token_hex(32),
            trust_score=0.5 + (i * 0.1),
            total_tasks_completed=20 + i,
            total_tasks_failed=0
        )
        db.add(agent)
    
    db.commit()
    db.close()
    
    # Get leaderboard
    response = client.get("/ains/agents/leaderboard?limit=3&min_tasks=10")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["leaderboard"]) >= 3
    
    # Verify sorted by trust score (descending)
    scores = [agent["trust_score"] for agent in data["leaderboard"]]
    assert scores == sorted(scores, reverse=True)


def test_trust_metrics_endpoint():
    """Test getting comprehensive trust metrics"""
    db = TestingSessionLocal()
    
    # Create agent with some history
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32),
        trust_score=0.75,
        total_tasks_completed=50,
        total_tasks_failed=5,
        avg_completion_time_seconds=45.5,
        last_task_completed_at=datetime.now(timezone.utc)
    )
    db.add(agent)
    db.commit()
    
    # Store agent_id BEFORE closing
    agent_id = agent.agent_id
    
    db.close()
    
    # Get metrics
    response = client.get(f"/ains/agents/{agent_id}/trust")  # Use stored variable
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["trust_score"] == 0.75
    assert data["total_tasks_completed"] == 50
    assert data["total_tasks_failed"] == 5



@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
