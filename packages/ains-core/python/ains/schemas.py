from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


# ============================================================================
# AGENT SCHEMAS
# ============================================================================

class AgentRegistration(BaseModel):
    """Schema for agent registration"""
    agent_id: str = Field(..., max_length=128)
    display_name: str = Field(..., max_length=256)
    endpoint: str = Field(..., max_length=512)
    public_key: str = Field(..., max_length=256)
    signature: str = Field(..., max_length=512)
    tags: Optional[List[str]] = None


class AgentResponse(BaseModel):
    """Schema for agent response"""
    agent_id: str
    public_key: str
    display_name: str
    endpoint: str
    created_at: str
    trust_score: float
    tags: List[str] = []
    
    model_config = ConfigDict(from_attributes=True)




# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskCreate(BaseModel):
    client_id: str = Field(..., max_length=128)
    task_type: str = Field(..., max_length=128)
    capability_required: str = Field(..., max_length=256)
    input_data: Dict[str, Any]
    priority: int = Field(5, ge=0, le=10)

    @field_validator("input_data")
    @classmethod
    def validate_input_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError("input_data must be a dictionary")
        return v


class TaskState(str):
    """Task status constants"""
    PENDING = "PENDING"
    ROUTING = "ROUTING"
    ASSIGNED = "ASSIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    """Schema for task"""
    task_id: str
    client_id: str
    task_type: str
    capability_required: str
    status: str
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
    """Schema for task state update"""
    status: str
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
    retry_policy: str = Field(default="exponential")
    expires_at: Optional[str] = None

    @field_validator("input_data")
    @classmethod
    def validate_input_data(cls, v):
        if not isinstance(v, dict):
            raise ValueError("input_data must be a dictionary")
        return v


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
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# BATCH OPERATION SCHEMAS
# ============================================================================

class BatchTaskSubmission(BaseModel):
    """Schema for batch task submission"""
    tasks: List[TaskSubmission]
    
    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, v):
        if not v:
            raise ValueError("tasks list cannot be empty")
        if len(v) > 100:
            raise ValueError("Cannot submit more than 100 tasks at once")
        return v


class BatchTaskResponse(BaseModel):
    """Schema for batch task response"""
    submitted: List[TaskResponse]
    failed: List[Dict[str, Any]]


# ============================================================================
# WEBHOOK SCHEMAS
# ============================================================================

class WebhookCreate(BaseModel):
    """Schema for webhook creation"""
    url: str = Field(..., max_length=512)
    events: List[str]
    secret: Optional[str] = None
    
    @field_validator("events")
    @classmethod
    def validate_events(cls, v):
        valid_events = ["task.created", "task.assigned", "task.completed", "task.failed"]
        for event in v:
            if event not in valid_events:
                raise ValueError(f"Invalid event: {event}. Must be one of {valid_events}")
        return v


class WebhookResponse(BaseModel):
    """Schema for webhook response"""
    webhook_id: str
    agent_id: str
    url: str
    events: List[str]
    active: bool
    created_at: str
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# TRUST & REPUTATION SCHEMAS
# ============================================================================

class TrustAdjustment(BaseModel):
    """Schema for manual trust adjustment"""
    trust_delta: float = Field(..., ge=-1.0, le=1.0)
    reason: Optional[str] = None


class TrustMetrics(BaseModel):
    """Schema for trust metrics response"""
    agent_id: str
    trust_score: float
    total_tasks_completed: int
    total_tasks_failed: int
    success_rate: float
    avg_completion_time_seconds: Optional[float] = None
    last_task_completed_at: Optional[str] = None


class TrustHistoryRecord(BaseModel):
    """Schema for trust history record"""
    record_id: str
    event_type: str
    trust_delta: float
    trust_score_before: float
    trust_score_after: float
    reason: Optional[str] = None
    task_id: Optional[str] = None
    created_at: str


class LeaderboardEntry(BaseModel):
    """Schema for leaderboard entry"""
    agent_id: str
    display_name: str
    trust_score: float
    total_tasks_completed: int
    total_tasks_failed: int
    success_rate: float


class Leaderboard(BaseModel):
    """Schema for leaderboard response"""
    leaderboard: List[LeaderboardEntry]
