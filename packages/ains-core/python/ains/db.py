"""AINS Database Models"""
import os
from datetime import datetime, timezone
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Index

from sqlalchemy import (
    create_engine, Column, String, DateTime, Integer, Boolean, 
    DECIMAL, Text, ForeignKey, JSON, Float, Index, func
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ains.db")

Base = declarative_base()

# Database connection - use SQLite for tests, PostgreSQL for production
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ains.db"  # SQLite for local development/testing
)

# Create engine
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Helper function for timezone-aware datetime defaults
def utc_now():
    """Return current UTC time with timezone awareness"""
    return datetime.now(timezone.utc)

class Agent(Base):
    """Registered agents"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    public_key = Column(String, nullable=False)
    endpoint = Column(String(512), nullable=False)
    signature = Column(String, nullable=False)
    tags = Column(JSON, default=list)
    
    # ✅ ADDED: Agent status field
    status = Column(String(32), default="AVAILABLE", nullable=False)
    
    # ✅ ADDED: Heartbeat timestamp
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    
    # Trust and performance metrics
    trust_score = Column(Float, default=0.5)
    total_tasks_completed = Column(Integer, default=0)
    total_tasks_failed = Column(Integer, default=0)
    avg_completion_time_seconds = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_task_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Sprint 7: Routing field
    last_assigned_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships - FIXED
    assigned_tasks = relationship("Task", back_populates="assigned_agent")
    capabilities = relationship("Capability", back_populates="agent")
    trust_records = relationship("TrustRecord", back_populates="agent")

class AgentTag(Base):
    """Agent tags for categorization"""
    __tablename__ = "agent_tags"
    
    agent_id = Column(String(64), ForeignKey("agents.agent_id"), primary_key=True)
    tag = Column(String(100), primary_key=True)

class Capability(Base):
    """Agent capabilities"""
    __tablename__ = "agent_capabilities"
    
    capability_id = Column(String(64), primary_key=True)
    agent_id = Column(String(64), ForeignKey("agents.agent_id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    version = Column(String(20))
    
    # Schemas as JSON
    input_schema = Column(JSON, nullable=False)
    output_schema = Column(JSON, nullable=False)
    
    # Pricing
    pricing_model = Column(String(20))
    price = Column(DECIMAL(10, 4))
    currency = Column(String(10), default='USD')
    
    # SLO
    latency_p99_ms = Column(Integer)
    availability_percent = Column(DECIMAL(5, 2))
    
    deprecated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relationships
    agent = relationship("Agent", back_populates="capabilities")

class Task(Base):
    """AI Task Protocol (AITP) tasks"""
    __tablename__ = "tasks"
    
    task_id = Column(String(64), primary_key=True)
    client_id = Column(String(64), nullable=False)
    priority = Column(Integer, default=5)
    
    # Task type and metadata
    task_type = Column(String(100), nullable=False)
    capability_required = Column(String(255), nullable=False)
    
    # Task data
    input_data = Column(JSON, nullable=False)
    task_metadata = Column(JSON)
    
    # Lifecycle status
    status = Column(String(20), default='PENDING', nullable=False)
    
    # Assignment and execution
    assigned_agent_id = Column(String(64), ForeignKey("agents.agent_id"))
    assigned_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    result_data = Column(JSON)
    error_message = Column(Text)
    
    # Retry and failure handling
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    retry_policy = Column(String, default="exponential")
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    expires_at = Column(DateTime)
    
    # Timeout and cancellation fields
    timeout_seconds = Column(Integer, nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(String, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    
    # Sprint 7: Advanced Features fields
    depends_on = Column(JSON, default=list)
    blocked_by = Column(JSON, default=list)
    is_blocked = Column(Boolean, default=False)
    routing_strategy = Column(String(64), default="round_robin")
    chain_id = Column(String(64), nullable=True)
    template_id = Column(String(64), nullable=True)
    
    # Relationships
    assigned_agent = relationship("Agent", back_populates="assigned_tasks")

class Webhook(Base):
    __tablename__ = "webhooks"
    
    webhook_id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False)
    url = Column(String, nullable=False)
    events = Column(String, nullable=False)
    secret = Column(String, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    
    delivery_id = Column(String, primary_key=True)
    webhook_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(String, nullable=False)
    status = Column(String, nullable=False)
    response_code = Column(Integer, nullable=True)
    response_body = Column(String, nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)

class TrustRecord(Base):
    """Audit trail for trust score changes"""
    __tablename__ = "trust_records"
    
    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(String, unique=True, nullable=False, index=True)
    agent_id = Column(String, ForeignKey("agents.agent_id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    task_id = Column(String, nullable=True)
    trust_delta = Column(Float, nullable=False)
    trust_score_before = Column(Float, nullable=False)
    trust_score_after = Column(Float, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    agent = relationship("Agent", back_populates="trust_records")

class APIKey(Base):
    """API keys for client authentication"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(64), unique=True, nullable=False, index=True)
    key_hash = Column(String(128), nullable=False)
    client_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    scopes = Column(JSON, default=list)
    
    # Status and lifecycle
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Metadata
    created_by = Column(String(64), nullable=True)
    description = Column(String(512), nullable=True)
    
    __table_args__ = (
        Index('idx_api_keys_client_active', 'client_id', 'active'),
        Index('idx_api_keys_key_id', 'key_id'),
    )

