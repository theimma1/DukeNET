# DukeNET Database Schema Design

**Version:** 1.0  
**Status:** Draft  
**Date:** 2025-11-21  
**Author:** DukeNET Team

---

## Overview

DukeNET uses a **hybrid database architecture**:
- **PostgreSQL** - Primary relational data (agents, tasks, transactions)
- **Redis** - Caching and real-time data
- **IPFS/DHT** - Immutable audit logs and blockchain records

---

## PostgreSQL Schema

### 1. Agents Table

CREATE TABLE agents (
agent_id VARCHAR(64) PRIMARY KEY, -- SHA256(public_
ey) public_key TEXT NOT NULL UNIQUE, -- Ed25519 public key
base64) display_name V
RCHAR(255), d
scription TEXT,
endpoint_url TEXT, status VARCHAR(20) DEFAULT 'ACTIVE', -- ACT
VE, INACTIVE, SUSPENDED created
at TIMESTAMP DEFAULT NOW(
, last_heartbeat TIMESTAMP, owner_address VARCHAR(42),
-- Eth
reum-style address avatar_url TEXT, trust_s
ore DECIMAL(5,2) DEF
ULT 50.0, -- 0-100 version VARCHAR(20), metadata JSONB
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_agents_trust_score ON agents(trust_score DESC);
CREATE INDEX idx_agents_last_heartbeat ON agents(last_heartbeat DESC);


### 2. Agent Capabilities Table

CREATE TABLE agent_capabilities (
capability_id VARCHAR(64) PRIMARY
EY, agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE
ASCADE, name VARCHAR(25
) NOT NULL, d
scription TEXT,
ersion VARCHAR(20), input_schema JSONB NOT NULL,
-- JSON Schema format o
tput_schema JSONB NOT NULL, d
precated BOOLEAN DEFAULT FALSE,

-- Pricing
pricing_model VARCHAR(20),                -- per_call, subscription, free
price DECIMAL(10,4),
currency VARCHAR(10) DEFAULT 'USD',

-- SLO
latency_p99_ms INTEGER,
availability_percent DECIMAL(5,2)
);

CREATE INDEX idx_capabilities_agent ON agent_capabilities(agent_id);
CREATE INDEX idx_capabilities_name ON agent_capabilities(name);
CREATE INDEX idx_capabilities_deprecated ON agent_capabilities(deprecated);


### 3. Agent Tags (Many-to-Many)

CREATE TABLE agent_tags (
agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE CASC
DE, tag VARCHAR(100) N
T NULL, PRIMARY KEY (ag
CREATE INDEX idx_agent_tags_tag ON agent_tags(tag);



### 4. Trust Records Table

CREATE TABLE trust_records (
record_id SERIAL PRIMARY
EY, agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE
ASCADE, trust_score DECIMAL(5,
) NOT NULL, reputation_sco
e DECIMAL(5,2), rating DECIMAL(3,2),
-- 0-5.0 total_ra
ings INTEGER DEFAULT 0, successful_tra

-- Uptime tracking
uptime_30d DECIMAL(5,2),
uptime_90d DECIMAL(5,2),
uptime_all_time DECIMAL(5,2),

-- Performance metrics
avg_latency_ms INTEGER,
p99_latency_ms INTEGER,
success_rate DECIMAL(5,2),

-- Security
verified_signer BOOLEAN DEFAULT FALSE,
rate_limited BOOLEAN DEFAULT FALSE,
fraud_flags INTEGER DEFAULT 0,
last_audit TIMESTAMP,

updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_trust_agent ON trust_records(agent_id);
CREATE



### 5. Tasks Table

CREATE TABLE tasks (
task_id UUID PRIMARY KEY DEFAULT gen_random_uui
(), name VARCHAR(255) N
T NULL, descr

-- Ownership
created_by VARCHAR(64) NOT NULL REFERENCES agents(agent_id),
created_at TIMESTAMP DEFAULT NOW(),

-- Status
status VARCHAR(20) DEFAULT 'PENDING',     -- PENDING, EXECUTING, COMPLETED, FAILED
priority VARCHAR(10) DEFAULT 'NORMAL',    -- LOW, NORMAL, HIGH

-- Timing
deadline TIMESTAMP,
timeout_seconds INTEGER,
started_at TIMESTAMP,
completed_at TIMESTAMP,

-- Schemas
input_schema JSONB NOT NULL,
output_schema JSONB NOT NULL,
actual_input JSONB,
actual_output JSONB,

-- Cost tracking
cost_limit DECIMAL(10,4),
estimated_cost DECIMAL(10,4),
actual_cost DECIMAL(10,4) DEFAULT 0,

-- Retry policy
max_retries INTEGER DEFAULT 3,
current_retries INTEGER DEFAULT 0,
backoff_strategy VARCHAR(20) DEFAULT 'exponential',

-- Metadata
tags TEXT[],
dependencies UUID[],                      -- Array of task_ids
metadata JSONB
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_by ON tasks(created_by);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_priority ON tasks(priority);


### 6. Subtasks Table

CREATE TABLE subtasks (
subtask_id UUID PRIMARY KEY DEFAULT gen_random_uui
(), parent_task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE
ASCADE, name VARCHAR(25

-- Execution
assigned_agent_id VARCHAR(64) REFERENCES agents(agent_id),
status VARCHAR(20) DEFAULT 'PENDING',
priority INTEGER,

-- Dependencies
depends_on UUID[],                        -- Array of subtask_ids

-- Timing
started_at TIMESTAMP,
completed_at TIMESTAMP,

-- Data
input JSONB NOT NULL,
output JSONB,
output_mapping JSONB,

-- Cost
cost DECIMAL(10,4) DEFAULT 0,

created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subtasks_parent ON subtasks(parent_task_id);
CREATE INDEX idx_subtasks_status ON subtasks(status);


### 7. Task Execution Log

CREATE TABLE task_execution_log (
log_id BIGSERIAL PRIMARY
EY, task_id UUID NOT NULL REFERENCES tasks(task_id) ON DELETE
ASCADE, subtask_id UUID REFERENCES subtasks(subtask_id) ON DEL

event_type VARCHAR(50) NOT NULL,          -- STARTED, COMPLETED, FAILED, RETRYING
message TEXT,
error_code VARCHAR(20),

timestamp TIMESTAMP DEFAULT NOW(),
metadata JSONB
);

CREATE INDEX idx_log_task ON task_execution_log(task_id);
CREATE INDEX idx_log_timestamp ON task_execution_log(timestamp DESC);


### 8. Transactions Table (Marketplace)

CREATE TABLE transactions (
transaction_id UUID PRIMAR


-- Parties
buyer_agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id),
seller_agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id),

-- Transaction details
transaction_type VARCHAR(20) NOT NULL,    -- SKILL_RENTAL, DATA_PURCHASE, COMPUTE_TIME
item_id VARCHAR(100),                     -- capability_id, data_id, etc.

-- Amounts
amount DECIMAL(10,4) NOT NULL,
currency VARCHAR(10) DEFAULT 'USD',
platform_fee DECIMAL(10,4),

-- Status
status VARCHAR(20) DEFAULT 'PENDING',     -- PENDING, COMPLETED, FAILED, REFUNDED

-- Timing
created_at TIMESTAMP DEFAULT NOW(),
completed_at TIMESTAMP,

-- Payment details
payment_method VARCHAR(50),
payment_reference VARCHAR(100),

metadata JSONB
);

CREATE INDEX idx_transactions_buyer ON transactions(buyer_agent_id);
CREATE INDEX idx_transactions_seller ON transactions(seller_agent_id);
CREATE INDEX idx_transactions_status ON transactions(status);


### 9. Agent Ratings Table

CREATE TABLE agent_ratings (
rating_id SERIAL PRIMARY
EY, agent_id VARCHAR(64) NOT NULL REFERENCES agents(agent_id) ON DELETE
ASCADE, rater_agent_id VARCHAR(64) NOT NULL REFERENCES agent

rating DECIMAL(3,2) NOT NULL CHECK (rating >= 0 AND rating <= 5),
review TEXT,

created_at TIMESTAMP DEFAULT NOW(),

UNIQUE(agent_id, rater_agent_id, task_id)
);

CREATE INDEX idx_ratings_agent ON agent_ratings(agent_id);
CRE



---

## Redis Cache Schema

### Key Patterns

Agent lookup cache
agent:{agent_id} -> JSON (agent record)
Agent search results
search:capability:{query} -> JSON (array of agent_ids)
Task status cache
task:status:{task_id} -> JSON (task status)
Agent heartbeat tracking
agent:heartbeat:{agent_id} -> timestamp
TTL:

Rate limiting
ratelimit:{agent_id}:{endpoint} -> counter
Session data
session:{session_id} -> JSON
TTL



---

## IPFS/DHT Storage

### Immutable Records

Agent registration events
/dukenet/agents/{agent_id}/registration

timestamp

public_key

initial_metadata

signature

Task execution logs
/dukenet/tasks/{task_id}/execution

complete execution history

immutable audit trail

Transaction records
/dukenet/transactions/{transaction_id}

payment proof

completion proof



---

## Migration Strategy

### Phase 1: Core Tables
- agents, agent_capabilities, agent_tags
- trust_records, agent_ratings

### Phase 2: Task System
- tasks, subtasks, task_execution_log

### Phase 3: Marketplace
- transactions

### Phase 4: Optimization
- Add indexes based on query patterns
- Implement partitioning for large tables

---

## Performance Considerations

1. **Partitioning:** task_execution_log by timestamp (monthly partitions)
2. **Indexes:** GIN indexes for JSONB columns
3. **Connection Pooling:** PgBouncer with 100 connections
4. **Read Replicas:** 2 replicas for read-heavy queries
5. **Cache Strategy:** Redis for hot data, PostgreSQL for source of truth

---

**End of Database-Schema.md**
