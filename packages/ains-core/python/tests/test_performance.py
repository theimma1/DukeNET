"""Test performance monitoring and optimization"""
import os
import tempfile
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, Task, Agent
from ains.performance import get_system_stats, get_database_size, cleanup_old_data

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


def test_get_system_stats():
    """Test getting system statistics"""
    response = client.get("/ains/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "agents" in data
    assert "capabilities" in data
    assert "total" in data["tasks"]


def test_get_database_stats():
    """Test getting database statistics"""
    response = client.get("/ains/stats/database")
    
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "agents" in data


def test_cleanup_old_data():
    """Test cleaning up old data"""
    db = TestingSessionLocal()
    
    # Create old completed task
    agent = Agent(
        agent_id=f"agent_{secrets.token_hex(4)}",
        display_name="Test Agent",
        public_key=secrets.token_hex(32)
    )
    db.add(agent)
    db.commit()
    
    old_task = Task(
        task_id=f"task_{secrets.token_hex(4)}",
        client_id=agent.agent_id,
        task_type="test",
        capability_required="test:v1",
        input_data={"test": "data"},
        status="COMPLETED",
        created_at=datetime.now(timezone.utc) - timedelta(days=40),
        updated_at=datetime.now(timezone.utc) - timedelta(days=40),
        completed_at=datetime.now(timezone.utc) - timedelta(days=40)
    )
    db.add(old_task)
    db.commit()
    
    # Cleanup data older than 30 days
    result = cleanup_old_data(db, days=30)
    
    assert result["deleted_tasks"] >= 1
    
    db.close()


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
