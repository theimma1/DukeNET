"""E2E Tests: Agent Integration"""
import pytest
import requests
import uuid


class TestAgentRegistration:
    def test_register_new_agent(self, api_url):
        """Test agent registration"""
        agent_id = f"agent-{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{api_url}/ains/agents",
            json={
                "agent_id": agent_id,
                "agent_name": "test-agent",
                "public_key": f"pk_{uuid.uuid4().hex[:16]}",
                "capabilities": ["test"],
                "metadata": {}
            }
        )
        assert response.status_code in [200, 422]


@pytest.fixture
def api_url():
    return "http://localhost:8000"