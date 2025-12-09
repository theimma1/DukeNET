# Sprint 10 - Task Scheduling System (IMPLEMENTATION)

**Date:** November 28, 2025  
**Priority:** HIGH - Enables recurring tasks  
**Estimated Time:** 2 hours

---

## Overview

Build a production-ready task scheduling system that supports:
- **Cron expressions** (standard format)
- **One-time scheduled tasks** (date/time)
- **Recurring tasks** (daily, weekly, monthly)
- **Timezone support**
- **Automatic execution**
- **Status tracking**

---

## Database Schema (New Table)

```sql
CREATE TABLE scheduled_tasks (
    schedule_id VARCHAR PRIMARY KEY,
    client_id VARCHAR NOT NULL,
    task_type VARCHAR NOT NULL,
    capability_required VARCHAR NOT NULL,
    input_data JSON NOT NULL,
    priority INT DEFAULT 5,
    cron_expression VARCHAR,  -- "0 9 * * 1-5" for weekdays at 9 AM
    next_run_at TIMESTAMP,
    last_run_at TIMESTAMP NULL,
    status VARCHAR DEFAULT 'ACTIVE',  -- ACTIVE, PAUSED, COMPLETED, FAILED
    total_runs INT DEFAULT 0,
    failed_runs INT DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    FOREIGN KEY (client_id) REFERENCES agents(agent_id)
);

CREATE TABLE schedule_executions (
    execution_id VARCHAR PRIMARY KEY,
    schedule_id VARCHAR NOT NULL,
    task_id VARCHAR NOT NULL,
    executed_at TIMESTAMP NOT NULL,
    status VARCHAR NOT NULL,  -- PENDING, COMPLETED, FAILED
    result_data JSON NULL,
    error_message TEXT NULL,
    FOREIGN KEY (schedule_id) REFERENCES scheduled_tasks(schedule_id),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE INDEX idx_scheduled_next_run ON scheduled_tasks(next_run_at, status);
CREATE INDEX idx_schedule_client ON scheduled_tasks(client_id);
```

---

## API Endpoints

### 1. Create Scheduled Task

**Endpoint:** `POST /aitp/tasks/schedule`

**Request:**
```json
{
  "client_id": "client-123",
  "task_type": "daily-report",
  "capability_required": "report-v1",
  "input_data": {"report_type": "sales"},
  "priority": 7,
  "cron_expression": "0 9 * * *",
  "description": "Daily sales report at 9 AM every day",
  "timezone": "America/New_York"
}
```

**Response:**
```json
{
  "schedule_id": "sched-abc123",
  "status": "ACTIVE",
  "cron_expression": "0 9 * * *",
  "next_run_at": "2025-11-29T14:00:00Z",
  "description": "Daily sales report at 9 AM every day",
  "created_at": "2025-11-28T02:45:00Z"
}
```

---

### 2. List Scheduled Tasks

**Endpoint:** `GET /aitp/tasks/schedule`

**Query Parameters:**
```
?client_id=client-123
&status=ACTIVE
&limit=20
&offset=0
```

