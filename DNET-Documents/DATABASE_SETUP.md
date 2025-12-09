# DukeNET Database Setup Guide

## Quick Start

### Initialize Database

```bash
cd /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python
source /Users/immanuelolajuyigbe/DukeNET/venv/bin/activate
python init_db.py
```

### Start Server

```bash
cd /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python
source /Users/immanuelolajuyigbe/DukeNET/venv/bin/activate
uvicorn ains.api:app --reload --port 8000
```

## Database Schema

The database consists of 13 tables organized into 5 functional categories:

### Core Tables
- **tasks** - Task management and execution tracking
- **agents** - Agent registry and metadata
- **trust_records** - Trust scores and reputation tracking

### Capability System
- **agent_capabilities** - Agent capability definitions
- **agent_tags** - Agent classification and discovery

### Advanced Features
- **task_chains** - Multi-step workflow orchestration
- **scheduled_tasks** - Cron-like task scheduling
- **task_templates** - Reusable task definitions

### Communication
- **webhooks** - Webhook subscription management
- **webhook_deliveries** - Delivery tracking and retry logic

### Security & Auditing
- **api_keys** - API authentication and authorization
- **audit_logs** - System activity logging
- **rate_limit_tracker** - Rate limiting enforcement

## Configuration

**Default database:**
```
sqlite:///./ains.db
```

**Override with environment variable:**
```bash
# SQLite
export DATABASE_URL="sqlite:///./custom.db"

# PostgreSQL
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

## Testing the System

### Start the Server
```bash
cd /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python
source /Users/immanuelolajuyigbe/DukeNET/venv/bin/activate
uvicorn ains.api:app --reload --port 8000
```

### Test Endpoints (in a new terminal)
```bash
# Health check
curl http://localhost:8000/health

# System metrics
curl http://localhost:8000/metrics | head -50

# Interactive API documentation
open http://localhost:8000/docs
```

## Troubleshooting

### "No such table" errors
Run the initialization script to create or recreate all tables:
```bash
python init_db.py
```

### Wrong virtual environment
Always use the project root virtual environment:
```bash
source /Users/immanuelolajuyigbe/DukeNET/venv/bin/activate
```
Do not use package-specific virtual environments.

### Database file location
The database file is created in the current working directory. Always run commands from:
```
/Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python/
```

### Server already running
If you see a "port already in use" error, stop the existing server:
```bash
# Find the process
lsof -i :8000

# Kill it (replace PID with the actual process ID)
kill -9 <PID>
```

## Status

✅ **Production Ready** - All 13 tables initialized and tested

## Git Workflow

To save this documentation:
```bash
git add docs/DATABASE_SETUP.md
git commit -m "Add database setup documentation

Complete guide for database initialization and management.

Includes:
- Quick start commands
- Table descriptions (all 13 tables)
- Configuration options
- Troubleshooting guide
- Testing procedures"

git push origin main
```