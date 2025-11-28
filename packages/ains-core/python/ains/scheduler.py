"""Task scheduling system with cron support"""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Any
from croniter import croniter
from sqlalchemy.orm import Session

from .db import (
    ScheduledTask, 
    ScheduleExecution, 
    Task,
    engine,
    SessionLocal
)


def validate_cron_expression(cron_expr: str) -> bool:
    """
    Validate a cron expression string
    
    Args:
        cron_expr: Cron expression (e.g., "0 9 * * *")
    
    Returns:
        True if valid, False otherwise
    """
    try:
        croniter(cron_expr)
        return True
    except (KeyError, ValueError):
        return False


def get_next_run_time(cron_expr: str, base_time: Optional[datetime] = None) -> datetime:
    """
    Calculate next run time from cron expression
    
    Args:
        cron_expr: Cron expression (e.g., "0 9 * * *")
        base_time: Base datetime to calculate from (defaults to now UTC)
    
    Returns:
        Next run time as datetime object
    
    Raises:
        ValueError: If cron expression is invalid
    """
    if base_time is None:
        base_time = datetime.now(timezone.utc)
    
    try:
        cron = croniter(cron_expr, base_time)
        return cron.get_next(datetime)
    except (KeyError, ValueError) as e:
        raise ValueError(f"Invalid cron expression: {cron_expr}") from e


