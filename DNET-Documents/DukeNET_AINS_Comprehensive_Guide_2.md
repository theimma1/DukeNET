# DukeNET AINS - Comprehensive Project Guide

**Project:** DukeNET AINS (Autonomous Intelligence Network System)  
**Status:** Production Ready ✅  
**Current Version:** 1.0.0  
**Last Updated:** November 28, 2025  
**Production URL:** https://dnet-llur.onrender.com

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Sprint Summary](#sprint-summary)
5. [Getting Started](#getting-started)
6. [Development Guide](#development-guide)
7. [Deployment](#deployment)
8. [Monitoring & Observability](#monitoring--observability)
9. [API Documentation](#api-documentation)
10. [Troubleshooting](#troubleshooting)

---

## Project Overview

### What is DukeNET AINS?

DukeNET AINS is a distributed, multi-agent task orchestration and management system designed for coordinating complex workflows across autonomous agents. It provides a production-ready platform for:

- **Multi-Agent Coordination** - Register, manage, and coordinate multiple agents
- **Task Routing & Scheduling** - Intelligent task distribution with cron support
- **Trust & Reputation System** - Automatic trust scoring based on agent performance
- **Advanced Workflows** - Support for task chains, dependencies, and complex pipelines
- **Real-Time Monitoring** - Prometheus metrics, health checks, and observability
- **Security & Authentication** - API key authentication, rate limiting, audit logging
- **Webhook Notifications** - Event-driven integrations with external systems

### Key Features

✅ **Agent Management System**
- Agent registration with public key cryptography
- Capability discovery and publishing
- Heartbeat monitoring and status tracking
- Trust score calculation (0.0-1.0 scale)

✅ **Task Management**
- Task submission, routing, and execution tracking
- Automatic retry with exponential backoff
- Batch operations (up to 100 tasks)
- Task cancellation and timeout handling

✅ **Advanced Features**
- Task dependencies and blocking
- Task chains for multi-step workflows
- Cron-based task scheduling
- Task templates for reusable configurations

✅ **Observability**
- Prometheus metrics export
- Health check endpoints
- Comprehensive logging
- Production-ready API documentation

✅ **Production Ready**
- SQLite + PostgreSQL support
- API authentication and authorization
- Rate limiting per API key
- Audit logging for compliance
- Comprehensive error handling

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server (Port 8000)                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Layer (FastAPI)                      │   │
│  │  • Authentication (API Keys)                          │   │
│  │  • Rate Limiting                                      │   │
│  │  • Input Validation (Pydantic)                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Business Logic Layer                         │   │
│  │  • Task Management (routing, scheduling)              │   │
│  │  • Agent Management (registration, heartbeat)         │   │
│  │  • Trust System (scoring, reputation)                 │   │
│  │  • Webhooks (event notifications)                     │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          Data Layer                                   │   │
│  │  • SQLAlchemy ORM                                     │   │
│  │  • Database Models (13 tables)                        │   │
│  │  • Migrations (Alembic)                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │    Database Layer (SQLite/PostgreSQL)                 │   │
│  │  • Agents, Tasks, Trust Records                       │   │
│  │  • Scheduled Tasks, Webhooks                          │   │
│  │  • API Keys, Audit Logs                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema (13 Tables)

**Core Tables**
- `agents` - Agent registry with metadata
- `tasks` - Task management and tracking
- `trust_records` - Trust score history

**Capabilities**
- `agent_capabilities` - Available capabilities
- `agent_tags` - Agent categorization

**Advanced Features**
- `task_chains` - Multi-step workflows
- `scheduled_tasks` - Cron-based scheduling
- `task_templates` - Reusable task configurations

**Communication**
- `webhooks` - Webhook subscriptions
- `webhook_deliveries` - Delivery tracking

**Security & Auditing**
- `api_keys` - API authentication
- `audit_logs` - System activity logging
- `rate_limit_tracker` - Rate limiting enforcement

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.115.5 |
| **Server** | Uvicorn | 0.32.1 |
| **Database** | SQLAlchemy | 2.0.36 |
| **Validation** | Pydantic | 2.9.2 |
| **Scheduling** | croniter | 5.0.1 |
| **Monitoring** | Prometheus Client | 0.21.1 |
| **Observability** | OpenTelemetry | 1.29.0 |
| **Testing** | pytest | 8.3.4 |
| **Code Quality** | Black, Flake8, mypy | Latest |

---

## Core Components

### 1. Agent Management System

**Registration**
- Agents register with `POST /ains/agents`
- Public key cryptography for identity verification
- Unique agent IDs generated
- Initial trust score: 0.5 (medium trust)

**Heartbeat Protocol**
- Periodic heartbeats to `POST /ains/agents/{agent_id}/heartbeat`
- Marks agents as AVAILABLE or INACTIVE
- Updates last seen timestamp

**Capability Discovery**
- Agents publish capabilities: `POST /ains/agents/{agent_id}/capabilities`
- Clients search capabilities: `GET /ains/search`
- Advanced filtering by name, tags, trust score, pricing

**Trust System**
- Trust scores range from 0.0 (very low) to 1.0 (excellent)
- Automatic updates based on task outcomes:
  - Task success: +0.02
  - Task failure: -0.05
- Manual adjustments available (admin only)
- Leaderboard tracking top performers

### 2. Task Management System

**Task Submission**
- Submit tasks: `POST /ains/tasks`
- Batch submission: `POST /ains/tasks/batch` (up to 100 tasks)
- Required fields: client_id, task_type, capability_required, input_data

**Task Routing**
- Intelligent routing algorithms:
  - Round-robin: Distribute evenly
  - Least-loaded: To agent with fewest tasks
  - Trust-weighted: Favor high-trust agents
  - Fastest-response: To fastest agents
- Capability matching with agent registrations
- Priority-based queue management

**Task Lifecycle**
- PENDING → ASSIGNED → ACTIVE → COMPLETED/FAILED
- Status updates: `PUT /ains/tasks/{task_id}`
- Result retrieval: `GET /ains/tasks/{task_id}`
- Task cancellation: `DELETE /ains/tasks/{task_id}`

**Advanced Features**
- Automatic retry with exponential backoff
- Task timeouts with automatic failure
- Task cancellation with cleanup
- Execution history tracking

### 3. Scheduling System

**Cron-Based Scheduling**
- Create schedules: `POST /aitp/tasks/schedule`
- Full cron expression support: `0 9 * * *` (daily at 9 AM)
- Timezone support: UTC or custom (e.g., America/New_York)

**Schedule Management**
- List schedules: `GET /aitp/tasks/schedule`
- Get details: `GET /aitp/tasks/schedule/{id}`
- Update: `PUT /aitp/tasks/schedule/{id}`
- Delete: `DELETE /aitp/tasks/schedule/{id}`

**Execution Management**
- Automatic background worker (every 30 seconds)
- Manual trigger: `POST /aitp/tasks/schedule/{id}/execute`
- Pause/Resume: `POST /aitp/tasks/schedule/{id}/pause`
- Execution history: `GET /aitp/tasks/schedule/{id}/executions`

### 4. Security System

**API Key Authentication**
- Generate keys: `POST /ains/api-keys`
- Format: `ains_[44_character_token]`
- Stored as SHA-256 hash (never plain text)
- Per-key rate limits and scopes

**Rate Limiting**
- Two-tier system:
  - Per-minute limit (default: 60 req/min)
  - Per-hour limit (default: 1000 req/hour)
- Sliding window algorithm
- Returns 429 (Too Many Requests) when exceeded

**Audit Logging**
- All security events logged
- Event types: auth_success, auth_failed, rate_limit_exceeded
- Full audit trail for compliance

### 5. Observability & Monitoring

**Health Checks**
- Liveness: `GET /health` (quick status)
- Detailed: `GET /health/detail` (component breakdown)
- Database, cache, and agent connectivity checks

**Prometheus Metrics**
- Export: `GET /metrics` (Prometheus format)
- HTTP metrics: requests, latency, error rates
- Task metrics: created, completed, failed, queue depth
- Agent metrics: total, active, trust scores
- Webhook metrics: deliveries, success rates

**Built-in Documentation**
- Swagger UI: `GET /docs`
- ReDoc: `GET /redoc`
- OpenAPI spec: `GET /openapi.json`

---

## Sprint Summary

### Sprint 1-3: Foundation
- ✅ Agent registration and identity system
- ✅ Task schema and submission API
- ✅ Intelligent task routing
- ✅ Task lifecycle management
- ✅ Basic monitoring

### Sprint 4: Advanced Features
- ✅ Automatic task retry with exponential backoff
- ✅ Batch task operations (up to 100 tasks/request)
- ✅ Webhook notifications for task events
- ✅ Performance optimization (caching, indexing)
- ✅ Priority queue management
- ✅ Task cancellation and timeouts
- ✅ Security and permissions
- ✅ Analytics and reporting

### Sprint 5: Trust & Reputation
- ✅ Trust score system (0.0-1.0 scale)
- ✅ Automatic trust adjustments
- ✅ Trust history audit trail
- ✅ Agent leaderboard
- ✅ Manual trust adjustments (admin)

### Sprint 6: Security & Authorization
- ✅ API key authentication
- ✅ Rate limiting (per-minute & per-hour)
- ✅ Security audit logging
- ✅ API key lifecycle management
- ✅ Usage tracking

### Sprint 7: Advanced Workflows
- ✅ Task dependencies
- ✅ Task chains (multi-step workflows)
- ✅ Advanced routing algorithms
- ✅ Scheduled tasks (cron)
- ✅ Task templates

### Sprint 8: Observability
- ✅ Prometheus metrics
- ✅ Health check endpoints
- ✅ Structured logging
- ✅ Performance metrics

### Sprint 9: End-to-End Testing
- ✅ Sample agent implementation
- ✅ End-to-end test suite
- ✅ Trust/routing validation
- ✅ Grafana dashboards

### Sprint 10: Production Deployment
- ✅ Task scheduling (cron) - Production ready
- ✅ All features tested
- ✅ Deployed to Render (https://dnet-llur.onrender.com)
- ✅ Database initialized
- ✅ API serving globally

**Total Status:** 10 Sprints Complete ✅
**Production Status:** LIVE 🚀

---

## Getting Started

### Prerequisites

- Python 3.10+
- Virtual environment (`venv`)
- Git
- Curl (for API testing)

### Local Development Setup

**1. Clone and Install**
```bash
cd /Users/immanuelolajuyigbe/DukeNET
source venv/bin/activate
cd packages/ains-core/python
pip install -r requirements.txt
```

**2. Initialize Database**
```bash
python init_db.py
```

**3. Start API Server**
```bash
uvicorn ains.api:app --reload --port 8000
```

**4. Test Endpoints**
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Metrics
curl http://localhost:8000/metrics
```

### Production Deployment

**Current Production Instance**
- URL: https://dnet-llur.onrender.com
- Status: 🟢 Healthy
- Deployment: Render (free tier)

**Check Production Status**
```bash
curl https://dnet-llur.onrender.com/health
```

---

## Development Guide

### File Structure

```
DukeNET/
├── packages/
│   └── ains-core/
│       └── python/
│           ├── ains/
│           │   ├── __init__.py          # Package initialization
│           │   ├── api.py               # FastAPI app & routes
│           │   ├── db.py                # Database models
│           │   ├── schemas.py           # Pydantic schemas
│           │   ├── scheduler.py         # Task scheduling
│           │   ├── retry.py             # Retry logic
│           │   ├── batch.py             # Batch operations
│           │   ├── webhooks.py          # Webhook system
│           │   ├── trust_system.py      # Trust scoring
│           │   ├── advanced_features.py # Chains, routing
│           │   └── observability/
│           │       ├── metrics.py       # Prometheus metrics
│           │       ├── middleware.py    # HTTP tracking
│           │       └── __init__.py
│           ├── tests/
│           │   ├── test_*.py            # Unit tests
│           │   └── integration/         # Integration tests
│           ├── init_db.py               # Database initialization
│           ├── requirements.txt         # Dependencies
│           └── startup.sh               # Startup script
├── aicp-core/
│   └── python/
│       └── aicp/                        # Protocol library
├── docs/                                # Documentation
└── README.md                            # Project README
```

### Adding a New Feature

**1. Update Database Models (if needed)**
```python
# ains/db.py
class NewFeature(Base):
    __tablename__ = "new_features"
    id = Column(Integer, primary_key=True)
    # ... fields
```

**2. Create Pydantic Schemas**
```python
# ains/schemas.py
class NewFeatureRequest(BaseModel):
    field_name: str
    # ... fields

class NewFeatureResponse(BaseModel):
    id: int
    # ... fields
```

**3. Implement Business Logic**
```python
# ains/feature.py (new file)
def handle_feature(db: Session, request: NewFeatureRequest):
    # Implementation
    pass
```

**4. Add API Endpoints**
```python
# ains/api.py
@app.post("/feature")
def create_feature(request: NewFeatureRequest, db: Session = Depends(get_db)):
    return handle_feature(db, request)
```

**5. Write Tests**
```python
# tests/test_feature.py
def test_feature_creation(test_db):
    # Test implementation
    pass
```

### Testing

**Run All Tests**
```bash
pytest tests/ -v
```

**Run Specific Test**
```bash
pytest tests/test_agents.py::test_agent_registration -v
```

**With Coverage**
```bash
pytest tests/ --cov=ains --cov-report=html
```

### Code Quality

**Format Code**
```bash
black ains/
```

**Lint**
```bash
flake8 ains/
```

**Type Check**
```bash
mypy ains/
```

---

## API Documentation

### Core Endpoints

#### Agents

```bash
# Register agent
POST /ains/agents
{
  "agent_id": "agent-123",
  "public_key": "...",
  "display_name": "My Agent",
  "endpoint": "http://agent.example.com"
}

# Get agent
GET /ains/agents/{agent_id}

# Agent heartbeat
POST /ains/agents/{agent_id}/heartbeat

# Get agent trust
GET /ains/agents/{agent_id}/trust

# Agent leaderboard
GET /ains/agents/leaderboard
```

#### Tasks

```bash
# Submit task
POST /ains/tasks
{
  "client_id": "client-1",
  "task_type": "analysis",
  "capability_required": "data:v1",
  "input_data": {...}
}

# Batch submit
POST /ains/tasks/batch
{
  "tasks": [...]
}

# Get task
GET /ains/tasks/{task_id}

# Update task
PUT /ains/tasks/{task_id}

# Cancel task
DELETE /ains/tasks/{task_id}
```

#### Scheduling

```bash
# Create schedule
POST /aitp/tasks/schedule
{
  "client_id": "client-1",
  "task_type": "daily-report",
  "cron_expression": "0 9 * * *"
}

# List schedules
GET /aitp/tasks/schedule

# Get schedule
GET /aitp/tasks/schedule/{id}

# Update schedule
PUT /aitp/tasks/schedule/{id}

# Execute now
POST /aitp/tasks/schedule/{id}/execute
```

#### Security

```bash
# Create API key
POST /ains/api-keys
{
  "client_id": "my-app",
  "name": "Production Key"
}

# List API keys
GET /ains/api-keys

# Revoke API key
DELETE /ains/api-keys/{key_id}
```

### Response Format

All responses follow this format:

**Success (200-299)**
```json
{
  "status": "success",
  "data": { ... }
}
```

**Error (400+)**
```json
{
  "status": "error",
  "error": "Error message",
  "details": { ... }
}
```

### Authentication

All protected endpoints require API key:

```bash
curl -H "X-API-Key: ains_your_key_here" http://localhost:8000/ains/protected/endpoint
```

---

## Monitoring & Observability

### Health Checks

**Basic Health**
```bash
curl http://localhost:8000/health
# Response: {"status":"healthy","service":"DukeNet-AINS","version":"1.0.0"}
```

**Detailed Health**
```bash
curl http://localhost:8000/health/detail
# Response: Component-by-component status
```

### Prometheus Metrics

**Export Metrics**
```bash
curl http://localhost:8000/metrics
```

**Key Metrics**
- `ains_http_requests_total` - Total HTTP requests
- `ains_http_request_duration_seconds` - Request latency
- `ains_tasks_created_total` - Created tasks
- `ains_tasks_completed_total` - Completed tasks
- `ains_agents_total` - Total agents
- `ains_agent_trust_score` - Agent trust scores

### Grafana Dashboards

(Available when connected to Prometheus)

**Recommended Dashboards**
1. HTTP & API Metrics
2. Task Execution & Throughput
3. Agent Performance & Trust
4. System Health & Resources

### Logging

**View Logs (local)**
```bash
tail -f /path/to/logs/ains.log
```

**Important Log Events**
- Agent registration
- Task routing decisions
- Trust score updates
- Authentication failures
- Rate limit violations

---

## Troubleshooting

### Common Issues

**Issue: "No such table" errors**
```bash
# Solution: Reinitialize database
python init_db.py
```

**Issue: Port 8000 already in use**
```bash
# Solution: Kill existing process
lsof -i :8000
kill -9 <PID>
```

**Issue: API not responding**
```bash
# Check health
curl http://localhost:8000/health

# Check logs
tail -f logs/ains.log

# Restart server
ctrl+c
uvicorn ains.api:app --reload --port 8000
```

**Issue: Database locked**
```bash
# Solution: Close all connections and restart
rm ains.db*
python init_db.py
```

**Issue: Tests failing**
```bash
# Solution: Clean and rerun
rm -rf .pytest_cache
pytest tests/ -v --tb=short
```

### Performance Tuning

**Slow API responses**
1. Check database indexes: `SELECT * FROM sqlite_master WHERE type='index'`
2. Enable query logging: `export SQLALCHEMY_ECHO=1`
3. Check Prometheus metrics for bottlenecks

**High memory usage**
1. Check task queue depth: `GET /health/detail`
2. Reduce batch sizes if submitting large batches
3. Check webhook delivery backlog

**Rate limiting issues**
1. Increase API key limits: `PATCH /ains/api-keys/{key_id}`
2. Or create separate keys for different environments

---

## Contributing

### Development Workflow

1. Create a branch: `git checkout -b feature/your-feature`
2. Make changes and test: `pytest tests/`
3. Format code: `black ains/`
4. Lint: `flake8 ains/`
5. Commit: `git commit -m "feat: your feature"`
6. Push and create PR

### Code Standards

- Python 3.10+ compatible
- Type hints on all functions
- Docstrings on classes and public functions
- 80%+ test coverage
- PEP 8 compliant

### Testing Standards

- Unit tests for all functions
- Integration tests for workflows
- Performance tests for critical paths
- 80% line coverage minimum

---

## Deployment

### Production Deployment (Render)

**Current Instance**
- URL: https://dnet-llur.onrender.com
- Auto-deploys on git push
- Free tier with 0.5 GB RAM
- SQLite database

**Deploy Steps**
1. Push to main branch: `git push origin main`
2. Render auto-deploys
3. Check status: `curl https://dnet-llur.onrender.com/health`

### Scaling Considerations

**When to Upgrade**
- Task throughput > 100 tasks/sec
- More than 50 concurrent agents
- Response latency > 100ms p95

**Upgrade Options**
1. Switch to PostgreSQL (production database)
2. Add Redis for caching
3. Scale to paid Render tier or AWS/GCP
4. Implement distributed tracing (Jaeger)

### Database Migration

**From SQLite to PostgreSQL**
```bash
# Update connection string
export DATABASE_URL="postgresql://user:pass@host:5432/ains"

# Restart server
uvicorn ains.api:app --port 8000
```

---

## Quick Reference

### Essential Commands

```bash
# Start server
uvicorn ains.api:app --reload --port 8000

# Initialize database
python init_db.py

# Run tests
pytest tests/ -v

# Format code
black ains/

# Check health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Export metrics
curl http://localhost:8000/metrics
```

### Key URLs

| URL | Purpose |
|-----|---------|
| http://localhost:8000 | API base |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/redoc | ReDoc |
| http://localhost:8000/health | Health check |
| http://localhost:8000/metrics | Prometheus metrics |
| https://dnet-llur.onrender.com | Production instance |

### Important Files

| File | Purpose |
|------|---------|
| ains/api.py | Main FastAPI app |
| ains/db.py | Database models |
| ains/schemas.py | Pydantic schemas |
| ains/scheduler.py | Task scheduling |
| tests/ | Test suite |
| requirements.txt | Dependencies |
| init_db.py | Database setup |

---

## Summary

DukeNET AINS is a **production-ready, fully-featured distributed task orchestration system** that provides:

✅ **Multi-agent coordination** with automatic trust scoring  
✅ **Intelligent task routing** with multiple algorithms  
✅ **Advanced scheduling** with cron support  
✅ **Enterprise security** with API keys and rate limiting  
✅ **Full observability** with Prometheus metrics  
✅ **Comprehensive testing** with 40+ test cases  
✅ **Production deployment** on Render  

### Next Steps for New Developers

1. **Read this guide** (you're doing it!)
2. **Clone the repo** and set up locally
3. **Run the tests** to verify setup
4. **Start the server** and explore `/docs`
5. **Review a sprint document** to understand features
6. **Make a small contribution** to get familiar with codebase

### Resources

- **Production URL:** https://dnet-llur.onrender.com
- **GitHub:** https://github.com/theimma1/DukeNET
- **Documentation:** See `docs/` directory
- **Issues:** File on GitHub

---

**Welcome to the DukeNET AINS project! 🚀**

For questions or support, refer to the documentation or open an issue on GitHub.