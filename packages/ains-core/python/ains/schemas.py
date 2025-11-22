from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class TaskCreate(BaseModel):
    client_id: str = Field(..., max_length=128)
    task_type: str = Field(..., max_length=128)
    capability_required: str = Field(..., max_length=256)
    input_data: Dict[str, Any]
    priority: int = Field(5, ge=0, le=10)

    @validator("input_data")
    def validate_payload_size(cls, v):
        import json
        size = len(json.dumps(v))
        if size > 10_000:
            raise ValueError(f"input_data too large ({size} bytes), max 10KB allowed")
        return v


class TaskState(str):
    PENDING = "PENDING"
    ROUTING = "ROUTING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    task_id: str
    client_id: str
    task_type: str
    capability_required: str
    status: str  # Changed from 'state' to 'status'
    priority: int
    created_at: datetime
    updated_at: datetime
    assigned_agent_id: Optional[str] = None
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class TaskUpdateState(BaseModel):
    status: str  # Changed from 'state' to 'status'
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class TaskSubmission(BaseModel):
    """Schema for task submission"""
    client_id: str
    task_type: str
    capability_required: str
    input_data: Dict[str, Any]
    priority: int = Field(default=5, ge=1, le=10)
    metadata: Optional[Dict[str, Any]] = None
    timeout_seconds: int = Field(default=300)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_policy: str = Field(default="exponential")  # ← ADD THIS LINE
    expires_at: Optional[str] = None

class TaskResponse(BaseModel):
    """Schema for task response"""
    task_id: str
    client_id: str
    task_type: str
    capability_required: str
    status: str
    priority: int
    assigned_agent_id: Optional[str] = None
    created_at: str
    updated_at: str
    assigned_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    
    class Config:
        from_attributes = True  # For Pydantic V2 (was orm_mode in V1)