class TaskScheduler:
    """Manages scheduled task execution with cron support"""
    
    def __init__(self, db: Session):
        """
        Initialize TaskScheduler
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
    
    def create_schedule(
        self,
        client_id: str,
        task_type: str,
        capability_required: str,
        input_data: Dict[str, Any],
        cron_expression: str,
        priority: int = 5,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new scheduled task
        
        Args:
            client_id: Client/agent ID
            task_type: Type of task
            capability_required: Required capability
            input_data: Task input data
            cron_expression: Cron expression (e.g., "0 9 * * *")
            priority: Task priority (1-10, default 5)
            description: Optional description
        
        Returns:
            Dictionary with schedule details
        
        Raises:
            ValueError: If cron expression is invalid
        """
        # Validate cron expression
        if not validate_cron_expression(cron_expression):
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        schedule_id = f"sched-{uuid.uuid4().hex[:8]}"
        
        # Calculate next run time
        now = datetime.now(timezone.utc)
        next_run = get_next_run_time(cron_expression, now)
        
        # Create schedule record
        schedule = ScheduledTask(
            schedule_id=schedule_id,
            client_id=client_id,
            task_type=task_type,
            capability_required=capability_required,
            input_data=input_data,
            priority=priority,
            cron_expression=cron_expression,
            next_run_at=next_run,
            status="ACTIVE",
            total_runs=0,
            failed_runs=0,
            created_at=now,
            updated_at=now
        )
        
        self.db.add(schedule)
        self.db.commit()
        self.db.refresh(schedule)
        
        return {
            "schedule_id": schedule.schedule_id,
            "status": schedule.status,
            "cron_expression": schedule.cron_expression,
            "next_run_at": schedule.next_run_at.isoformat(),
            "description": description,
            "created_at": schedule.created_at.isoformat()
        }
    
    def get_schedule(self, schedule_id: str) -> Optional[ScheduledTask]:
        """Get schedule by ID"""
        return self.db.query(ScheduledTask).filter(
            ScheduledTask.schedule_id == schedule_id
        ).first()
    
    def list_schedules(
        self,
        client_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List scheduled tasks
        
        Args:
            client_id: Filter by client ID
            status: Filter by status (ACTIVE, PAUSED, COMPLETED, FAILED)
            limit: Results limit
            offset: Results offset
        
        Returns:
            Dictionary with schedules list and total count
        """
        query = self.db.query(ScheduledTask)
        
        if client_id:
            query = query.filter(ScheduledTask.client_id == client_id)
        if status:
            query = query.filter(ScheduledTask.status == status)
        
        total = query.count()
        schedules = query.offset(offset).limit(limit).all()
        
        return {
            "schedules": [
                {
                    "schedule_id": s.schedule_id,
                    "client_id": s.client_id,
                    "task_type": s.task_type,
                    "status": s.status,
                    "cron_expression": s.cron_expression,
                    "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
                    "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
                    "total_runs": s.total_runs,
                    "failed_runs": s.failed_runs
                }
                for s in schedules
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def get_due_schedules(self) -> List[ScheduledTask]:
        """Get all schedules that are due to run"""
        now = datetime.now(timezone.utc)
        return self.db.query(ScheduledTask).filter(
            ScheduledTask.status == "ACTIVE",
            ScheduledTask.next_run_at <= now
        ).all()
    
    def execute_schedule(self, schedule: ScheduledTask) -> str:
        """
        Execute a scheduled task by creating a new task from the schedule
        
        Args:
            schedule: ScheduledTask to execute
        
        Returns:
            Task ID of created task
        """
        now = datetime.now(timezone.utc)
        
        # Create task from schedule
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = Task(
            task_id=task_id,
            client_id=schedule.client_id,
            task_type=schedule.task_type,
            capability_required=schedule.capability_required,
            input_data=schedule.input_data,
            priority=schedule.priority,
            status="PENDING",
            created_at=now,
            updated_at=now
        )
        self.db.add(task)
        
        # Record execution
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        execution = ScheduleExecution(
            execution_id=execution_id,
            schedule_id=schedule.schedule_id,
            task_id=task_id,
            executed_at=now,
            status="PENDING"
        )
        self.db.add(execution)
        
        # Update schedule
        schedule.last_run_at = now
        schedule.total_runs = (schedule.total_runs or 0) + 1
        
        # Calculate next run
        next_run = get_next_run_time(schedule.cron_expression, now)
        schedule.next_run_at = next_run
        schedule.updated_at = now
        
        self.db.commit()
        
        return task_id
    
    def update_schedule(
        self,
        schedule_id: str,
        updates: Dict[str, Any]
    ) -> Optional[ScheduledTask]:
        """
        Update a scheduled task
        
        Args:
            schedule_id: Schedule ID to update
            updates: Dictionary of fields to update
        
        Returns:
            Updated schedule or None if not found
        """
        schedule = self.get_schedule(schedule_id)
        if not schedule:
            return None
        
        # Validate cron expression if being updated
        if "cron_expression" in updates:
            if not validate_cron_expression(updates["cron_expression"]):
                raise ValueError(f"Invalid cron expression: {updates['cron_expression']}")
            # Recalculate next run time
            updates["next_run_at"] = get_next_run_time(updates["cron_expression"])
        
        # Update allowed fields
        allowed_fields = {
            "task_type", "capability_required", "input_data", "priority",
            "cron_expression", "status", "next_run_at", "description"
        }
        
        for key, value in updates.items():
            if key in allowed_fields:
                setattr(schedule, key, value)
        
        schedule.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(schedule)
        
        return schedule
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a scheduled task"""
        schedule = self.get_schedule(schedule_id)
        if schedule:
            schedule.status = "PAUSED"
            schedule.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule"""
        schedule = self.get_schedule(schedule_id)
        if schedule:
            schedule.status = "ACTIVE"
            schedule.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a scheduled task"""
        schedule = self.get_schedule(schedule_id)
        if schedule:
            self.db.delete(schedule)
            self.db.commit()
            return True
        return False
    
    def get_executions(
        self,
        schedule_id: str,
        limit: int = 50
    ) -> List[ScheduleExecution]:
        """Get execution history for a schedule"""
        return self.db.query(ScheduleExecution).filter(
            ScheduleExecution.schedule_id == schedule_id
        ).order_by(ScheduleExecution.executed_at.desc()).limit(limit).all()
    
    def record_execution_result(
        self,
        execution_id: str,
        status: str,
        result_data: Optional[Dict] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Record the result of a task execution
        
        Args:
            execution_id: Execution ID
            status: Status (PENDING, COMPLETED, FAILED)
            result_data: Result data if completed
            error_message: Error message if failed
        
        Returns:
            True if updated, False otherwise
        """
        execution = self.db.query(ScheduleExecution).filter(
            ScheduleExecution.execution_id == execution_id
        ).first()
        
        if execution:
            execution.status = status
            execution.result_data = result_data
            execution.error_message = error_message
            self.db.commit()
            return True
        
        return False


async def scheduler_worker(db_session: Session):
    """
    Background worker that executes due schedules
    
    This worker runs continuously, checking for schedules that are due
    and creating tasks from them.
    
    Args:
        db_session: Database session
    """
    print("🚀 Starting scheduler worker...")
    
    while True:
        try:
            scheduler = TaskScheduler(db_session)
            due_schedules = scheduler.get_due_schedules()
            
            if due_schedules:
                print(f"📅 Found {len(due_schedules)} due schedules")
            
            for schedule in due_schedules:
                try:
                    task_id = scheduler.execute_schedule(schedule)
                    print(f"✅ Executed schedule {schedule.schedule_id}, created task {task_id}")
                    print(f"   Next run: {schedule.next_run_at}")
                except Exception as e:
                    print(f"❌ Failed to execute schedule {schedule.schedule_id}: {e}")
                    schedule = scheduler.get_schedule(schedule.schedule_id)
                    if schedule:
                        schedule.failed_runs = (schedule.failed_runs or 0) + 1
                        schedule.updated_at = datetime.now(timezone.utc)
                        db_session.commit()
            
            # Check every 30 seconds
            await asyncio.sleep(30)
        except Exception as e:
            print(f"⚠️  Scheduler worker error: {e}")
            await asyncio.sleep(30)


def start_scheduler_worker():
    """
    Start the scheduler worker as a background task
    
    This should be called once when the application starts.
    """
    db = SessionLocal()
    
    try:
        asyncio.create_task(scheduler_worker(db))
        print("🎯 Scheduler worker started")
    except Exception as e:
        print(f"Failed to start scheduler worker: {e}")
        db.close()