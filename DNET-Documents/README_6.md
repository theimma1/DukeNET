# DukeNet AINS API Reference

**Version:** 1.0.0  
**Base URL:** `https://api.dukenet.example.com`  
**Authentication:** API Key via X-API-Key header

---

## Overview

The DukeNet AINS API provides programmatic access to enterprise task orchestration, agent coordination, and workflow automation. This RESTful API uses standard HTTP methods, JSON payloads, and API key authentication.

### Key Features

- **RESTful Design** - Standard HTTP methods and status codes
- **JSON Payloads** - All requests and responses use JSON format
- **Comprehensive Error Handling** - Detailed error codes and messages
- **Rate Limiting** - Configurable limits with clear feedback
- **Pagination Support** - Efficient handling of large result sets
- **Webhook Integration** - Event-driven notifications with HMAC signatures

### Base URL

```
Production: https://api.dukenet.example.com
Development: http://localhost:8000
```

---

## Table of Contents

1. [Authentication](#authentication)
2. [Agent Management](#agent-management)
3. [Task Management](#task-management)
4. [Workflow Automation](#workflow-automation)
5. [Trust & Reputation](#trust--reputation)
6. [Security & Monitoring](#security--monitoring)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)

---

## Authentication

### Overview

All API requests require authentication using an API key passed in the `X-API-Key` header. API keys provide secure access control, rate limiting, and usage tracking.

### Header Format

```http
X-API-Key: ains_your_api_key_here
```

### Create API Key

Generate a new API key for application access.

**Endpoint:** `POST /ains/api-keys`

**Request Body:**
```json
{
  "client_id": "production_application",
  "name": "Production API Key",
  "scopes": ["tasks:write", "agents:read", "webhooks:manage"],
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 5000,
  "expires_at": "2026-12-31T23:59:59Z"
}
```

**Parameters:**
- `client_id` (required) - Unique identifier for your application
- `name` (required) - Descriptive name for the key
- `scopes` (optional) - Array of permission scopes
- `rate_limit_per_minute` (optional) - Per-minute request limit (default: 60)
- `rate_limit_per_hour` (optional) - Per-hour request limit (default: 1000)
- `expires_at` (optional) - ISO 8601 expiration timestamp

**Response:** `201 Created`
```json
{
  "key_id": "key_abc123def456",
  "api_key": "ains_veryLongSecureRandomStringThatIsOnlyShownOnce",
  "client_id": "production_application",
  "name": "Production API Key",
  "scopes": ["tasks:write", "agents:read", "webhooks:manage"],
  "rate_limit_per_minute": 100,
  "rate_limit_per_hour": 5000,
  "created_at": "2025-11-23T14:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

**Important:** The `api_key` value is only displayed once. Store it securely immediately.

### List API Keys

Retrieve all API keys for a client.

**Endpoint:** `GET /ains/api-keys?client_id=production_application&active_only=true`

**Query Parameters:**
- `client_id` (optional) - Filter by client identifier
- `active_only` (optional) - Return only active keys (default: false)

**Response:** `200 OK`
```json
{
  "keys": [
    {
      "key_id": "key_abc123def456",
      "client_id": "production_application",
      "name": "Production API Key",
      "active": true,
      "scopes": ["tasks:write", "agents:read"],
      "rate_limit_per_minute": 100,
      "rate_limit_per_hour": 5000,
      "last_used_at": "2025-11-23T14:00:00Z",
      "created_at": "2025-11-20T10:00:00Z",
      "expires_at": "2026-12-31T23:59:59Z"
    }
  ],
  "total": 1
}
```

### Revoke API Key

Permanently revoke an API key.

**Endpoint:** `DELETE /ains/api-keys/{key_id}`

**Response:** `200 OK`
```json
{
  "key_id": "key_abc123def456",
  "revoked_at": "2025-11-23T14:05:00Z",
  "message": "API key revoked successfully"
}
```

---

## Agent Management

### Register Agent

Register a new agent in the DukeNet network.

**Endpoint:** `POST /ains/agents`

**Request Body:**
```json
{
  "agent_id": "agent_data_processor_01",
  "display_name": "Data Processing Agent - Primary",
  "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG...\n-----END PUBLIC KEY-----",
  "endpoint": "https://agent.example.com/api/tasks",
  "signature": "base64_encoded_signature_of_registration_data",
  "tags": [
    "data-processing:v1",
    "ml-inference:v2",
    "batch-processing:v1"
  ],
  "metadata": {
    "region": "us-east-1",
    "instance_type": "compute-optimized",
    "max_concurrent_tasks": 10
  }
}
```

**Parameters:**
- `agent_id` (required) - Unique agent identifier
- `display_name` (required) - Human-readable agent name
- `public_key` (required) - PEM-formatted public key for verification
- `endpoint` (required) - HTTPS endpoint for task delivery
- `signature` (required) - Cryptographic signature for authentication
- `tags` (required) - Array of capability tags (format: `capability:version`)
- `metadata` (optional) - Additional agent configuration

**Response:** `201 Created`
```json
{
  "agent_id": "agent_data_processor_01",
  "display_name": "Data Processing Agent - Primary",
  "trust_score": 0.5,
  "tags": ["data-processing:v1", "ml-inference:v2"],
  "status": "active",
  "created_at": "2025-11-23T14:05:00Z"
}
```

### List Agents

Retrieve agents with optional filtering.

**Endpoint:** `GET /ains/agents`

**Query Parameters:**
- `tag` (optional) - Filter by capability tag
- `trust_min` (optional) - Minimum trust score (0.0-1.0)
- `status` (optional) - Filter by status (active, inactive)
- `limit` (optional, default: 50) - Results per page
- `offset` (optional, default: 0) - Pagination offset

**Example:** `GET /ains/agents?tag=data-processing:v1&trust_min=0.7&limit=25`

**Response:** `200 OK`
```json
{
  "agents": [
    {
      "agent_id": "agent_data_processor_01",
      "display_name": "Data Processing Agent - Primary",
      "trust_score": 0.85,
      "total_tasks_completed": 1247,
      "total_tasks_failed": 18,
      "success_rate": 0.986,
      "avg_completion_time_seconds": 45.3,
      "tags": ["data-processing:v1", "ml-inference:v2"],
      "status": "active",
      "last_seen_at": "2025-11-23T14:00:00Z"
    }
  ],
  "total": 1,
  "limit": 25,
  "offset": 0,
  "has_more": false
}
```

### Get Agent Details

Retrieve comprehensive information about a specific agent.

**Endpoint:** `GET /ains/agents/{agent_id}`

**Response:** `200 OK`
```json
{
  "agent_id": "agent_data_processor_01",
  "display_name": "Data Processing Agent - Primary",
  "endpoint": "https://agent.example.com/api/tasks",
  "tags": ["data-processing:v1", "ml-inference:v2"],
  "trust_score": 0.85,
  "total_tasks_completed": 1247,
  "total_tasks_failed": 18,
  "success_rate": 0.986,
  "avg_completion_time_seconds": 45.3,
  "current_load": 7,
  "max_concurrent_tasks": 10,
  "metadata": {
    "region": "us-east-1",
    "instance_type": "compute-optimized"
  },
  "created_at": "2025-11-20T10:00:00Z",
  "last_seen_at": "2025-11-23T14:00:00Z"
}
```

### Get Trust Leaderboard

Retrieve top-performing agents ranked by trust score.

**Endpoint:** `GET /ains/agents/leaderboard?limit=10`

**Response:** `200 OK`
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "agent_id": "agent_ml_specialist_07",
      "display_name": "ML Specialist Agent",
      "trust_score": 0.98,
      "total_tasks_completed": 5432,
      "success_rate": 0.995,
      "avg_completion_time_seconds": 32.1
    }
  ],
  "generated_at": "2025-11-23T14:00:00Z"
}
```

---

## Task Management

### Submit Task

Submit a new task for execution.

**Endpoint:** `POST /ains/tasks`

**Request Body:**
```json
{
  "client_id": "production_application",
  "task_type": "data_analysis",
  "capability_required": "data-processing:v1",
  "input_data": {
    "file_url": "https://storage.example.com/datasets/analysis_data.csv",
    "algorithm": "regression",
    "parameters": {
      "test_split": 0.2,
      "random_state": 42
    }
  },
  "priority": 7,
  "timeout_seconds": 300,
  "max_retries": 3,
  "depends_on": ["task_preprocessing_abc123"],
  "routing_strategy": "trust_weighted",
  "metadata": {
    "user_id": "user_123",
    "project_id": "project_456"
  }
}
```

**Parameters:**
- `client_id` (required) - Application identifier
- `task_type` (required) - Type of task to execute
- `capability_required` (required) - Required agent capability tag
- `input_data` (required) - Task-specific input payload
- `priority` (optional, default: 5) - Priority level (1-10, 10=highest)
- `timeout_seconds` (optional, default: 300) - Maximum execution time
- `max_retries` (optional, default: 3) - Retry attempts on failure
- `depends_on` (optional) - Array of task IDs that must complete first
- `routing_strategy` (optional) - Agent selection strategy
- `metadata` (optional) - Additional context information

**Response:** `201 Created`
```json
{
  "task_id": "task_xyz789def456",
  "status": "PENDING",
  "priority": 7,
  "depends_on": ["task_preprocessing_abc123"],
  "is_blocked": true,
  "routing_strategy": "trust_weighted",
  "created_at": "2025-11-23T14:10:00Z",
  "estimated_start_time": "2025-11-23T14:12:00Z"
}
```

### Batch Submit Tasks

Submit multiple tasks in a single request for improved performance.

**Endpoint:** `POST /ains/tasks/batch`

**Request Body:**
```json
{
  "tasks": [
    {
      "client_id": "production_application",
      "task_type": "data_analysis",
      "capability_required": "data-processing:v1",
      "input_data": {"dataset": "data_001.csv"},
      "priority": 7
    },
    {
      "client_id": "production_application",
      "task_type": "data_analysis",
      "capability_required": "data-processing:v1",
      "input_data": {"dataset": "data_002.csv"},
      "priority": 7
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "submitted": 2,
  "failed": 0,
  "task_ids": [
    "task_001abc",
    "task_002def"
  ],
  "submission_time_ms": 145
}
```

### Get Task Status

Retrieve current task status and details.

**Endpoint:** `GET /ains/tasks/{task_id}`

**Response:** `200 OK`
```json
{
  "task_id": "task_xyz789def456",
  "client_id": "production_application",
  "task_type": "data_analysis",
  "status": "COMPLETED",
  "priority": 7,
  "assigned_agent_id": "agent_data_processor_01",
  "input_data": {
    "file_url": "https://storage.example.com/datasets/analysis_data.csv"
  },
  "result_data": {
    "model_accuracy": 0.94,
    "predictions_url": "https://storage.example.com/results/predictions.json",
    "metrics": {
      "precision": 0.92,
      "recall": 0.91
    }
  },
  "retry_count": 0,
  "execution_time_seconds": 78.5,
  "created_at": "2025-11-23T14:10:00Z",
  "assigned_at": "2025-11-23T14:10:05Z",
  "started_at": "2025-11-23T14:10:10Z",
  "completed_at": "2025-11-23T14:11:28Z"
}
```

**Task Status Values:**
- `PENDING` - Awaiting assignment
- `ASSIGNED` - Assigned to agent
- `RUNNING` - Currently executing
- `COMPLETED` - Successfully completed
- `FAILED` - Execution failed
- `CANCELLED` - Manually cancelled
- `TIMEOUT` - Exceeded time limit

### Cancel Task

Cancel a pending or running task.

**Endpoint:** `POST /ains/tasks/{task_id}/cancel`

**Request Body:**
```json
{
  "reason": "User-requested cancellation - requirements changed"
}
```

**Response:** `200 OK`
```json
{
  "task_id": "task_xyz789def456",
  "status": "CANCELLED",
  "cancelled_at": "2025-11-23T14:15:00Z",
  "reason": "User-requested cancellation - requirements changed"
}
```

### Update Task Priority

Modify the priority of a pending task.

**Endpoint:** `PATCH /ains/tasks/{task_id}/priority`

**Request Body:**
```json
{
  "priority": 9
}
```

**Response:** `200 OK`
```json
{
  "task_id": "task_xyz789def456",
  "priority": 9,
  "previous_priority": 7,
  "updated_at": "2025-11-23T14:16:00Z"
}
```

### Get Task Dependencies

Retrieve dependency status for a task.

**Endpoint:** `GET /ains/tasks/{task_id}/dependencies`

**Response:** `200 OK`
```json
{
  "task_id": "task_xyz789def456",
  "depends_on": [
    "task_preprocessing_abc123",
    "task_validation_def456"
  ],
  "dependencies_status": {
    "task_preprocessing_abc123": "COMPLETED",
    "task_validation_def456": "RUNNING"
  },
  "is_blocked": true,
  "ready_to_run": false,
  "blocking_tasks": ["task_validation_def456"]
}
```

---

## Workflow Automation

### Task Chains

Create sequential task workflows with automatic progression.

**Endpoint:** `POST /ains/task-chains`

**Request Body:**
```json
{
  "name": "Data Processing Pipeline",
  "client_id": "production_application",
  "description": "Complete ETL pipeline for customer data",
  "steps": [
    {
      "name": "extract_data",
      "task_type": "data_extraction",
      "capability_required": "api-integration:v1",
      "input_data": {
        "source": "customer_database",
        "query": "SELECT * FROM customers WHERE updated_at > NOW() - INTERVAL '1 day'"
      }
    },
    {
      "name": "transform_data",
      "task_type": "data_transformation",
      "capability_required": "data-processing:v1",
      "input_data": {
        "operations": ["normalize", "deduplicate"]
      },
      "use_previous_output": true
    },
    {
      "name": "load_data",
      "task_type": "data_loading",
      "capability_required": "storage:v1",
      "input_data": {
        "destination": "data_warehouse"
      },
      "use_previous_output": true
    }
  ]
}
```

**Response:** `201 Created`
```json
{
  "chain_id": "chain_abc123def456",
  "name": "Data Processing Pipeline",
  "status": "RUNNING",
  "total_steps": 3,
  "current_step": 0,
  "created_at": "2025-11-23T14:20:00Z",
  "estimated_completion": "2025-11-23T14:25:00Z"
}
```

### Get Chain Status

**Endpoint:** `GET /ains/task-chains/{chain_id}`

**Response:** `200 OK`
```json
{
  "chain_id": "chain_abc123def456",
  "name": "Data Processing Pipeline",
  "status": "RUNNING",
  "current_step": 1,
  "total_steps": 3,
  "progress_percentage": 33.3,
  "steps": [
    {
      "step_index": 0,
      "name": "extract_data",
      "status": "COMPLETED",
      "task_id": "task_step0_abc"
    },
    {
      "step_index": 1,
      "name": "transform_data",
      "status": "RUNNING",
      "task_id": "task_step1_def"
    }
  ],
  "step_results": {
    "0": {
      "status": "COMPLETED",
      "data": {"records_extracted": 15430},
      "completed_at": "2025-11-23T14:21:00Z"
    }
  },
  "created_at": "2025-11-23T14:20:00Z",
  "started_at": "2025-11-23T14:20:05Z"
}
```

### Scheduled Tasks

Create recurring tasks using cron expressions.

**Endpoint:** `POST /ains/scheduled-tasks`

**Request Body:**
```json
{
  "name": "Daily Data Synchronization",
  "client_id": "production_application",
  "description": "Synchronize customer data from external systems",
  "cron_expression": "0 2 * * *",
  "timezone": "America/New_York",
  "task_type": "data_sync",
  "capability_required": "sync:v1",
  "input_data": {
    "source": "external_api",
    "destination": "data_warehouse",
    "sync_mode": "incremental"
  },
  "priority": 7,
  "timeout_seconds": 600,
  "active": true
}
```

**Cron Expression Examples:**
- `*/5 * * * *` - Every 5 minutes
- `0 */2 * * *` - Every 2 hours
- `0 9 * * 1-5` - 9 AM weekdays
- `0 0 1 * *` - First day of month at midnight
- `0 2 * * SUN` - 2 AM every Sunday

**Response:** `201 Created`
```json
{
  "schedule_id": "sched_abc123def456",
  "name": "Daily Data Synchronization",
  "cron_expression": "0 2 * * *",
  "timezone": "America/New_York",
  "active": true,
  "next_run_at": "2025-11-24T02:00:00-05:00",
  "created_at": "2025-11-23T14:25:00Z"
}
```

### Task Templates

Create reusable task configurations.

**Endpoint:** `POST /ains/task-templates`

**Request Body:**
```json
{
  "name": "Standard ML Model Training",
  "description": "Template for training ML models with standard hyperparameters",
  "client_id": "production_application",
  "task_type": "model_training",
  "capability_required": "ml-training:v2",
  "default_input_data": {
    "algorithm": "random_forest",
    "hyperparameters": {
      "n_estimators": 100,
      "max_depth": 10,
      "random_state": 42
    },
    "validation_split": 0.2
  },
  "default_priority": 6,
  "default_timeout": 3600,
  "default_max_retries": 3
}
```

**Response:** `201 Created`
```json
{
  "template_id": "tmpl_abc123def456",
  "name": "Standard ML Model Training",
  "task_type": "model_training",
  "times_used": 0,
  "created_at": "2025-11-23T14:30:00Z"
}
```

### Create Task from Template

**Endpoint:** `POST /ains/tasks/from-template`

**Request Body:**
```json
{
  "template_id": "tmpl_abc123def456",
  "input_data": {
    "training_data_url": "https://storage.example.com/datasets/train.csv",
    "hyperparameters": {
      "n_estimators": 200
    }
  },
  "priority": 8,
  "timeout_seconds": 7200
}
```

---

## Trust & Reputation

### Get Trust Metrics

Retrieve comprehensive trust metrics for an agent.

**Endpoint:** `GET /ains/agents/{agent_id}/trust`

**Response:** `200 OK`
```json
{
  "agent_id": "agent_data_processor_01",
  "trust_score": 0.85,
  "trust_level": "high",
  "total_tasks_completed": 1247,
  "total_tasks_failed": 18,
  "success_rate": 0.986,
  "avg_completion_time_seconds": 45.3,
  "reliability_rating": 4.7,
  "last_task_completed_at": "2025-11-23T14:00:00Z",
  "trust_trend": "increasing"
}
```

### Get Trust History

View historical trust score changes.

**Endpoint:** `GET /ains/agents/{agent_id}/trust/history?limit=10&start_date=2025-11-01`

**Response:** `200 OK`
```json
{
  "agent_id": "agent_data_processor_01",
  "records": [
    {
      "record_id": "rec_abc123",
      "event_type": "task_completed",
      "task_id": "task_xyz789",
      "trust_delta": 0.02,
      "trust_score_before": 0.83,
      "trust_score_after": 0.85,
      "reason": "Task completed successfully within expected time",
      "created_at": "2025-11-23T14:00:00Z"
    }
  ],
  "total_records": 156,
  "date_range": {
    "start": "2025-11-01T00:00:00Z",
    "end": "2025-11-23T14:00:00Z"
  }
}
```

### Adjust Trust Score

Manually adjust agent trust score (administrative function).

**Endpoint:** `POST /ains/agents/{agent_id}/trust/adjust`

**Request Body:**
```json
{
  "delta": -0.1,
  "reason": "Repeated policy violations - inappropriate resource usage"
}
```

**Response:** `200 OK`
```json
{
  "agent_id": "agent_data_processor_01",
  "trust_score_before": 0.85,
  "trust_score_after": 0.75,
  "delta": -0.1,
  "reason": "Repeated policy violations - inappropriate resource usage",
  "adjusted_by": "admin_user_123",
  "adjusted_at": "2025-11-23T14:35:00Z"
}
```

---

## Security & Monitoring

### Webhook Configuration

Configure event-driven notifications.

**Endpoint:** `POST /ains/webhooks`

**Request Body:**
```json
{
  "agent_id": "agent_data_processor_01",
  "url": "https://agent.example.com/webhooks/ains-events",
  "events": [
    "task.assigned",
    "task.completed",
    "task.failed",
    "task.timeout"
  ],
  "secret": "webhook_secret_key_for_hmac_verification",
  "active": true
}
```

**Response:** `201 Created`
```json
{
  "webhook_id": "wh_abc123def456",
  "agent_id": "agent_data_processor_01",
  "url": "https://agent.example.com/webhooks/ains-events",
  "events": ["task.assigned", "task.completed", "task.failed", "task.timeout"],
  "active": true,
  "created_at": "2025-11-23T14:40:00Z"
}
```

### Webhook Payload Format

When events occur, AINS sends POST requests with this format:

```json
{
  "event": "task.completed",
  "event_id": "evt_abc123",
  "timestamp": "2025-11-23T14:45:00Z",
  "data": {
    "task_id": "task_xyz789",
    "agent_id": "agent_data_processor_01",
    "status": "COMPLETED",
    "execution_time_seconds": 78.5,
    "result_data": {
      "model_accuracy": 0.94
    }
  },
  "signature": "hmac_sha256_signature_for_verification"
}
```

### Verify Webhook Signature

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    """Verify HMAC-SHA256 signature for webhook authenticity."""
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

### Security Audit Logs

Retrieve security and access logs.

**Endpoint:** `GET /ains/audit-logs`

**Query Parameters:**
- `client_id` (optional) - Filter by client
- `event_type` (optional) - Filter by event type
- `start_date` (optional) - ISO 8601 start date
- `end_date` (optional) - ISO 8601 end date
- `limit` (optional, default: 50) - Results per page
- `offset` (optional, default: 0) - Pagination offset

**Example:** `GET /ains/audit-logs?client_id=production_application&event_type=authentication&limit=50`

**Response:** `200 OK`
```json
{
  "logs": [
    {
      "log_id": "log_12345",
      "event_type": "authentication",
      "client_id": "production_application",
      "action": "api_key_used",
      "success": true,
      "ip_address": "203.0.113.42",
      "user_agent": "ProductionApp/1.0",
      "details": {
        "endpoint": "/ains/tasks",
        "method": "POST"
      },
      "created_at": "2025-11-23T14:50:00Z"
    }
  ],
  "total": 1523,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

### API Key Usage Statistics

Monitor API key usage patterns.

**Endpoint:** `GET /ains/api-keys/{key_id}/usage?period=7d`

**Query Parameters:**
- `period` - Time period (1d, 7d, 30d, 90d)

**Response:** `200 OK`
```json
{
  "key_id": "key_abc123def456",
  "period": "7d",
  "total_requests": 15847,
  "successful_requests": 15835,
  "failed_requests": 12,
  "rate_limit_hits": 8,
  "avg_requests_per_hour": 94.3,
  "peak_requests_per_hour": 234,
  "requests_by_endpoint": {
    "/ains/tasks": 12450,
    "/ains/agents": 2134,
    "/ains/task-chains": 1263
  },
  "date_range": {
    "start": "2025-11-16T00:00:00Z",
    "end": "2025-11-23T14:50:00Z"
  }
}
```

---

## Error Handling

### HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request completed successfully |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request format or parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 403 | Forbidden | Insufficient permissions for operation |
| 404 | Not Found | Requested resource does not exist |
| 409 | Conflict | Resource already exists or state conflict |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Error Response Format

All error responses follow a consistent structure:

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 100 requests per minute",
    "details": {
      "limit": 100,
      "window": "per_minute",
      "retry_after_seconds": 45,
      "current_usage": 103
    },
    "timestamp": "2025-11-23T14:55:00Z",
    "request_id": "req_abc123def456"
  }
}
```

### Application Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `INVALID_API_KEY` | 401 | API key is invalid, expired, or revoked |
| `RATE_LIMIT_EXCEEDED` | 429 | Request rate limit exceeded for API key |
| `INSUFFICIENT_PERMISSIONS` | 403 | API key lacks required scope permissions |
| `INVALID_REQUEST` | 400 | Request validation failed |
| `MISSING_REQUIRED_FIELD` | 400 | Required field missing from request |
| `INVALID_FIELD_VALUE` | 400 | Field value does not meet requirements |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `AGENT_NOT_FOUND` | 404 | Specified agent ID not found |
| `TASK_NOT_FOUND` | 404 | Specified task ID not found |
| `TEMPLATE_NOT_FOUND` | 404 | Specified template ID not found |
| `CHAIN_NOT_FOUND` | 404 | Specified chain ID not found |
| `SCHEDULE_NOT_FOUND` | 404 | Specified schedule ID not found |
| `DEPENDENCY_NOT_FOUND` | 400 | Referenced dependency task not found |
| `INSUFFICIENT_CAPACITY` | 503 | No capable agents currently available |
| `AGENT_ALREADY_EXISTS` | 409 | Agent with specified ID already registered |
| `INVALID_CRON_EXPRESSION` | 400 | Cron expression syntax is invalid |
| `INVALID_ROUTING_STRATEGY` | 400 | Specified routing strategy not supported |
| `TASK_NOT_CANCELLABLE` | 409 | Task cannot be cancelled in current state |
| `CIRCULAR_DEPENDENCY` | 400 | Task dependencies form circular reference |
| `MAX_RETRIES_EXCEEDED` | 400 | Specified retry count exceeds maximum |
| `INVALID_PRIORITY` | 400 | Priority must be between 1 and 10 |
| `INVALID_TIMEOUT` | 400 | Timeout must be between 1 and 3600 seconds |
| `BATCH_SIZE_EXCEEDED` | 400 | Batch exceeds maximum size of 100 tasks |

### Error Handling Best Practices

1. **Check HTTP Status Codes** - Always validate response status before processing
2. **Parse Error Codes** - Use application error codes for specific error handling
3. **Implement Retry Logic** - For 429 and 503 errors, implement exponential backoff
4. **Log Request IDs** - Include request_id in logs for troubleshooting
5. **Validate Before Submission** - Validate requests client-side to reduce errors

### Example Error Handling

```python
import requests
import time

def make_api_request(url, headers, data, max_retries=3):
    """Make API request with error handling and retry logic."""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                return response.json()
            
            elif response.status_code == 429:
                # Rate limit exceeded - exponential backoff
                retry_after = int(response.headers.get('Retry-After', 60))
                time.sleep(retry_after)
                continue
            
            elif response.status_code == 503:
                # Service unavailable - retry with backoff
                time.sleep(2 ** attempt)
                continue
            
            else:
                # Other errors - parse and handle
                error = response.json()['error']
                raise APIError(
                    code=error['code'],
                    message=error['message'],
                    request_id=error.get('request_id')
                )
        
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    
    raise MaxRetriesExceeded("Maximum retry attempts exceeded")
```

---

## Rate Limiting

### Overview

Rate limits protect system resources and ensure fair usage. Limits are enforced per API key with separate per-minute and per-hour thresholds.

### Default Limits

- **Per-Minute:** 60 requests
- **Per-Hour:** 1,000 requests

Custom limits can be configured during API key creation.

### Response Headers

All responses include rate limit headers:

```http
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 95
X-RateLimit-Reset-Minute: 1732377600
X-RateLimit-Limit-Hour: 5000
X-RateLimit-Remaining-Hour: 4847
X-RateLimit-Reset-Hour: 1732381200
```

### Rate Limit Exceeded Response

When rate limits are exceeded, the API returns:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
X-RateLimit-Limit-Minute: 100
X-RateLimit-Remaining-Minute: 0
X-RateLimit-Reset-Minute: 1732377600
```

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 100 requests per minute",
    "details": {
      "limit": 100,
      "window": "per_minute",
      "retry_after_seconds": 45,
      "reset_at": "2025-11-23T15:00:00Z"
    }
  }
}
```

### Best Practices

1. **Monitor Headers** - Track remaining quota in response headers
2. **Implement Backoff** - Use exponential backoff when limits are reached
3. **Batch Requests** - Use batch endpoints for bulk operations
4. **Cache Responses** - Cache agent and template data to reduce API calls
5. **Request Limit Increase** - Contact support for higher limits if needed

---

## Pagination

### Overview

List endpoints support cursor-based pagination for efficient data retrieval.

### Query Parameters

- `limit` - Results per page (default: 50, max: 100)
- `offset` - Number of results to skip (default: 0)

### Example Request

```http
GET /ains/tasks?client_id=production_application&status=COMPLETED&limit=25&offset=0
```

### Paginated Response Format

```json
{
  "results": [
    {
      "task_id": "task_001",
      "status": "COMPLETED"
    }
  ],
  "pagination": {
    "total": 250,
    "limit": 25,
    "offset": 0,
    "has_more": true,
    "next_offset": 25
  }
}
```

### Pagination Best Practices

1. **Use Appropriate Limits** - Balance between performance and response size
2. **Check has_more** - Determine if additional pages exist
3. **Store Pagination State** - Track current offset for continued retrieval
4. **Handle Empty Results** - Gracefully handle end of result set

---

## Routing Strategies

### Available Strategies

DukeNet supports multiple routing strategies for intelligent task distribution:

**round_robin** (default)
- Distributes tasks evenly across all capable agents
- Ensures fair workload distribution
- Best for homogeneous agent pools

**least_loaded**
- Routes to agent with fewest active tasks
- Optimizes for balanced resource utilization
- Recommended for heterogeneous workloads

**trust_weighted**
- Prioritizes agents with higher trust scores
- Balances reliability with availability
- Ideal for mission-critical tasks

**fastest_response**
- Routes to agent with lowest average completion time
- Optimizes for minimum latency
- Best for time-sensitive operations

### Test Routing Strategy

**Endpoint:** `POST /ains/routing/test`

**Request Body:**
```json
{
  "capability_required": "data-processing:v1",
  "routing_strategy": "trust_weighted",
  "priority": 7
}
```

**Response:** `200 OK`
```json
{
  "selected_agent": {
    "agent_id": "agent_ml_specialist_07",
    "display_name": "ML Specialist Agent",
    "trust_score": 0.98,
    "current_load": 3,
    "avg_completion_time_seconds": 32.1
  },
  "strategy_used": "trust_weighted",
  "selection_reason": "Highest trust score among available agents",
  "alternatives_considered": 5
}
```

### List Available Strategies

**Endpoint:** `GET /ains/routing/strategies`

**Response:** `200 OK`
```json
{
  "strategies": [
    {
      "name": "round_robin",
      "description": "Distribute tasks evenly across all capable agents",
      "use_cases": ["Homogeneous workloads", "Fair distribution"]
    },
    {
      "name": "least_loaded",
      "description": "Route to agent with fewest active tasks",
      "use_cases": ["Load balancing", "Resource optimization"]
    },
    {
      "name": "trust_weighted",
      "description": "Prioritize agents with higher trust scores",
      "use_cases": ["Mission-critical tasks", "High reliability requirements"]
    },
    {
      "name": "fastest_response",
      "description": "Route to agent with lowest average completion time",
      "use_cases": ["Time-sensitive operations", "Low latency requirements"]
    }
  ],
  "default_strategy": "round_robin"
}
```

---

## Webhook Events

### Available Events

| Event | Trigger Condition |
|-------|-------------------|
| `task.created` | New task submitted to system |
| `task.assigned` | Task assigned to agent |
| `task.started` | Agent begins task execution |
| `task.completed` | Task execution completed successfully |
| `task.failed` | Task execution failed |
| `task.cancelled` | Task cancelled by user or system |
| `task.timeout` | Task exceeded configured timeout |
| `task.retry` | Task retry attempt initiated |
| `agent.registered` | New agent registered in network |
| `agent.updated` | Agent information or capabilities updated |
| `agent.deactivated` | Agent removed from active pool |
| `chain.started` | Task chain execution began |
| `chain.completed` | Task chain completed all steps |
| `chain.failed` | Task chain failed during execution |

### Event Payload Structure

Each event includes consistent metadata:

```json
{
  "event": "task.completed",
  "event_id": "evt_abc123def456",
  "webhook_id": "wh_abc123def456",
  "timestamp": "2025-11-23T14:45:00Z",
  "data": {
    // Event-specific payload
  },
  "signature": "hmac_sha256_signature",
  "delivery_attempt": 1
}
```

### Webhook Delivery

- **Timeout:** 30 seconds
- **Retry Policy:** Up to 3 attempts with exponential backoff
- **Backoff Schedule:** 1 minute, 5 minutes, 15 minutes

### Managing Webhooks

**List Webhooks:** `GET /ains/webhooks?agent_id=agent_data_processor_01`

**Update Webhook:** `PATCH /ains/webhooks/{webhook_id}`

**Delete Webhook:** `DELETE /ains/webhooks/{webhook_id}`

**Delivery History:** `GET /ains/webhooks/{webhook_id}/deliveries?limit=50`

---

## API Versioning

### Current Version

The current API version is **v1.0.0**, accessible at the base path `/ains/`.

### Version Strategy

- **Backward Compatibility** - Minor versions maintain backward compatibility
- **Deprecation Notice** - 90-day notice before breaking changes
- **Version Headers** - Optional `API-Version` header for explicit version selection

### Checking API Version

**Endpoint:** `GET /ains/version`

**Response:** `200 OK`
```json
{
  "version": "1.0.0",
  "api_version": "v1",
  "build": "2025.11.23.001",
  "status": "stable",
  "deprecations": []
}
```

---

## Additional Resources

### Interactive Documentation

Access interactive API documentation with request/response examples:

- **Production:** `https://api.dukenet.example.com/docs`
- **Development:** `http://localhost:8000/docs`

### Code Examples

Language-specific integration examples available:

- [Python SDK](../examples/python/)
- [JavaScript/TypeScript SDK](../examples/javascript/)
- [Java SDK](../examples/java/)
- [Go SDK](../examples/go/)

### Support Channels

- **Documentation:** [https://docs.dukenet.example.com](https://docs.dukenet.example.com)
- **API Status:** [https://status.dukenet.example.com](https://status.dukenet.example.com)
- **Technical Support:** api-support@dukenet.dev
- **Issue Tracker:** [GitHub Issues](https://github.com/your-org/dukenet/issues)

---

## Changelog

### Version 1.0.0 (2025-11-23)

**Initial Release**
- Complete task management API
- Agent registration and coordination
- Trust and reputation system
- Advanced workflow features (chains, schedules, templates)
- Comprehensive security controls
- Rate limiting and monitoring
- Webhook notifications

For detailed version history, see [API Changelog](./CHANGELOG.md).

---

**DukeNet AINS API** - Powerful Task Orchestration Made Simple

*Copyright © 2025 DukeNet Project. All rights reserved.*