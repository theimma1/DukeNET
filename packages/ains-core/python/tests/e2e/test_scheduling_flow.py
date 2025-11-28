"""E2E Tests: Scheduling Flow"""
import pytest
import requests
import uuid


class TestScheduleCreation:
    def test_create_valid_schedule(self, api_url, test_client_id):
        """Test creating a schedule with valid cron expression"""
        response = requests.post(
            f"{api_url}/aitp/tasks/schedule",
            params={
                "client_id": test_client_id,
                "task_type": "daily-report",
                "capability_required": "report-v1",
                "cron_expression": "0 9 * * *",
                "priority": 7
            },
            json={"input_data": {"report_type": "daily"}}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "schedule_id" in data
        assert data["status"] == "ACTIVE"
    
    def test_list_schedules(self, api_url):
        """Test listing all schedules"""
        response = requests.get(f"{api_url}/aitp/tasks/schedule")
        assert response.status_code == 200


class TestSchedulePauseResume:
    def test_pause_and_resume(self, api_url, test_client_id):
        """Test pause and resume schedule"""
        # Create schedule
        response = requests.post(
            f"{api_url}/aitp/tasks/schedule",
            params={
                "client_id": test_client_id,
                "task_type": "pause-test",
                "capability_required": "test",
                "cron_expression": "0 18 * * *",
                "priority": 5
            },
            json={"input_data": {}}
        )
        schedule_id = response.json()["schedule_id"]
        
        # Pause
        response = requests.post(f"{api_url}/aitp/tasks/schedule/{schedule_id}/pause")
        assert response.status_code == 200
        
        # Resume
        response = requests.post(f"{api_url}/aitp/tasks/schedule/{schedule_id}/resume")
        assert response.status_code == 200


@pytest.fixture
def api_url():
    return "http://localhost:8000"


@pytest.fixture
def test_client_id():
    return f"test-client-{uuid.uuid4().hex[:8]}"