class RateLimitTracker(Base):
    """Track API usage for rate limiting"""
    __tablename__ = "rate_limit_tracker"
    
    id = Column(Integer, primary_key=True, index=True)
    key_id = Column(String(64), ForeignKey("api_keys.key_id"), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_type = Column(String(20), nullable=False)
    request_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_rate_limit_key_window', 'key_id', 'window_start', 'window_type'),
    )

class AuditLog(Base):
    """Security audit log"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    client_id = Column(String(64), nullable=True, index=True)
    key_id = Column(String(64), nullable=True)
    
    # Event details
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(128), nullable=True)
    
    # Request context
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    
    # Result
    success = Column(Boolean, nullable=False)
    error_message = Column(String(512), nullable=True)
    
    # Additional data
    extra_task_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_audit_logs_created', 'created_at'),
        Index('idx_audit_logs_client_event', 'client_id', 'event_type'),
    )

class TaskChain(Base):
    """Task chains for sequential workflow execution"""
    __tablename__ = "task_chains"
    
    id = Column(Integer, primary_key=True, index=True)
    chain_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    client_id = Column(String(64), nullable=False, index=True)
    
    # Chain definition
    steps = Column(JSON, nullable=False)
    current_step = Column(Integer, default=0)
    
    # Status
    status = Column(String(32), default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    step_results = Column(JSON, default=dict)
    final_result = Column(JSON, nullable=True)
    error_message = Column(String(512), nullable=True)
    
    __table_args__ = (
        Index('idx_task_chains_client_id', 'client_id'),
        Index('idx_task_chains_status', 'status'),
    )

class ScheduledTask(Base):
    """
    Unified Task/ScheduledTask model
    This model serves BOTH regular tasks and scheduled tasks
    """
    __tablename__ = "scheduled_tasks"
    
    # Core task fields
    task_id = Column(String, primary_key=True)  # Used as both task_id and schedule_id
    schedule_id = Column(String, index=True, nullable=True)  # For scheduled tasks
    client_id = Column(String, nullable=False, index=True)
    task_type = Column(String, nullable=False)
    capability_required = Column(String, nullable=False)
    input_data = Column(JSON, nullable=False)
    priority = Column(Integer, default=5)
    
    # Status fields
    status = Column(String, default='PENDING', index=True)  # PENDING, ASSIGNED, ACTIVE, COMPLETED, FAILED, CANCELLED
    
    # Assignment fields
    assigned_agent_id = Column(String, nullable=True, index=True)
    assigned_at = Column(DateTime, nullable=True)
    
    # Execution timing
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Results and errors
    result_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Retry logic
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    retry_policy = Column(String, default='exponential')
    next_retry_at = Column(DateTime, nullable=True)
    
    # Timeout
    timeout_seconds = Column(Integer, default=300)
    
    # Dependencies
    depends_on = Column(JSON, nullable=True)  # List of task_ids
    is_blocked = Column(Boolean, default=False)
    
    # Routing
    routing_strategy = Column(String, default='round_robin')
    
    # Chain support
    chain_id = Column(String, nullable=True, index=True)
    
    # Expiration
    expires_at = Column(DateTime, nullable=True)
    
    # Scheduling-specific fields (only populated for scheduled tasks)
    cron_expression = Column(String, nullable=True)
    timezone = Column(String, default='UTC')
    next_run_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True)
    total_runs = Column(Integer, default=0)
    successful_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    
    # Metadata
    task_metadata = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<Task(task_id='{self.task_id}', status='{self.status}', type='{self.task_type}')>"

Task = ScheduledTask
class TaskTemplate(Base):
    """Reusable task templates"""
    __tablename__ = "task_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(512), nullable=True)
    client_id = Column(String(64), nullable=False, index=True)
    
    # Template configuration
    task_type = Column(String(128), nullable=False)
    capability_required = Column(String(256), nullable=False)
    default_input_data = Column(JSON, nullable=False)
    default_priority = Column(Integer, default=5)
    default_timeout = Column(Integer, default=300)
    default_max_retries = Column(Integer, default=3)
    
    # Usage tracking
    times_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_task_templates_client_id', 'client_id'),
    )

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
Database Models for Task Scheduling
Add these models to ains/db.py
Location: Reference for db.py additions
"""

