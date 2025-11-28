"""API endpoints for task scheduling"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from .db import get_db, ScheduledTask, ScheduleExecution
from .scheduler import TaskScheduler, validate_cron_expression, get_next_run_time

# Create router for scheduling endpoints
router = APIRouter(prefix="/aitp/tasks", tags=["scheduling"])


@router.post("/schedule")
def create_schedule(
    client_id: str,
    task_type: str,
    capability_required: str,
    input_data: Dict[str, Any],
    cron_expression: str,
    priority: int = 5,
    description: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new scheduled task"""
    try:
        scheduler = TaskScheduler(db)
        return scheduler.create_schedule(
            client_id=client_id,
            task_type=task_type,
            capability_required=capability_required,
            input_data=input_data,
            cron_expression=cron_expression,
            priority=priority,
            description=description
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("/schedule")
def list_schedules(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List scheduled tasks"""
    try:
        scheduler = TaskScheduler(db)
        return scheduler.list_schedules(
            client_id=client_id,
            status=status,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list schedules: {str(e)}")


@router.get("/schedule/{schedule_id}")
def get_schedule(
    schedule_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get schedule details"""
    try:
        scheduler = TaskScheduler(db)
        schedule = scheduler.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {
            "schedule_id": schedule.schedule_id,
            "client_id": schedule.client_id,
            "task_type": schedule.task_type,
            "capability_required": schedule.capability_required,
            "input_data": schedule.input_data,
            "priority": schedule.priority,
            "cron_expression": schedule.cron_expression,
            "status": schedule.status,
            "next_run_at": schedule.next_run_at.isoformat() if schedule.next_run_at else None,
            "last_run_at": schedule.last_run_at.isoformat() if schedule.last_run_at else None,
            "total_runs": schedule.total_runs,
            "failed_runs": schedule.failed_runs,
            "created_at": schedule.created_at.isoformat(),
            "updated_at": schedule.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


@router.put("/schedule/{schedule_id}")
def update_schedule(
    schedule_id: str,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Update a scheduled task"""
    try:
        scheduler = TaskScheduler(db)
        schedule = scheduler.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        if "cron_expression" in updates:
            if not validate_cron_expression(updates["cron_expression"]):
                raise ValueError("Invalid cron expression format")
            schedule.cron_expression = updates["cron_expression"]
            schedule.next_run_at = get_next_run_time(updates["cron_expression"])
        
        if "priority" in updates:
            schedule.priority = updates["priority"]
        if "status" in updates:
            schedule.status = updates["status"]
        
        schedule.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(schedule)
        
        return {
            "schedule_id": schedule.schedule_id,
            "status": schedule.status,
            "cron_expression": schedule.cron_expression,
            "priority": schedule.priority,
            "updated_at": schedule.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.delete("/schedule/{schedule_id}")
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Delete/cancel a scheduled task"""
    try:
        scheduler = TaskScheduler(db)
        schedule = scheduler.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        db.delete(schedule)
        db.commit()
        
        return {
            "schedule_id": schedule_id,
            "status": "DELETED",
            "message": "Schedule cancelled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


@router.post("/schedule/{schedule_id}/pause")
def pause_schedule(
    schedule_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Pause a scheduled task"""
    try:
        scheduler = TaskScheduler(db)
        
        if not scheduler.pause_schedule(schedule_id):
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {
            "schedule_id": schedule_id,
            "status": "PAUSED",
            "message": "Schedule paused successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause schedule: {str(e)}")


@router.post("/schedule/{schedule_id}/resume")
def resume_schedule(
    schedule_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Resume a paused schedule"""
    try:
        scheduler = TaskScheduler(db)
        
        if not scheduler.resume_schedule(schedule_id):
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {
            "schedule_id": schedule_id,
            "status": "ACTIVE",
            "message": "Schedule resumed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume schedule: {str(e)}")


@router.get("/schedule/{schedule_id}/executions")
def get_executions(
    schedule_id: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get execution history for a schedule"""
    try:
        scheduler = TaskScheduler(db)
        
        if not scheduler.get_schedule(schedule_id):
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        executions = db.query(ScheduleExecution).filter(
            ScheduleExecution.schedule_id == schedule_id
        ).order_by(ScheduleExecution.executed_at.desc()).limit(limit).all()
        
        return {
            "schedule_id": schedule_id,
            "executions": [
                {
                    "execution_id": exec.execution_id,
                    "task_id": exec.task_id,
                    "executed_at": exec.executed_at.isoformat(),
                    "status": exec.status,
                    "result_data": exec.result_data,
                    "error_message": exec.error_message
                }
                for exec in executions
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get executions: {str(e)}")


@router.post("/schedule/validate")
def validate_cron(cron_expression: str) -> Dict[str, Any]:
    """Validate a cron expression"""
    try:
        is_valid = validate_cron_expression(cron_expression)
        
        if is_valid:
            next_run = get_next_run_time(cron_expression)
            return {
                "valid": True,
                "cron_expression": cron_expression,
                "next_run_at": next_run.isoformat(),
                "message": "Valid cron expression"
            }
        else:
            return {
                "valid": False,
                "cron_expression": cron_expression,
                "message": "Invalid cron expression"
            }
    except Exception as e:
        return {
            "valid": False,
            "cron_expression": cron_expression,
            "error": str(e)
        }
