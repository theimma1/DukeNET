"""Test AINS API Endpoints with secure random keys"""

import os
import tempfile
import pytest
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ains.api import app
from ains.db import Base, get_db

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


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "AINS"


def test_register_agent(client):
    registration = {
        "agent_id": "test_agent_abc123",
        "public_key": generate_secure_hex_key(),
        "display_name": "Test Agent",
        "description": "A test agent for AINS",
        "endpoint": "http://localhost:8001",
        "signature": generate_secure_hex_key(),
        "tags": ["python", "testing"]
    }
    response = client.post("/ains/agents", json=registration)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["agent_id"] == registration["agent_id"]
    assert data["display_name"] == registration["display_name"]
    assert data["status"] == "ACTIVE"
    assert data["trust_score"] == 50.0


def test_register_duplicate_agent(client):
    pub_key = generate_secure_hex_key()
    registration = {
        "agent_id": "test_duplicate",
        "public_key": pub_key,
        "display_name": "Duplicate Agent",
        "endpoint": "http://localhost:8002",
        "signature": pub_key,
    }
    response1 = client.post("/ains/agents", json=registration)
    assert response1.status_code == 200, response1.text
    response2 = client.post("/ains/agents", json=registration)
    assert response2.status_code == 409, response2.text
    assert "already registered" in response2.json()["detail"]


def test_get_agent(client):
    pub_key = generate_secure_hex_key()
    registration = {
        "agent_id": "lookup_test_123",
        "public_key": pub_key,
        "display_name": "Lookup Test Agent",
        "endpoint": "http://localhost:8003",
        "signature": pub_key,
    }
    post_resp = client.post("/ains/agents", json=registration)
    assert post_resp.status_code == 200, post_resp.text

    response = client.get(f"/ains/agents/{registration['agent_id']}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["agent_id"] == registration["agent_id"]
    assert data["display_name"] == registration["display_name"]
    assert data["status"] == "ACTIVE"


def test_get_nonexistent_agent(client):
    response = client.get("/ains/agents/nonexistent_agent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_list_agents(client):
    for i in range(3):
        pub_key = generate_secure_hex_key()
        registration = {
            "agent_id": f"list_test_{i}",
            "public_key": pub_key,
            "display_name": f"Agent {i}",
            "endpoint": f"http://localhost:800{i}",
            "signature": pub_key,
        }
        post_resp = client.post("/ains/agents", json=registration)
        assert post_resp.status_code == 200, post_resp.text

    response = client.get("/ains/agents")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] >= 3
    assert len(data["agents"]) >= 3


def test_list_agents_with_limit(client):
    response = client.get("/ains/agents?limit=2&offset=0")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["limit"] == 2
    assert data["offset"] == 0
