"""Test webhook notifications"""
import os
import tempfile
import pytest
import secrets
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db
from ains.webhooks import register_webhook, trigger_webhook_event, EVENT_TASK_COMPLETED

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


def test_register_webhook():
    """Test webhook registration"""
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
    
    # Register webhook
    webhook_payload = {
        "agent_id": agent_id,
        "url": "https://example.com/webhook",
        "events": ["task.completed", "task.failed"],
        "secret": "test_secret_123"
    }
    
    response = client.post("/ains/webhooks", json=webhook_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "webhook_id" in data
    assert data["events"] == ["task.completed", "task.failed"]


def test_get_webhook():
    """Test getting webhook details"""
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
    
    # Register webhook
    webhook_payload = {
        "agent_id": agent_id,
        "url": "https://example.com/webhook",
        "events": ["task.completed"]
    }
    
    webhook_resp = client.post("/ains/webhooks", json=webhook_payload)
    webhook_id = webhook_resp.json()["webhook_id"]
    
    # Get webhook
    response = client.get(f"/ains/webhooks/{webhook_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["webhook_id"] == webhook_id
    assert data["active"] is True


def test_delete_webhook():
    """Test webhook deletion"""
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
    
    # Register webhook
    webhook_payload = {
        "agent_id": agent_id,
        "url": "https://example.com/webhook",
        "events": ["task.completed"]
    }
    
    webhook_resp = client.post("/ains/webhooks", json=webhook_payload)
    webhook_id = webhook_resp.json()["webhook_id"]
    
    # Delete webhook
    response = client.delete(f"/ains/webhooks/{webhook_id}?agent_id={agent_id}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "deactivated"


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    os.close(temp_db_fd)
    os.unlink(temp_db_path)
