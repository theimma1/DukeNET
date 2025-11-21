"""Test capability publishing and listing"""

import pytest
from fastapi.testclient import TestClient
from ains.api import app
from ains.db import Base, engine

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)

def test_publish_and_list_capability(client):
    # Register agent first
    agent_data = {
        "agent_id": "cap_agent_01",
        "public_key": "abc123" * 10,
        "display_name": "Capability Agent",
        "endpoint": "http://localhost:8080",
        "signature": "signature" * 10,
        "tags": ["capability", "test"]
    }
    client.post("/ains/agents", json=agent_data)

    # Publish capability
    cap_data = {
        "name": "Test Capability",
        "description": "Testing capability endpoint",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "pricing_model": "per_call",
        "price": 0.01,
        "latency_p99_ms": 150,
        "availability_percent": 99.9,
        "signature": "signature"
    }
    response = client.post(f"/ains/agents/{agent_data['agent_id']}/capabilities", json=cap_data)
    assert response.status_code == 200
    data = response.json()
    assert "capability_id" in data
    assert data["status"] == "published"

    # List capabilities
    response = client.get(f"/ains/agents/{agent_data['agent_id']}/capabilities")
    assert response.status_code == 200
    caps = response.json()
    assert any(c["name"] == "Test Capability" for c in caps)
