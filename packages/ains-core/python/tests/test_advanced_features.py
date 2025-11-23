"""Tests for Sprint 7: Advanced Features"""
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, Agent, Task, TaskChain, ScheduledTask, TaskTemplate
from ains.advanced_features import (
    check_dependencies, create_task_chain, route_task,
    calculate_next_run, create_task_template, create_task_from_template
)

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_advanced.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_database():
    """Clear database before each test"""
    db = TestingSessionLocal()
    db.query(Task).delete()
    db.query(Agent).delete()
    db.query(TaskChain).delete()
    db.query(ScheduledTask).delete()
    db.query(TaskTemplate).delete()
    db.commit()
    db.close()
    yield

def create_test_agent(db, agent_id: str = None, trust_score: float = 0.7):
    """Helper to create test agent"""
    if not agent_id:
        agent_id = f"agent_{secrets.token_hex(4)}"
    
    agent = Agent(
        agent_id=agent_id,
        public_key=secrets.token_hex(32),
        display_name=f"Test Agent {agent_id}",
        endpoint="http://localhost:8000",
        signature=secrets.token_hex(64),
        tags=["data:v1", "api:v1"],
        trust_score=trust_score
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent

# ============================================================================
# TASK DEPENDENCIES TESTS
# ============================================================================

def test_task_with_dependencies():
    """Test creating a task with dependencies"""
    db = TestingSessionLocal()
    
    # Create dependency tasks
    task1 = Task(
        task_id="task_001",
        client_id="client_1",
        task_type="step1",
        capability_required="data:v1",
        status="COMPLETED",
        input_data={}  # FIXED
    )
    task2 = Task(
        task_id="task_002",
        client_id="client_1",
        task_type="step2",
        capability_required="data:v1",
        status="COMPLETED",
        input_data={}  # FIXED
    )
    db.add(task1)
    db.add(task2)
    db.commit()
    
    # Create task with dependencies
    response = client.post("/ains/tasks", json={
        "client_id": "client_1",
        "task_type": "step3",
        "capability_required": "data:v1",
        "input_data": {"test": "data"},
        "depends_on": ["task_001", "task_002"]
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["depends_on"] == ["task_001", "task_002"]
    
    db.close()

def test_check_dependencies():
    """Test dependency checking"""
    db = TestingSessionLocal()
    
    # Create tasks
    task1 = Task(
        task_id="task_001",
        client_id="client_1",
        task_type="step1",
        capability_required="data:v1",
        status="COMPLETED",
        input_data={}  # FIXED
    )
    task2 = Task(
        task_id="task_002",
        client_id="client_1",
        task_type="step2",
        capability_required="data:v1",
        status="RUNNING",
        input_data={}  # FIXED
    )
    task3 = Task(
        task_id="task_003",
        client_id="client_1",
        task_type="step3",
        capability_required="data:v1",
        status="PENDING",
        depends_on=["task_001", "task_002"],
        input_data={}  # FIXED
    )
    db.add_all([task1, task2, task3])
    db.commit()
    
    # Dependencies not satisfied (task2 still running)
    assert check_dependencies(db, "task_003") is False
    
    # Complete task2
    task2.status = "COMPLETED"
    db.commit()
    
    # Dependencies now satisfied
    assert check_dependencies(db, "task_003") is True
    
    db.close()

def test_get_dependency_status():
    """Test getting dependency status"""
    db = TestingSessionLocal()
    
    task1 = Task(
        task_id="task_001",
        client_id="client_1",
        task_type="step1",
        capability_required="data:v1",
        status="COMPLETED",
        input_data={}  # FIXED
    )
    task2 = Task(
        task_id="task_002",
        client_id="client_1",
        task_type="step2",
        capability_required="data:v1",
        status="PENDING",
        depends_on=["task_001"],
        input_data={}  # FIXED
    )
    db.add_all([task1, task2])
    db.commit()
    
    response = client.get("/ains/tasks/task_002/dependencies")
    assert response.status_code == 200
    data = response.json()
    
    assert data["task_id"] == "task_002"
    assert data["depends_on"] == ["task_001"]
    assert data["dependencies_status"]["task_001"] == "COMPLETED"
    assert data["ready_to_run"] is True
    
    db.close()

# ============================================================================
# TASK CHAINS TESTS
# ============================================================================

def test_create_task_chain():
    """Test creating a task chain"""
    db = TestingSessionLocal()
    create_test_agent(db)
    
    response = client.post("/ains/task-chains", json={
        "name": "Test Pipeline",
        "client_id": "client_1",
        "steps": [
            {
                "name": "step1",
                "task_type": "fetch",
                "capability_required": "data:v1",
                "input_data": {"source": "api"}
            },
            {
                "name": "step2",
                "task_type": "process",
                "capability_required": "data:v1",
                "input_data": {"operation": "transform"},
                "use_previous_output": True
            }
        ]
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "chain_id" in data
    assert data["name"] == "Test Pipeline"
    assert data["total_steps"] == 2
    assert data["status"] in ["PENDING", "RUNNING"]
    
    db.close()

def test_get_task_chain():
    """Test getting task chain details"""
    db = TestingSessionLocal()
    create_test_agent(db)
    
    # Create chain
    create_response = client.post("/ains/task-chains", json={
        "name": "Test Pipeline",
        "client_id": "client_1",
        "steps": [
            {
                "name": "step1",
                "task_type": "fetch",
                "capability_required": "data:v1",
                "input_data": {"source": "api"}
            }
        ]
    })
    chain_id = create_response.json()["chain_id"]
    
    # Get chain
    response = client.get(f"/ains/task-chains/{chain_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["chain_id"] == chain_id
    assert data["name"] == "Test Pipeline"
    assert len(data["steps"]) == 1
    
    db.close()

def test_list_task_chains():
    """Test listing task chains"""
    db = TestingSessionLocal()
    create_test_agent(db)
    
    # Create multiple chains
    for i in range(3):
        client.post("/ains/task-chains", json={
            "name": f"Pipeline {i}",
            "client_id": "client_1",
            "steps": [
                {
                    "name": "step1",
                    "task_type": "test",
                    "capability_required": "data:v1",
                    "input_data": {}
                }
            ]
        })
    
    response = client.get("/ains/task-chains?client_id=client_1")
    assert response.status_code == 200
    chains = response.json()
    
    assert len(chains) == 3
    
    db.close()

def test_cancel_task_chain():
    """Test cancelling a task chain"""
    db = TestingSessionLocal()
    create_test_agent(db)
    
    # Create chain
    create_response = client.post("/ains/task-chains", json={
        "name": "Test Pipeline",
        "client_id": "client_1",
        "steps": [
            {
                "name": "step1",
                "task_type": "test",
                "capability_required": "data:v1",
                "input_data": {}
            }
        ]
    })
    chain_id = create_response.json()["chain_id"]
    
    # Cancel chain
    response = client.post(f"/ains/task-chains/{chain_id}/cancel")
    assert response.status_code == 200
    
    # Verify cancelled
    get_response = client.get(f"/ains/task-chains/{chain_id}")
    assert get_response.json()["status"] == "CANCELLED"
    
    db.close()

# ============================================================================
# ROUTING STRATEGIES TESTS
# ============================================================================

def test_list_routing_strategies():
    """Test listing available routing strategies"""
    response = client.get("/ains/routing/strategies")
    assert response.status_code == 200
    data = response.json()
    
    assert "strategies" in data
    assert len(data["strategies"]) == 4
    assert data["default"] == "round_robin"

def test_round_robin_routing():
    """Test round-robin routing strategy"""
    db = TestingSessionLocal()
    
    # Create multiple agents
    agent1 = create_test_agent(db, "agent_1")
    agent2 = create_test_agent(db, "agent_2")
    agent3 = create_test_agent(db, "agent_3")
    
    # Create tasks with round-robin routing
    selected_agents = []
    for i in range(6):
        task = Task(
            task_id=f"task_{i}",
            client_id="client_1",
            task_type="test",
            capability_required="data:v1",
            routing_strategy="round_robin",
            status="PENDING",
            input_data={}  # FIXED
        )
        agent_id = route_task(db, task)
        selected_agents.append(agent_id)
    
    # Should distribute evenly
    assert selected_agents.count("agent_1") == 2
    assert selected_agents.count("agent_2") == 2
    assert selected_agents.count("agent_3") == 2
    
    db.close()

def test_trust_weighted_routing():
    """Test trust-weighted routing strategy"""
    db = TestingSessionLocal()
    
    # Create agents with different trust scores
    agent1 = create_test_agent(db, "agent_1", trust_score=0.9)
    agent2 = create_test_agent(db, "agent_2", trust_score=0.5)
    agent3 = create_test_agent(db, "agent_3", trust_score=0.3)
    
    # Create tasks with trust-weighted routing
    selected_agents = []
    for i in range(10):
        task = Task(
            task_id=f"task_{i}",
            client_id="client_1",
            task_type="test",
            capability_required="data:v1",
            routing_strategy="trust_weighted",
            status="PENDING",
            input_data={}  # FIXED
        )
        agent_id = route_task(db, task)
        selected_agents.append(agent_id)
    
    # High trust agent should be selected more often
    assert selected_agents.count("agent_1") > selected_agents.count("agent_3")
    
    db.close()

def test_routing_test_endpoint():
    """Test the routing test endpoint"""
    db = TestingSessionLocal()
    create_test_agent(db, trust_score=0.8)
    
    response = client.post("/ains/routing/test", json={
        "capability_required": "data:v1",
        "routing_strategy": "trust_weighted"
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "selected_agent" in data
    assert data["strategy_used"] == "trust_weighted"
    
    db.close()

# ============================================================================
# SCHEDULED TASKS TESTS
# ============================================================================

def test_create_scheduled_task():
    """Test creating a scheduled task"""
    response = client.post("/ains/scheduled-tasks", json={
        "name": "Daily Sync",
        "client_id": "client_1",
        "cron_expression": "0 2 * * *",
        "timezone": "UTC",
        "task_type": "sync",
        "capability_required": "data:v1",
        "input_data": {"source": "api"},
        "priority": 7
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "schedule_id" in data
    assert data["name"] == "Daily Sync"
    assert data["cron_expression"] == "0 2 * * *"
    assert data["active"] is True

def test_list_scheduled_tasks():
    """Test listing scheduled tasks"""
    # Create multiple schedules
    for i in range(3):
        client.post("/ains/scheduled-tasks", json={
            "name": f"Schedule {i}",
            "client_id": "client_1",
            "cron_expression": "*/5 * * * *",
            "task_type": "test",
            "capability_required": "data:v1",
            "input_data": {}
        })
    
    response = client.get("/ains/scheduled-tasks?client_id=client_1")
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["schedules"]) == 3

def test_get_scheduled_task():
    """Test getting scheduled task details"""
    # Create schedule
    create_response = client.post("/ains/scheduled-tasks", json={
        "name": "Test Schedule",
        "client_id": "client_1",
        "cron_expression": "0 */2 * * *",
        "task_type": "test",
        "capability_required": "data:v1",
        "input_data": {"key": "value"}
    })
    schedule_id = create_response.json()["schedule_id"]
    
    # Get schedule
    response = client.get(f"/ains/scheduled-tasks/{schedule_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["schedule_id"] == schedule_id
    assert data["name"] == "Test Schedule"
    assert data["input_data"] == {"key": "value"}

def test_update_scheduled_task():
    """Test updating scheduled task"""
    # Create schedule
    create_response = client.post("/ains/scheduled-tasks", json={
        "name": "Test Schedule",
        "client_id": "client_1",
        "cron_expression": "0 2 * * *",
        "task_type": "test",
        "capability_required": "data:v1",
        "input_data": {}
    })
    schedule_id = create_response.json()["schedule_id"]
    
    # Update schedule
    response = client.patch(f"/ains/scheduled-tasks/{schedule_id}", json={
        "active": False,
        "priority": 8
    })
    
    assert response.status_code == 200
    
    # Verify update
    get_response = client.get(f"/ains/scheduled-tasks/{schedule_id}")
    assert get_response.json()["active"] is False

def test_delete_scheduled_task():
    """Test deleting scheduled task"""
    # Create schedule
    create_response = client.post("/ains/scheduled-tasks", json={
        "name": "Test Schedule",
        "client_id": "client_1",
        "cron_expression": "0 2 * * *",
        "task_type": "test",
        "capability_required": "data:v1",
        "input_data": {}
    })
    schedule_id = create_response.json()["schedule_id"]
    
    # Delete schedule
    response = client.delete(f"/ains/scheduled-tasks/{schedule_id}")
    assert response.status_code == 200
    
    # Verify deleted
    get_response = client.get(f"/ains/scheduled-tasks/{schedule_id}")
    assert get_response.status_code == 404

def test_trigger_scheduled_task_now():
    """Test manually triggering a scheduled task"""
    db = TestingSessionLocal()
    create_test_agent(db)
    
    # Create schedule
    create_response = client.post("/ains/scheduled-tasks", json={
        "name": "Test Schedule",
        "client_id": "client_1",
        "cron_expression": "0 2 * * *",
        "task_type": "test",
        "capability_required": "data:v1",
        "input_data": {}
    })
    schedule_id = create_response.json()["schedule_id"]
    
    # Trigger now
    response = client.post(f"/ains/scheduled-tasks/{schedule_id}/run-now")
    assert response.status_code == 200
    data = response.json()
    
    assert "task_id" in data
    assert data["schedule_id"] == schedule_id
    
    db.close()

def test_calculate_next_run():
    """Test cron expression calculation"""
    # Every 5 minutes
    next_run = calculate_next_run("*/5 * * * *")
    assert next_run > datetime.now(timezone.utc)
    
    # Every hour
    next_run = calculate_next_run("0 * * * *")
    assert next_run > datetime.now(timezone.utc)

# ============================================================================
# TASK TEMPLATES TESTS
# ============================================================================

def test_create_task_template():
    """Test creating a task template"""
    response = client.post("/ains/task-templates", json={
        "name": "Standard Analysis",
        "description": "Template for data analysis",
        "client_id": "client_1",
        "task_type": "analysis",
        "capability_required": "data:v1",
        "default_input_data": {
            "algorithm": "standard",
            "output_format": "json"
        },
        "default_priority": 6,
        "default_timeout": 600
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "template_id" in data
    assert data["name"] == "Standard Analysis"

def test_list_task_templates():
    """Test listing task templates"""
    # Create multiple templates
    for i in range(3):
        client.post("/ains/task-templates", json={
            "name": f"Template {i}",
            "client_id": "client_1",
            "task_type": "test",
            "capability_required": "data:v1",
            "default_input_data": {}
        })
    
    response = client.get("/ains/task-templates?client_id=client_1")
    assert response.status_code == 200
    templates = response.json()
    
    assert len(templates) == 3

def test_get_task_template():
    """Test getting template details"""
    # Create template
    create_response = client.post("/ains/task-templates", json={
        "name": "Test Template",
        "client_id": "client_1",
        "task_type": "test",
        "capability_required": "data:v1",
        "default_input_data": {"key": "value"}
    })
    template_id = create_response.json()["template_id"]
    
    # Get template
    response = client.get(f"/ains/task-templates/{template_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["template_id"] == template_id
    assert data["default_input_data"] == {"key": "value"}

def test_create_task_from_template():
    """Test creating a task from a template"""
    # Create template
    create_template_response = client.post("/ains/task-templates", json={
        "name": "Test Template",
        "client_id": "client_1",
        "task_type": "test",
        "capability_required": "data:v1",
        "default_input_data": {
            "algorithm": "standard",
            "format": "json"
        },
        "default_priority": 5
    })
    template_id = create_template_response.json()["template_id"]
    
    # Create task from template
    response = client.post("/ains/tasks/from-template", json={
        "template_id": template_id,
        "input_data": {
            "file": "data.csv"
        },
        "priority": 8
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "task_id" in data
    assert data["template_id"] == template_id

def test_update_task_template():
    """Test updating a task template"""
    # Create template
    create_response = client.post("/ains/task-templates", json={
        "name": "Test Template",
        "client_id": "client_1",
        "task_type": "test",
        "capability_required": "data:v1",
        "default_input_data": {}
    })
    template_id = create_response.json()["template_id"]
    
    # Update template
    response = client.patch(f"/ains/task-templates/{template_id}", json={
        "name": "Updated Template",
        "default_priority": 8
    })
    
    assert response.status_code == 200
    
    # Verify update
    get_response = client.get(f"/ains/task-templates/{template_id}")
    assert get_response.json()["name"] == "Updated Template"

def test_delete_task_template():
    """Test deleting a task template"""
    # Create template
    create_response = client.post("/ains/task-templates", json={
        "name": "Test Template",
        "client_id": "client_1",
        "task_type": "test",
        "capability_required": "data:v1",
        "default_input_data": {}
    })
    template_id = create_response.json()["template_id"]
    
    # Delete template
    response = client.delete(f"/ains/task-templates/{template_id}")
    assert response.status_code == 200
    
    # Verify deleted
    get_response = client.get(f"/ains/task-templates/{template_id}")
    assert get_response.status_code == 404
