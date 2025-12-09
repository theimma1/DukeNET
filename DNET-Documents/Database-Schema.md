# Database Schema Documentation

**Version:** 1.0.0  
**Database:** SQLite (development) / PostgreSQL (production)  
**Last Updated:** November 23, 2025

---

## Table of Contents

1. [Schema Overview](#schema-overview)
2. [Core Tables](#core-tables)
3. [Advanced Feature Tables](#advanced-feature-tables)
4. [Security Tables](#security-tables)
5. [Relationships](#relationships)
6. [Indexes](#indexes)
7. [Constraints](#constraints)
8. [Migration History](#migration-history)

---

## Schema Overview

### Table Categories

**Core Tables (Sprints 1-3):**
- `agents` - Registered agents in the network
- `tasks` - Task submissions and lifecycle
- `agent_tags` - Agent categorization
- `agent_capabilities` - Detailed capability definitions

**Advanced Features (Sprint 7):**
- `task_chains` - Sequential workflow execution
- `scheduled_tasks` - Cron-based task automation
- `task_templates` - Reusable task configurations

**Security & Trust (Sprints 5-6):**
- `api_keys` - Client authentication
- `rate_limit_tracker` - Rate limiting enforcement
- `audit_logs` - Security event tracking
- `trust_records` - Trust score audit trail

**Integration:**
- `webhooks` - Webhook registrations
- `webhook_deliveries` - Delivery tracking

---

## Core Tables

### agents

Stores registered agents and their metadata.

CREATE TABLE agents (
id INTEGER PRIMARY KEY AUTOINCREMENT,
agent_id VARCHAR(64) UNIQUE NOT NULL,
display_name VARCHAR(255) NOT NULL,
public_key TEXT NOT NULL,
endpoint VARCHAR(512) NOT NULL,
signature TEXT NOT NULL,
tags JSON DEFAULT '[]',


-- Trust and performance metrics
trust_score FLOAT DEFAULT 0.5,
total_tasks_completed INTEGER DEFAULT 0,
total_tasks_failed INTEGER DEFAULT 0,
avg_completion_time_seconds FLOAT,

-- Timestamps
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE,
last_seen_at TIMESTAMP WITH TIME ZONE,
last_task_completed_at TIMESTAMP WITH TIME ZONE,

-- Sprint 7: Routing
last_assigned_at TIMESTAMP WITH TIME ZONE,

INDEX idx_agent_id (agent_id),
INDEX idx_agent_tags USING GIN (tags)  -- PostgreSQL only
);



**Fields:**

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| `id` | INTEGER | Internal primary key | AUTO_INCREMENT |
| `agent_id` | VARCHAR(64) | External agent identifier | UNIQUE, NOT NULL |
| `display_name` | VARCHAR(255) | Human-readable name | NOT NULL |
| `public_key` | TEXT | Agent's public key for verification | NOT NULL |
| `endpoint` | VARCHAR(512) | Agent's webhook/task endpoint | NOT NULL |
| `signature` | TEXT | Registration signature | NOT NULL |
| `tags` | JSON | Capability tags (e.g., ["data:v1"]) | DEFAULT [] |
| `trust_score` | FLOAT | Reputation score (0.0-1.0) | DEFAULT 0.5 |
| `total_tasks_completed` | INTEGER | Successful task count | DEFAULT 0 |
| `total_tasks_failed` | INTEGER | Failed task count | DEFAULT 0 |
| `avg_completion_time_seconds` | FLOAT | Average task duration | NULL |
| `last_assigned_at` | TIMESTAMP | Last task assignment time | NULL |

**Sample Data:**
{
"agent_id": "agent_001",
"display_name": "Data Processor Alpha",
"tags": ["data:v1", "ml:v1", "image:v1"],
"trust_score": 0.85,
"total_tasks_completed": 247,
"total_tasks_failed": 12,
"avg_completion_time_seconds": 45.3
}



---

### tasks

Stores all task submissions and their lifecycle state.

CREATE TABLE tasks (
task_id VARCHAR(64) PRIMARY KEY,
client_id VARCHAR(64) NOT NULL,
priority INTEGER DEFAULT 5,


-- Task type and metadata
task_type VARCHAR(100) NOT NULL,
capability_required VARCHAR(255) NOT NULL,
input_data JSON NOT NULL,
task_metadata JSON,

-- Lifecycle
status VARCHAR(20) DEFAULT 'PENDING' NOT NULL,
assigned_agent_id VARCHAR(64),
assigned_at TIMESTAMP WITH TIME ZONE,
started_at TIMESTAMP WITH TIME ZONE,
completed_at TIMESTAMP WITH TIME ZONE,

-- Results
result_data JSON,
error_message TEXT,

-- Retry and failure handling
max_retries INTEGER DEFAULT 3,
retry_count INTEGER DEFAULT 0,
next_retry_at TIMESTAMP WITH TIME ZONE,
retry_policy VARCHAR(50) DEFAULT 'exponential',
last_error TEXT,

-- Timestamps
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE,
expires_at TIMESTAMP WITH TIME ZONE,

-- Timeout and cancellation
timeout_seconds INTEGER,
cancelled_at TIMESTAMP WITH TIME ZONE,
cancelled_by VARCHAR(255),
cancellation_reason TEXT,

-- Sprint 7: Advanced Features
depends_on JSON DEFAULT '[]',
blocked_by JSON DEFAULT '[]',
is_blocked BOOLEAN DEFAULT FALSE,
routing_strategy VARCHAR(64) DEFAULT 'round_robin',
chain_id VARCHAR(64),
template_id VARCHAR(64),

FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id),
FOREIGN KEY (chain_id) REFERENCES task_chains(chain_id),
FOREIGN KEY (template_id) REFERENCES task_templates(template_id),

INDEX idx_task_status (status),
INDEX idx_task_status_priority (status, priority DESC),
INDEX idx_task_client (client_id),
INDEX idx_task_assigned_agent (assigned_agent_id),
INDEX idx_task_chain (chain_id),
INDEX idx_task_created (created_at DESC),
INDEX idx_task_depends_on USING GIN (depends_on)
);


**Status Values:**
- `PENDING` - Task submitted, awaiting assignment
- `ASSIGNED` - Assigned to agent, not started
- `RUNNING` - Agent executing task
- `COMPLETED` - Task finished successfully
- `FAILED` - Task execution failed
- `CANCELLED` - Task cancelled by user
- `TIMEOUT` - Task exceeded time limit

**Sample Data:**
{
"task_id": "task_abc123",
"client_id": "my_app",
"task_type": "data_analysis",
"capability_required": "data:v1",
"status": "COMPLETED",
"priority": 7,
"input_data": {
"file_url": "https://storage.example.com/data.csv",
"algorithm": "regression"
},
"result_data": {
"model_accuracy": 0.94,
"predictions_url": "https://storage.example.com/results.json"
},
"depends_on": ["task_xyz789"],
"routing_strategy": "trust_weighted",
"created_at": "2025-11-23T14:10:00Z",
"completed_at": "2025-11-23T14:12:30Z"
}



---

### agent_capabilities

Detailed capability definitions (optional, for enhanced discovery).

CREATE TABLE agent_capabilities (
capability_id VARCHAR(64) PRIMARY KEY,
agent_id VARCHAR(64) NOT NULL,
name VARCHAR(255) NOT NULL,
description TEXT,
version VARCHAR(20),


-- Schemas
input_schema JSON NOT NULL,
output_schema JSON NOT NULL,

-- Pricing
pricing_model VARCHAR(20),
price DECIMAL(10, 4),
currency VARCHAR(10) DEFAULT 'USD',

-- SLO
latency_p99_ms INTEGER,
availability_percent DECIMAL(5, 2),

deprecated BOOLEAN DEFAULT FALSE,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE,

FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
INDEX idx_capability_agent (agent_id),
INDEX idx_capability_name (name)
);



---

## Advanced Feature Tables

### task_chains

Sequential workflow execution chains.

CREATE TABLE task_chains (
id INTEGER PRIMARY KEY AUTOINCREMENT,
chain_id VARCHAR(64) UNIQUE NOT NULL,
name VARCHAR(255) NOT NULL,
client_id VARCHAR(64) NOT NULL,


-- Chain definition
steps JSON NOT NULL,
current_step INTEGER DEFAULT 0,

-- Status
status VARCHAR(32) DEFAULT 'PENDING',
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
started_at TIMESTAMP WITH TIME ZONE,
completed_at TIMESTAMP WITH TIME ZONE,

-- Results
step_results JSON DEFAULT '{}',
final_result JSON,
error_message VARCHAR(512),

INDEX idx_task_chains_client_id (client_id),
INDEX idx_task_chains_status (status),
INDEX idx_task_chains_created (created_at DESC)
);



**Steps Format:**
[
{
"name": "fetch_data",
"task_type": "fetch",
"capability_required": "api:v1",
"input_data": {"source": "database"}
},
{
"name": "process_data",
"task_type": "process",
"capability_required": "data:v1",
"use_previous_output": true
}
]



**Status Values:**
- `PENDING` - Chain created, not started
- `RUNNING` - Executing steps
- `COMPLETED` - All steps finished
- `FAILED` - A step failed
- `CANCELLED` - Chain cancelled

---

### scheduled_tasks

Cron-based task automation.

CREATE TABLE scheduled_tasks (
id INTEGER PRIMARY KEY AUTOINCREMENT,
schedule_id VARCHAR(64) UNIQUE NOT NULL,
name VARCHAR(255) NOT NULL,
client_id VARCHAR(64) NOT NULL,


-- Schedule configuration
cron_expression VARCHAR(128) NOT NULL,
timezone VARCHAR(64) DEFAULT 'UTC',

-- Task template
task_type VARCHAR(128) NOT NULL,
capability_required VARCHAR(256) NOT NULL,
input_data JSON NOT NULL,
priority INTEGER DEFAULT 5,
timeout_seconds INTEGER DEFAULT 300,

-- Status
active BOOLEAN DEFAULT TRUE,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
last_run_at TIMESTAMP WITH TIME ZONE,
next_run_at TIMESTAMP WITH TIME ZONE,

-- Statistics
total_runs INTEGER DEFAULT 0,
successful_runs INTEGER DEFAULT 0,
failed_runs INTEGER DEFAULT 0,

INDEX idx_scheduled_tasks_client_id (client_id),
INDEX idx_scheduled_tasks_active (active),
INDEX idx_scheduled_tasks_next_run (next_run_at)
);



**Cron Expression Examples:**
*/5 * * * * - Every 5 minutes
0 */2 * * * - Every 2 hours
0 9 * * 1-5 - 9 AM on weekdays
0 0 1 * * - First day of month at midnight



---

### task_templates

Reusable task configurations.

CREATE TABLE task_templates (
id INTEGER PRIMARY KEY AUTOINCREMENT,
template_id VARCHAR(64) UNIQUE NOT NULL,
name VARCHAR(255) NOT NULL,
description VARCHAR(512),
client_id VARCHAR(64) NOT NULL,


-- Template configuration
task_type VARCHAR(128) NOT NULL,
capability_required VARCHAR(256) NOT NULL,
default_input_data JSON NOT NULL,
default_priority INTEGER DEFAULT 5,
default_timeout INTEGER DEFAULT 300,
default_max_retries INTEGER DEFAULT 3,

-- Usage tracking
times_used INTEGER DEFAULT 0,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP WITH TIME ZONE,

INDEX idx_task_templates_client_id (client_id),
INDEX idx_task_templates_name (name)
);


---

## Security Tables

### api_keys

Client authentication keys.

CREATE TABLE api_keys (
id INTEGER PRIMARY KEY AUTOINCREMENT,
key_id VARCHAR(64) UNIQUE NOT NULL,
key_hash VARCHAR(128) NOT NULL,
client_id VARCHAR(64) NOT NULL,
name VARCHAR(255) NOT NULL,
scopes JSON DEFAULT '[]',


-- Status and lifecycle
active BOOLEAN DEFAULT TRUE NOT NULL,
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
expires_at TIMESTAMP WITH TIME ZONE,
last_used_at TIMESTAMP WITH TIME ZONE,

-- Rate limiting
rate_limit_per_minute INTEGER DEFAULT 60,
rate_limit_per_hour INTEGER DEFAULT 1000,

-- Metadata
created_by VARCHAR(64),
description VARCHAR(512),

INDEX idx_api_keys_key_id (key_id),
INDEX idx_api_keys_client_active (client_id, active),
UNIQUE INDEX idx_api_keys_hash (key_hash)
);


**Key Format:** `ains_{44_character_base64_token}`

---

### rate_limit_tracker

Track API usage for rate limiting.

CREATE TABLE rate_limit_tracker (
id INTEGER PRIMARY KEY AUTOINCREMENT,
key_id VARCHAR(64) NOT NULL,
window_start TIMESTAMP WITH TIME ZONE NOT NULL,
window_type VARCHAR(20) NOT NULL,
request_count INTEGER DEFAULT 0,


FOREIGN KEY (key_id) REFERENCES api_keys(key_id) ON DELETE CASCADE,
INDEX idx_rate_limit_key_window (key_id, window_start, window_type),
UNIQUE INDEX idx_rate_limit_unique (key_id, window_start, window_type)
);



**Window Types:**
- `minute` - Per-minute tracking
- `hour` - Per-hour tracking

---

### audit_logs

Security event tracking.

CREATE TABLE audit_logs (
id INTEGER PRIMARY KEY AUTOINCREMENT,
event_type VARCHAR(64) NOT NULL,
client_id VARCHAR(64),
key_id VARCHAR(64),


-- Event details
action VARCHAR(128) NOT NULL,
resource_type VARCHAR(64),
resource_id VARCHAR(128),

-- Request context
ip_address VARCHAR(45),
user_agent VARCHAR(512),

-- Result
success BOOLEAN NOT NULL,
error_message VARCHAR(512),

-- Additional data
extra_metadata JSON DEFAULT '{}',
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

INDEX idx_audit_logs_created (created_at DESC),
INDEX idx_audit_logs_client_event (client_id, event_type),
INDEX idx_audit_logs_event_type (event_type)
);



**Event Types:**
- `authentication` - Login attempts
- `api_key_created` - New API key
- `api_key_revoked` - Key deletion
- `rate_limit_exceeded` - Rate limit hit
- `task_created` - Task submission
- `agent_registered` - Agent registration

---

### trust_records

Trust score change audit trail.

CREATE TABLE trust_records (
id INTEGER PRIMARY KEY AUTOINCREMENT,
record_id VARCHAR(64) UNIQUE NOT NULL,
agent_id VARCHAR(64) NOT NULL,
event_type VARCHAR(64) NOT NULL,
task_id VARCHAR(64),


trust_delta FLOAT NOT NULL,
trust_score_before FLOAT NOT NULL,
trust_score_after FLOAT NOT NULL,
reason VARCHAR(512),
created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
INDEX idx_trust_records_agent (agent_id),
INDEX idx_trust_records_agent_date (agent_id, created_at DESC)
);



**Event Types:**
- `task_completed` - Successful task
- `task_failed` - Failed task
- `task_timeout` - Task timeout
- `manual_adjustment` - Admin adjustment

---

## Relationships

### Entity Relationship Diagram

agents (1) ──< (N) tasks
│ │
│ │
└──< (N) trust_records

tasks (N) ──> (1) task_chains
tasks (N) ──> (1) task_templates

api_keys (1) ──< (N) rate_limit_tracker
api_keys (1) ──< (N) audit_logs

agents (1) ──< (N) webhooks
webhooks (1) ──< (N) webhook_deliveries


---

## Indexes

### Performance-Critical Indexes

**Agent Queries:**
CREATE INDEX idx_agent_id ON agents(agent_id);
CREATE INDEX idx_agent_tags ON agents USING GIN(tags); -- PostgreSQL
CREATE INDEX idx_agent_trust ON agents(trust_score DESC);



**Task Queries:**
CREATE INDEX idx_task_status_priority ON tasks(status, priority DESC);
CREATE INDEX idx_task_client ON tasks(client_id, created_at DESC);
CREATE INDEX idx_task_assigned_agent ON tasks(assigned_agent_id);
CREATE INDEX idx_task_depends_on ON tasks USING GIN(depends_on);
CREATE INDEX idx_task_created ON tasks(created_at DESC);



**Security Queries:**
CREATE INDEX idx_api_key_hash ON api_keys(key_hash);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX idx_rate_limit_key_window ON rate_limit_tracker(key_id, window_start, window_type);



**Scheduled Tasks:**
CREATE INDEX idx_scheduled_next_run ON scheduled_tasks(active, next_run_at);



---

## Constraints

### Foreign Key Constraints

-- Tasks reference agents
ALTER TABLE tasks
ADD CONSTRAINT fk_tasks_agent
FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id);

-- Tasks reference chains
ALTER TABLE tasks
ADD CONSTRAINT fk_tasks_chain
FOREIGN KEY (chain_id) REFERENCES task_chains(chain_id);

-- Tasks reference templates
ALTER TABLE tasks
ADD CONSTRAINT fk_tasks_template
FOREIGN KEY (template_id) REFERENCES task_templates(template_id);

-- Trust records reference agents
ALTER TABLE trust_records
ADD CONSTRAINT fk_trust_agent
FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE;



### Check Constraints

-- Trust score bounds
ALTER TABLE agents
ADD CONSTRAINT chk_trust_score
CHECK (trust_score >= 0.0 AND trust_score <= 1.0);

-- Priority bounds
ALTER TABLE tasks
ADD CONSTRAINT chk_priority
CHECK (priority >= 1 AND priority <= 10);

-- Valid status values
ALTER TABLE tasks
ADD CONSTRAINT chk_status
CHECK (status IN ('PENDING', 'ASSIGNED', 'RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED', 'TIMEOUT'));



---

## Migration History

### Sprint 1-3: Core Tables
- Created `agents`, `tasks`, `agent_tags`, `agent_capabilities`
- Basic indexes for performance

### Sprint 4: Reliability
- Added retry fields to `tasks`
- Created `webhooks` and `webhook_deliveries`

### Sprint 5: Trust System
- Added trust fields to `agents`
- Created `trust_records` table

### Sprint 6: Security
- Created `api_keys`, `rate_limit_tracker`, `audit_logs`
- Added security indexes

### Sprint 7: Advanced Features
- Created `task_chains`, `scheduled_tasks`, `task_templates`
- Added dependency fields to `tasks`
- Added `last_assigned_at` to `agents`

---

**[Back to Architecture →](./README.md)**