**Response:**
```json
{
  "schedules": [
    {
      "schedule_id": "sched-abc123",
      "task_type": "daily-report",
      "status": "ACTIVE",
      "cron_expression": "0 9 * * *",
      "next_run_at": "2025-11-29T14:00:00Z",
      "last_run_at": "2025-11-28T14:00:00Z",
      "total_runs": 1,
      "failed_runs": 0
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

---

### 3. Get Schedule Details

**Endpoint:** `GET /aitp/tasks/schedule/{schedule_id}`

**Response:**
```json
{
  "schedule_id": "sched-abc123",
  "client_id": "client-123",
  "task_type": "daily-report",
  "capability_required": "report-v1",
  "input_data": {"report_type": "sales"},
  "priority": 7,
  "cron_expression": "0 9 * * *",
  "status": "ACTIVE",
  "next_run_at": "2025-11-29T14:00:00Z",
  "last_run_at": "2025-11-28T14:00:00Z",
  "total_runs": 1,
  "failed_runs": 0,
  "description": "Daily sales report at 9 AM every day",
  "created_at": "2025-11-28T02:45:00Z",
  "updated_at": "2025-11-28T02:45:00Z"
}
```

---

### 4. Update Schedule

**Endpoint:** `PUT /aitp/tasks/schedule/{schedule_id}`

**Request:**
```json
{
  "cron_expression": "0 10 * * *",
  "priority": 8,
  "status": "PAUSED"
}
```

**Response:**
```json
{
  "schedule_id": "sched-abc123",
  "status": "PAUSED",
  "cron_expression": "0 10 * * *",
  "priority": 8
}
```

---

### 5. Delete/Cancel Schedule

**Endpoint:** `DELETE /aitp/tasks/schedule/{schedule_id}`

**Response:**
```json
{
  "schedule_id": "sched-abc123",
  "status": "DELETED",
  "message": "Schedule cancelled successfully"
}
```

---

### 6. Get Execution History

**Endpoint:** `GET /aitp/tasks/schedule/{schedule_id}/executions`

**Response:**
```json
{
  "executions": [
    {
      "execution_id": "exec-001",
      "task_id": "task-001",
      "executed_at": "2025-11-28T14:00:00Z",
      "status": "COMPLETED",
      "result_data": {...},
      "error_message": null
    },
    {
      "execution_id": "exec-002",
      "task_id": "task-002",
      "executed_at": "2025-11-29T14:00:00Z",
      "status": "PENDING",
      "result_data": null,
      "error_message": null
    }
  ]
}
```

---

## Implementation Files

### 1. `ains/scheduler.py` (NEW)

```python
"""Task scheduling system with cron support"""
import asyncio
from datetime import datetime, timezone, timedelta
from croniter import croniter  # pip install croniter
import uuid
from sqlalchemy.orm import Session
from .db import ScheduledTask, ScheduleExecution, Task

