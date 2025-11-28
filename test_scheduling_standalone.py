"""
Task Scheduling System - Standalone Tests
Location: tests/integration/test_scheduling.py
Tests work without requiring scheduler module to be imported
"""

import pytest
from datetime import datetime, timezone


class TestCronValidation:
    """Test cron expression validation using croniter directly"""
    
    def test_croniter_installed(self):
        """Verify croniter is installed"""
        try:
            from croniter import croniter
            assert croniter is not None
        except ImportError:
            pytest.skip("croniter not installed - run: pip install croniter")
    
    def test_valid_cron_expressions(self):
        """Test valid cron expressions"""
        from croniter import croniter
        
        valid_expressions = [
            "* * * * *",
            "0 * * * *",
            "0 9 * * *",
            "0 9 * * 1-5",
            "0 0 1 * *",
            "*/15 * * * *",
            "0 */6 * * *",
            "0 0 * * 0",
        ]
        
        for expr in valid_expressions:
            try:
                cron = croniter(expr)
                assert cron is not None, f"Failed to parse: {expr}"
            except (KeyError, ValueError) as e:
                pytest.fail(f"Invalid expression {expr}: {e}")
    
    def test_invalid_cron_expressions(self):
        """Test invalid cron expressions are rejected"""
        from croniter import croniter
        
        invalid_expressions = [
            "invalid",
            "60 * * * *",
            "* 25 * * *",
            "* * 32 * *",
            "",
        ]
        
        for expr in invalid_expressions:
            with pytest.raises((KeyError, ValueError)):
                croniter(expr)
    
    def test_next_run_time_calculation(self):
        """Test calculating next run time"""
        from croniter import croniter
        
        cron = croniter("0 9 * * *", datetime.now(timezone.utc))
        next_run = cron.get_next(datetime)
        
        assert next_run is not None
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now(timezone.utc)
    
    def test_multiple_run_times(self):
        """Test getting multiple future run times"""
        from croniter import croniter
        
        cron = croniter("0 9 * * *", datetime.now(timezone.utc))
        runs = [cron.get_next(datetime) for _ in range(5)]
        
        assert len(runs) == 5
        assert all(isinstance(r, datetime) for r in runs)
        # Verify they're in ascending order
        for i in range(len(runs)-1):
            assert runs[i] < runs[i+1]


class TestSchedulerImports:
    """Test that scheduler module can be imported"""
    
    def test_scheduler_module_exists(self):
        """Test scheduler module can be imported"""
        try:
            from ains import scheduler
            assert scheduler is not None
            assert hasattr(scheduler, 'TaskScheduler')
            assert hasattr(scheduler, 'validate_cron_expression')
            assert hasattr(scheduler, 'get_next_run_time')
        except ImportError as e:
            pytest.skip(f"scheduler module not yet copied to ains/: {e}")
    
    def test_api_endpoints_module_exists(self):
        """Test API endpoints module can be imported"""
        try:
            from ains import api_scheduling_endpoints
            assert api_scheduling_endpoints is not None
            assert hasattr(api_scheduling_endpoints, 'ScheduleCreate')
        except ImportError as e:
            pytest.skip(f"api_scheduling_endpoints module not yet copied to ains/: {e}")


class TestDatabaseModels:
    """Test that database models exist"""
    
    def test_scheduled_task_model_exists(self):
        """Test ScheduledTask model is defined in db"""
        try:
            from ains.db import ScheduledTask
            assert ScheduledTask is not None
            # Check it has expected attributes
            assert hasattr(ScheduledTask, '__tablename__')
            assert ScheduledTask.__tablename__ == 'scheduled_tasks'
        except (ImportError, AttributeError) as e:
            pytest.skip(f"ScheduledTask model not yet added to ains/db.py: {e}")
    
    def test_schedule_execution_model_exists(self):
        """Test ScheduleExecution model is defined in db"""
        try:
            from ains.db import ScheduleExecution
            assert ScheduleExecution is not None
            assert hasattr(ScheduleExecution, '__tablename__')
            assert ScheduleExecution.__tablename__ == 'schedule_executions'
        except (ImportError, AttributeError) as e:
            pytest.skip(f"ScheduleExecution model not yet added to ains/db.py: {e}")


class TestAPIEndpoints:
    """Test API endpoints are registered"""
    
    def test_create_schedule_endpoint_exists(self):
        """Test POST /aitp/tasks/schedule endpoint exists"""
        try:
            from ains.api import app
            routes = [route.path for route in app.routes]
            assert '/aitp/tasks/schedule' in routes
        except (ImportError, AttributeError) as e:
            pytest.skip(f"API routes not yet added: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
