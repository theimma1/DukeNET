"""Test capability publishing and listing with secure keys"""

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

def test_publish_and_list_capability(client):
    pub_key = generate_secure_hex_key()
    agent_data = {
        "agent_id": "cap_agent_01",
        "public_key": pub_key,
        "display_name": "Capability Agent",
        "endpoint": "http://localhost:8080",
        "signature": pub_key,
        "tags": ["capability", "test"]
    }
    post_resp = client.post("/ains/agents", json=agent_data)
    assert post_resp.status_code == 200, post_resp.text

    cap_data = {
        "name": "Test Capability",
        "description": "Testing capability endpoint",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "pricing_model": "per_call",
        "price": 0.01,
        "latency_p99_ms": 150,
        "availability_percent": 99.9,
        "signature": pub_key
    }
    response = client.post(f"/ains/agents/{agent_data['agent_id']}/capabilities", json=cap_data)
    assert response.status_code == 200, response.text
    data = response.json()
    assert "capability_id" in data
    assert data["status"] == "published"

    response = client.get(f"/ains/agents/{agent_data['agent_id']}/capabilities")
    assert response.status_code == 200, response.text
    caps = response.json()
    assert any(c["name"] == "Test Capability" for c in caps)