class TaskScheduler:
    """Manages scheduled task execution"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_schedule(self, client_id: str, task_type: str,
                       capability_required: str, input_data: dict,
                       cron_expression: str, priority: int = 5,
                       description: str = None) -> dict:
        """Create a new scheduled task"""
        schedule_id = f"sched-{uuid.uuid4().hex[:8]}"
        
        # Calculate next run time
        cron = croniter(cron_expression, datetime.now(timezone.utc))
        next_run = cron.get_next(datetime)
        
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
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
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
    
    def get_due_schedules(self) -> list:
        """Get all schedules that are due to run"""
        now = datetime.now(timezone.utc)
        due_schedules = self.db.query(ScheduledTask).filter(
            ScheduledTask.status == "ACTIVE",
            ScheduledTask.next_run_at <= now
        ).all()
        return due_schedules
    
    def execute_schedule(self, schedule: ScheduledTask) -> str:
        """Execute a scheduled task"""
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
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.db.add(task)
        
        # Record execution
        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        execution = ScheduleExecution(
            execution_id=execution_id,
            schedule_id=schedule.schedule_id,
            task_id=task_id,
            executed_at=datetime.now(timezone.utc),
            status="PENDING"
        )
        self.db.add(execution)
        
        # Update schedule
        schedule.last_run_at = datetime.now(timezone.utc)
        schedule.total_runs = (schedule.total_runs or 0) + 1
        
        # Calculate next run
        cron = croniter(schedule.cron_expression, schedule.last_run_at)
        schedule.next_run_at = cron.get_next(datetime)
        
        self.db.commit()
        return task_id
    
    def pause_schedule(self, schedule_id: str) -> bool:
        """Pause a scheduled task"""
        schedule = self.db.query(ScheduledTask).filter(
            ScheduledTask.schedule_id == schedule_id
        ).first()
        if schedule:
            schedule.status = "PAUSED"
            self.db.commit()
            return True
        return False
    
    def resume_schedule(self, schedule_id: str) -> bool:
        """Resume a paused schedule"""
        schedule = self.db.query(ScheduledTask).filter(
            ScheduledTask.schedule_id == schedule_id
        ).first()
        if schedule:
            schedule.status = "ACTIVE"
            self.db.commit()
            return True
        return False

async def scheduler_worker(db_session):
    """Background worker that executes due schedules"""
    while True:
        try:
            scheduler = TaskScheduler(db_session)
            due_schedules = scheduler.get_due_schedules()
            
            for schedule in due_schedules:
                try:
                    task_id = scheduler.execute_schedule(schedule)
                    print(f"✓ Executed schedule {schedule.schedule_id}, task {task_id}")
                except Exception as e:
                    print(f"✗ Failed to execute schedule {schedule.schedule_id}: {e}")
                    schedule.failed_runs = (schedule.failed_runs or 0) + 1
                    db_session.commit()
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"Scheduler worker error: {e}")
            await asyncio.sleep(30)
```

---

## API Endpoints to Add (in `ains/api.py`)

```python
from .scheduler import TaskScheduler

# POST - Create schedule
@app.post("/aitp/tasks/schedule")
def create_schedule(schedule_req: dict, db: Session = Depends(get_db)):
    scheduler = TaskScheduler(db)
    return scheduler.create_schedule(
        client_id=schedule_req["client_id"],
        task_type=schedule_req["task_type"],
        capability_required=schedule_req["capability_required"],
        input_data=schedule_req["input_data"],
        cron_expression=schedule_req["cron_expression"],
        priority=schedule_req.get("priority", 5)
    )

# GET - List schedules
@app.get("/aitp/tasks/schedule")
def list_schedules(client_id: str = None, status: str = None, db: Session = Depends(get_db)):
    query = db.query(ScheduledTask)
    if client_id:
        query = query.filter(ScheduledTask.client_id == client_id)
    if status:
        query = query.filter(ScheduledTask.status == status)
    schedules = query.all()
    return {"schedules": schedules, "total": len(schedules)}

# GET - Get schedule details
@app.get("/aitp/tasks/schedule/{schedule_id}")
def get_schedule(schedule_id: str, db: Session = Depends(get_db)):
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule

# PUT - Update schedule
@app.put("/aitp/tasks/schedule/{schedule_id}")
def update_schedule(schedule_id: str, updates: dict, db: Session = Depends(get_db)):
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    for key, value in updates.items():
        if hasattr(schedule, key):
            setattr(schedule, key, value)
    
    db.commit()
    db.refresh(schedule)
    return schedule

# DELETE - Cancel schedule
@app.delete("/aitp/tasks/schedule/{schedule_id}")
def delete_schedule(schedule_id: str, db: Session = Depends(get_db)):
    schedule = db.query(ScheduledTask).filter(
        ScheduledTask.schedule_id == schedule_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    db.delete(schedule)
    db.commit()
    return {"schedule_id": schedule_id, "status": "DELETED"}

# GET - Execution history
@app.get("/aitp/tasks/schedule/{schedule_id}/executions")
def get_executions(schedule_id: str, limit: int = 50, db: Session = Depends(get_db)):
    executions = db.query(ScheduleExecution).filter(
        ScheduleExecution.schedule_id == schedule_id
    ).order_by(ScheduleExecution.executed_at.desc()).limit(limit).all()
    return {"executions": executions}
```

---

## Installation

```bash
# Install croniter for cron expression parsing
pip install croniter

# Restart API with new scheduler worker
cd /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python
uvicorn ains.api:app --reload --port 8000
```

---

## Example Usage

```bash
# Create daily schedule
curl -X POST http://localhost:8000/aitp/tasks/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "client-1",
    "task_type": "daily-report",
    "capability_required": "report-v1",
    "input_data": {"report_type": "sales"},
    "priority": 7,
    "cron_expression": "0 9 * * *",
    "description": "Daily sales report at 9 AM"
  }'

# List schedules
curl http://localhost:8000/aitp/tasks/schedule?client_id=client-1

# Pause schedule
curl -X PUT http://localhost:8000/aitp/tasks/schedule/sched-abc123 \
  -H "Content-Type: application/json" \
  -d '{"status": "PAUSED"}'

# Get execution history
curl http://localhost:8000/aitp/tasks/schedule/sched-abc123/executions
```

---

## Testing

```bash
# Test cron expression
pytest tests/unit/test_scheduler.py -v

# Integration test
pytest tests/integration/test_scheduling.py -v
```

---

## Success Criteria

- [ ] Schedules stored in database
- [ ] Cron expressions parsed correctly
- [ ] Background worker executes due schedules
- [ ] New tasks created from schedule
- [ ] Execution history recorded
- [ ] Status updates tracked
- [ ] API endpoints working
- [ ] Integration tests passing

---

## Ready to Build? 🎯

This is the complete implementation guide for Sprint 10 - Task Scheduling System.

**Would you like me to:**
1. Implement all the code (scheduler.py, db models, API endpoints)
2. Create the integration tests
3. Both?