Base = declarative_base()


# ============================================================================
# SCHEDULING MODELS (Added for Sprint 10)
# ============================================================================

class ScheduledTask(Base):
    """Scheduled recurring tasks"""
    __tablename__ = "scheduled_tasks"
    
    schedule_id = Column(String(64), primary_key=True)
    client_id = Column(String(64), nullable=False, index=True)  # Removed FK to avoid ordering issues
    task_type = Column(String(64), nullable=False)
    capability_required = Column(String(64), nullable=False)
    input_data = Column(JSON, nullable=False)
    priority = Column(Integer, default=5)
    cron_expression = Column(String(64), nullable=False)
    next_run_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="ACTIVE")
    total_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)


class ScheduleExecution(Base):
    """Execution records for scheduled tasks"""
    __tablename__ = "schedule_executions"
    
    execution_id = Column(String(64), primary_key=True)
    schedule_id = Column(String(64), nullable=False)
    task_id = Column(String(64), nullable=False)
    executed_at = Column(DateTime, nullable=False)
    status = Column(String(20), default="PENDING")
    result_data = Column(JSON, nullable=True)
    error_message = Column(String(512), nullable=True)


# ============================================================================
# SECURITY MODELS (API KEYS & AUDIT LOGS)
# ============================================================================

class APIKey(Base):
    """API keys for authentication"""
    __tablename__ = "api_keys"
    
    key_id = Column(String(64), primary_key=True)
    key_hash = Column(String(128), unique=True, nullable=False)
    client_id = Column(String(64), nullable=False, index=True)  # Removed FK to avoid ordering issues
    name = Column(String(255), nullable=False)
    description = Column(String(512), nullable=True)
    scopes = Column(JSON, default=[])
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(64), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    rate_limit_per_minute = Column(Integer, default=60)
    rate_limit_per_hour = Column(Integer, default=1000)
    
    __table_args__ = (
        Index("idx_api_keys_key_id", "key_id"),
        Index("idx_api_keys_client_active", "client_id", "active"),
    )


class RateLimitTracker(Base):
    """Rate limit tracking for API keys"""
    __tablename__ = "rate_limit_tracker"
    
    id = Column(Integer, primary_key=True)
    key_id = Column(String(64), ForeignKey("api_keys.key_id"), nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_type = Column(String(20), nullable=False)
    request_count = Column(Integer, default=0)
    
    __table_args__ = (
        Index("idx_rate_limit_key_window", "key_id", "window_start", "window_type"),
    )


class AuditLog(Base):
    """Security audit logs"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(64), nullable=False)
    client_id = Column(String(64), nullable=True, index=True)
    key_id = Column(String(64), nullable=True)
    action = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=True)
    resource_id = Column(String(128), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(String(512), nullable=True)
    extra_task_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False, index=True)
    
    __table_args__ = (
        Index("idx_audit_logs_created", "created_at"),
        Index("idx_audit_logs_client_event", "client_id", "event_type"),
    )

