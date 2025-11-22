"""Test task lifecycle management endpoints"""
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


def create_agent_and_task():
    """Helper to create agent and task for testing"""
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
    
    # Publish capability
    cap_payload = {
        "name": "test_capability:v1",
        "description": "Test capability",
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
        "capability_required": "test_capability:v1",
        "input_data": {"test": "data"},
        "priority": 5
    }
    task_resp = client.post("/aitp/tasks", json=task_payload)
    task_id = task_resp.json()["task_id"]
    
    return agent_id, task_id


def test_get_task_by_id():
    """Test retrieving a task by ID"""
    agent_id, task_id = create_agent_and_task()
    
    response = client.get(f"/aitp/tasks/{task_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["client_id"] == agent_id
    assert data["status"] == "PENDING"


def test_get_nonexistent_task():
    """Test retrieving a task that doesn't exist"""
    response = client.get("/aitp/tasks/nonexistent_task_id")
    
    assert response.status_code == 404


def test_update_task_state_valid_transition():
    """Test valid state transition"""
    agent_id, task_id = create_agent_and_task()
    
    # First, manually assign the task to the agent
    from ains.routing import assign_task_to_agent
    
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id, agent_id)
    db.close()
    
    # Now the agent can update status: ASSIGNED -> ACTIVE
    update_payload = {
        "status": "ACTIVE"
    }
    response = client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", json=update_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    
    # Verify task was updated
    task_resp = client.get(f"/aitp/tasks/{task_id}")
    assert task_resp.json()["status"] == "ACTIVE"


def test_update_task_state_invalid_transition():
    """Test invalid state transition"""
    agent_id, task_id = create_agent_and_task()
    
    # Assign task first
    from ains.routing import assign_task_to_agent
    
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id, agent_id)
    db.close()
    
    # Try to go ASSIGNED -> COMPLETED (invalid, must be ACTIVE first)
    update_payload = {
        "status": "COMPLETED"
    }
    response = client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", json=update_payload)
    
    assert response.status_code == 400
    assert "Can only complete ACTIVE tasks" in response.json()["detail"]


def test_complete_task_with_result():
    """Test completing a task with result data"""
    agent_id, task_id = create_agent_and_task()
    
    # Assign task first
    from ains.routing import assign_task_to_agent
    
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id, agent_id)
    db.close()
    
    # Activate the task
    client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", 
               json={"status": "ACTIVE"})
    
    # Complete with result
    update_payload = {
        "status": "COMPLETED",
        "result_data": {"output": "success", "value": 42}
    }
    response = client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", json=update_payload)
    
    assert response.status_code == 200
    
    # Verify result was saved
    task_resp = client.get(f"/aitp/tasks/{task_id}")
    task_data = task_resp.json()
    assert task_data["status"] == "COMPLETED"
    assert task_data["result_data"]["output"] == "success"
    assert task_data["completed_at"] is not None


def test_fail_task_with_error():
    """Test failing a task with error message"""
    agent_id, task_id = create_agent_and_task()
    
    # Assign task first
    from ains.routing import assign_task_to_agent
    
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id, agent_id)
    db.close()
    
    # Activate the task
    client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}",
               json={"status": "ACTIVE"})
    
    # Fail with error
    update_payload = {
        "status": "FAILED",
        "error_message": "Task execution failed due to timeout"
    }
    response = client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", json=update_payload)
    
    assert response.status_code == 200
    
    # Verify error was saved - task might be retried, so check for PENDING or FAILED
    task_resp = client.get(f"/aitp/tasks/{task_id}")
    task_data = task_resp.json()
    assert task_data["status"] in ["PENDING", "FAILED"]
    if task_data["status"] == "FAILED":
        assert "timeout" in task_data["error_message"]


def test_list_tasks():
    """Test listing all tasks"""
    # Create multiple tasks
    create_agent_and_task()
    create_agent_and_task()
    
    response = client.get("/aitp/tasks")
    
    assert response.status_code == 200
    data = response.json()
    # API returns paginated format: {tasks: [], total: N, limit: N, offset: N}
    assert "tasks" in data
    assert len(data["tasks"]) >= 2
    assert all("task_id" in task for task in data["tasks"])


def test_list_tasks_with_status_filter():
    """Test listing tasks filtered by status"""
    agent_id, task_id = create_agent_and_task()
    
    # Create another task and assign + activate it
    agent_id2, task_id2 = create_agent_and_task()
    
    from ains.routing import assign_task_to_agent
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id2, agent_id2)
    db.close()
    
    client.put(f"/aitp/tasks/{task_id2}/status?agent_id={agent_id2}",
               json={"status": "ACTIVE"})
    
    # Filter by PENDING
    response = client.get("/aitp/tasks?status=PENDING")
    
    assert response.status_code == 200
    data = response.json()
    assert all(task["status"] == "PENDING" for task in data["tasks"])


def test_list_tasks_with_pagination():
    """Test task list pagination"""
    # Create multiple tasks
    for _ in range(5):
        create_agent_and_task()
    
    # Get first page
    response = client.get("/aitp/tasks?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    
    # Get second page
    response = client.get("/aitp/tasks?limit=2&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)

def test_retrieve_completed_task_results():
    """Test retrieving results from a completed task"""
    agent_id, task_id = create_agent_and_task()
    
    # Assign and complete task
    from ains.routing import assign_task_to_agent
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id, agent_id)
    db.close()
    
    client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", 
               json={"status": "ACTIVE"})
    
    result_payload = {
        "status": "COMPLETED",
        "result_data": {"summary": "Task completed successfully", "items_processed": 42}
    }
    client.put(f"/aitp/tasks/{task_id}/status?agent_id={agent_id}", json=result_payload)
    
    # Retrieve task and verify results
    response = client.get(f"/aitp/tasks/{task_id}")
    assert response.status_code == 200
    
    task_data = response.json()
    assert task_data["status"] == "COMPLETED"
    assert task_data["result_data"]["summary"] == "Task completed successfully"
    assert task_data["result_data"]["items_processed"] == 42


def test_list_tasks_by_assigned_agent():
    """Test filtering tasks by assigned agent"""
    agent_id, task_id = create_agent_and_task()
    
    # Assign task
    from ains.routing import assign_task_to_agent
    db = TestingSessionLocal()
    assign_task_to_agent(db, task_id, agent_id)
    db.close()
    
    # Create another unassigned task
    create_agent_and_task()
    
    # Filter by assigned agent
    response = client.get(f"/aitp/tasks?assigned_agent_id={agent_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) >= 1
    assert all(task["assigned_agent_id"] == agent_id for task in data["tasks"] if task["assigned_agent_id"])


def test_list_tasks_by_client():
    """Test filtering tasks by client/requester"""
    agent_id, task_id = create_agent_and_task()
    
    # Create another task from different client
    create_agent_and_task()
    
    # Filter by client
    response = client.get(f"/aitp/tasks?client_id={agent_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) >= 1
    assert all(task["client_id"] == agent_id for task in data["tasks"])
