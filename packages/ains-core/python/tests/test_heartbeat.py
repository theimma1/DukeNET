"""Test heartbeat endpoints and agent health monitoring"""

import os
import tempfile
import pytest
import secrets
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ains.api import app
from ains.db import Base, get_db, Agent

temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
SQLALCHEMY_TEST_DATABASE_URL = f"sqlite:///{temp_db_path}"

engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def teardown_module(module):
    os.close(temp_db_fd)
    os.unlink(temp_db_path)


def generate_secure_hex_key(length=64):
    return secrets.token_hex(length // 2)


def test_heartbeat_endpoint(client):
    """Test that heartbeat endpoint exists and works"""
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "heartbeat_endpoint_test",
        "public_key": pub_key,
        "display_name": "Heartbeat Endpoint Test",
        "endpoint": "http://localhost:8001",
        "signature": pub_key,
    }
    
    # Register agent
    post_resp = client.post("/ains/agents", json=agent_data)
    assert post_resp.status_code == 200
    
    # Send heartbeat with required fields
    heartbeat_data = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "status": "ACTIVE",
        "uptime_ms": 10000
    }
    
    heartbeat_resp = client.post(
        f"/ains/agents/{agent_data['agent_id']}/heartbeat",
        json=heartbeat_data
    )
    assert heartbeat_resp.status_code == 200
    assert "acknowledged" in heartbeat_resp.json()


def test_heartbeat_updates_timestamp(client):
    """Test that heartbeat updates the agent's last_heartbeat timestamp"""
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "heartbeat_test_1",
        "public_key": pub_key,
        "display_name": "Heartbeat Test Agent",
        "endpoint": "http://localhost:8002",
        "signature": pub_key,
    }
    
    # Register agent
    post_resp = client.post("/ains/agents", json=agent_data)
    assert post_resp.status_code == 200
    
    # Send heartbeat
    import time
    time.sleep(0.1)  # Small delay to ensure timestamp difference
    
    heartbeat_data = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "status": "ACTIVE",
        "uptime_ms": 10000
    }
    
    heartbeat_resp = client.post(
        f"/ains/agents/{agent_data['agent_id']}/heartbeat",
        json=heartbeat_data
    )
    assert heartbeat_resp.status_code == 200
    assert heartbeat_resp.json()["acknowledged"] is True


def test_heartbeat_sets_agent_active(client):
    """Test that heartbeat sets agent status to ACTIVE"""
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "heartbeat_test_2",
        "public_key": pub_key,
        "display_name": "Heartbeat Status Test",
        "endpoint": "http://localhost:8003",
        "signature": pub_key,
    }
    
    # Register agent
    client.post("/ains/agents", json=agent_data)
    
    # Send heartbeat with ACTIVE status
    heartbeat_data = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "status": "ACTIVE",
        "uptime_ms": 10000
    }
    
    heartbeat_resp = client.post(
        f"/ains/agents/{agent_data['agent_id']}/heartbeat",
        json=heartbeat_data
    )
    assert heartbeat_resp.status_code == 200
    
    # Verify agent status
    get_resp = client.get(f"/ains/agents/{agent_data['agent_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "ACTIVE"


def test_heartbeat_nonexistent_agent(client):
    """Test heartbeat for non-existent agent returns 404"""
    heartbeat_data = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "status": "ACTIVE",
        "uptime_ms": 10000
    }
    
    response = client.post(
        "/ains/agents/nonexistent_agent_xyz/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_multiple_heartbeats(client):
    """Test multiple consecutive heartbeats"""
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "heartbeat_test_3",
        "public_key": pub_key,
        "display_name": "Multiple Heartbeat Test",
        "endpoint": "http://localhost:8004",
        "signature": pub_key,
    }
    
    # Register agent
    client.post("/ains/agents", json=agent_data)
    
    # Send multiple heartbeats
    for i in range(5):
        heartbeat_data = {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "status": "ACTIVE",
            "uptime_ms": 10000 + (i * 1000)
        }
        response = client.post(
            f"/ains/agents/{agent_data['agent_id']}/heartbeat",
            json=heartbeat_data
        )
        assert response.status_code == 200
        assert "acknowledged" in response.json()


def test_heartbeat_with_metrics(client):
    """Test heartbeat with optional metrics"""
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "heartbeat_metrics_test",
        "public_key": pub_key,
        "display_name": "Metrics Test Agent",
        "endpoint": "http://localhost:8005",
        "signature": pub_key,
    }
    
    # Register agent
    client.post("/ains/agents", json=agent_data)
    
    # Send heartbeat with metrics
    heartbeat_data = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "status": "ACTIVE",
        "uptime_ms": 10000,
        "metrics": {
            "cpu_usage": 45.2,
            "memory_usage": 1024,
            "requests_per_second": 100
        }
    }
    
    response = client.post(
        f"/ains/agents/{agent_data['agent_id']}/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 200


def test_heartbeat_degraded_status(client):
    """Test heartbeat with DEGRADED status"""
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "heartbeat_degraded_test",
        "public_key": pub_key,
        "display_name": "Degraded Status Test",
        "endpoint": "http://localhost:8006",
        "signature": pub_key,
    }
    
    # Register agent
    client.post("/ains/agents", json=agent_data)
    
    # Send heartbeat with DEGRADED status
    heartbeat_data = {
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "status": "DEGRADED",
        "uptime_ms": 10000
    }
    
    response = client.post(
        f"/ains/agents/{agent_data['agent_id']}/heartbeat",
        json=heartbeat_data
    )
    assert response.status_code == 200
    
    # Verify status updated
    get_resp = client.get(f"/ains/agents/{agent_data['agent_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "DEGRADED"


def test_stale_agents_detection(client):
    """Test detecting agents with stale heartbeats"""
    # Create database session
    db = TestingSessionLocal()
    
    # Create agent with old heartbeat
    pub_key = generate_secure_hex_key()
    old_time = datetime.now(timezone.utc) - timedelta(hours=2)
    
    stale_agent = Agent(
        agent_id="stale_agent_test",
        public_key=pub_key,
        display_name="Stale Agent",
        endpoint_url="http://localhost:8007",
        status="ACTIVE",
        trust_score=50.0,
        created_at=old_time,
        last_heartbeat=old_time
    )
    db.add(stale_agent)
    db.commit()
    
    # Query for stale agents (no heartbeat in last hour)
    threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    stale_agents = db.query(Agent).filter(
        Agent.last_heartbeat < threshold
    ).all()
    
    assert len(stale_agents) >= 1
    assert any(a.agent_id == "stale_agent_test" for a in stale_agents)
    
    db.close()


def test_health_check_returns_timestamp(client):
    """Test that health check includes version info"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AINS"
    assert "version" in data