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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
