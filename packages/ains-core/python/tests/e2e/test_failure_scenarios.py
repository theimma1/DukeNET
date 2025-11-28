"""E2E Tests: Failure Scenarios"""
import pytest
import requests
import uuid


class TestScheduleFailures:
    def test_pause_nonexistent_schedule(self, api_url):
        """Test pausing a schedule that doesn't exist"""
        fake_id = f"sched-{uuid.uuid4().hex[:8]}"
        response = requests.post(f"{api_url}/aitp/tasks/schedule/{fake_id}/pause")
        assert response.status_code == 404

    def test_invalid_endpoint(self, api_url):
        """Test calling non-existent endpoint"""
        response = requests.get(f"{api_url}/aitp/tasks/nonexistent")
        assert response.status_code in [404, 405]


@pytest.fixture
def api_url():
    return "http://localhost:8000"
