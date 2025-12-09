# Sprint 8: Monitoring & Observability

**Status:** 📋 PLANNED  
**Priority:** HIGH  
**Estimated Duration:** 2-3 weeks  
**Complexity:** Medium-High

---

## Overview

Transform DukeNet into a fully observable system with comprehensive metrics, tracing, logging, and real-time monitoring capabilities. Enable production teams to understand system behavior, diagnose issues, and optimize performance.

---

## Goals

1. **Metrics Collection** - Expose Prometheus-compatible metrics
2. **Distributed Tracing** - Implement OpenTelemetry tracing
3. **Structured Logging** - Enhanced logging with correlation IDs
4. **Health Checks** - Comprehensive system health endpoints
5. **Dashboards** - Pre-built Grafana dashboards
6. **Alerting** - Alert rule templates for common issues

---

## Features

### 8.1 Prometheus Metrics ⭐

**Priority:** HIGH  
**Complexity:** Medium  
**Estimated Effort:** 3 days

Expose application metrics in Prometheus format.

**Metrics to Track:**

**System Metrics:**
- `ains_http_requests_total` - Total HTTP requests (by endpoint, method, status)
- `ains_http_request_duration_seconds` - Request latency histogram
- `ains_http_requests_in_progress` - Active requests gauge

**Task Metrics:**
- `ains_tasks_total` - Total tasks (by status, type, priority)
- `ains_tasks_duration_seconds` - Task execution time histogram
- `ains_tasks_in_queue` - Tasks waiting for assignment
- `ains_task_retries_total` - Total retry attempts
- `ains_task_timeouts_total` - Total task timeouts

**Agent Metrics:**
- `ains_agents_total` - Total registered agents
- `ains_agents_active` - Currently active agents
- `ains_agent_trust_score` - Agent trust scores (gauge per agent)
- `ains_agent_tasks_completed_total` - Tasks completed per agent

**Chain Metrics:**
- `ains_chains_total` - Total chains (by status)
- `ains_chain_steps_total` - Total chain steps executed
- `ains_chain_duration_seconds` - Chain execution time

**Scheduled Task Metrics:**
- `ains_scheduled_tasks_total` - Total schedules
- `ains_scheduled_tasks_runs_total` - Total runs (success/failure)
- `ains_scheduled_tasks_next_run_seconds` - Time until next run

**Cache Metrics:**
- `ains_cache_hits_total` - Cache hit count
- `ains_cache_misses_total` - Cache miss count
- `ains_cache_hit_rate` - Hit rate percentage

**Database Metrics:**
- `ains_db_connections_active` - Active DB connections
- `ains_db_queries_total` - Total queries executed
- `ains_db_query_duration_seconds` - Query execution time

**Implementation:**
from prometheus_client import Counter, Histogram, Gauge, generate_latest

Define metrics
http_requests_total = Counter(
'ains_http_requests_total',
'Total HTTP requests',
['method', 'endpoint', 'status']
)

task_duration = Histogram(
'ains_tasks_duration_seconds',
'Task execution time',
['task_type', 'status']
)

Expose endpoint
@app.get("/metrics")
def metrics():
return Response(
generate_latest(),
media_type="text/plain"
)



**Acceptance Criteria:**
- [ ] All key metrics exposed at `/metrics`
- [ ] Metrics follow Prometheus naming conventions
- [ ] Histograms use appropriate buckets
- [ ] Labels added for filtering/grouping
- [ ] Documentation for all metrics

---

### 8.2 OpenTelemetry Tracing ⭐

**Priority:** HIGH  
**Complexity:** High  
**Estimated Effort:** 4 days

Implement distributed tracing to track requests across services.

**Trace Points:**
- API request entry/exit
- Database queries
- Cache operations
- External HTTP calls (webhooks)
- Task lifecycle events
- Chain step execution

**Span Attributes:**
- `http.method`, `http.route`, `http.status_code`
- `db.system`, `db.statement`, `db.operation`
- `task.id`, `task.type`, `task.status`
- `agent.id`, `agent.trust_score`
- `chain.id`, `chain.step`

**Implementation:**
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

Initialize tracer
tracer = trace.get_tracer(name)

Auto-instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

Manual spans for business logic
@tracer.start_as_current_span("route_task")
def route_task(db, task):
span = trace.get_current_span()
span.set_attribute("task.id", task.task_id)
span.set_attribute("task.routing_strategy", task.routing_strategy)


# Routing logic
agent_id = select_agent(db, task)

span.set_attribute("agent.id", agent_id)
return agent_id


**Exporters:**
- Jaeger (development)
- Tempo (production)
- Cloud providers (AWS X-Ray, Google Cloud Trace)

**Acceptance Criteria:**
- [ ] All API endpoints traced
- [ ] Database queries traced
- [ ] Task lifecycle traced end-to-end
- [ ] Span relationships correctly linked
- [ ] Traces exportable to Jaeger/Tempo
- [ ] Trace sampling configurable

---

### 8.3 Structured Logging ⭐

**Priority:** MEDIUM  
**Complexity:** Low  
**Estimated Effort:** 2 days

Enhance logging with structured JSON output and correlation IDs.

**Log Levels:**
- `DEBUG` - Detailed debugging info
- `INFO` - General informational messages
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical failures

**Log Structure:**
{
"timestamp": "2025-11-23T14:55:00Z",
"level": "INFO",
"message": "Task assigned to agent",
"correlation_id": "req_abc123",
"trace_id": "trace_xyz789",
"span_id": "span_456",
"task_id": "task_001",
"agent_id": "agent_007",
"client_id": "my_app",
"endpoint": "/ains/tasks",
"duration_ms": 45
}



**Implementation:**
import structlog

Configure structured logging
structlog.configure(
processors=[
structlog.processors.TimeStamper(fmt="iso"),
structlog.processors.add_log_level,
structlog.processors.JSONRenderer()
]
)

logger = structlog.get_logger()

Usage
logger.info(
"task_assigned",
task_id=task.task_id,
agent_id=agent.agent_id,
routing_strategy=task.routing_strategy
)



**Log Aggregation:**
- Compatible with ELK Stack (Elasticsearch, Logstash, Kibana)
- Compatible with Loki (Grafana Loki)
- Compatible with cloud logging (CloudWatch, Stackdriver)

**Acceptance Criteria:**
- [ ] All logs in structured JSON format
- [ ] Correlation IDs added to all logs
- [ ] Trace IDs linked to OpenTelemetry traces
- [ ] Log levels configurable via environment
- [ ] Sensitive data (API keys) redacted
- [ ] Log rotation configured

---

### 8.4 Health Check System ⭐

**Priority:** HIGH  
**Complexity:** Low  
**Estimated Effort:** 1 day

Comprehensive health check endpoints for monitoring.

**Health Check Types:**

**Liveness Probe** (`/health/live`)
- Is the application running?
- Quick check, always returns 200 if alive

**Readiness Probe** (`/health/ready`)
- Is the application ready to serve traffic?
- Checks database, cache, dependencies

**Startup Probe** (`/health/startup`)
- Has the application finished initialization?
- For slow-starting applications

**Detailed Health** (`/health/detail`)
- Detailed health of all components
- Database connection pool status
- Cache connectivity
- Agent availability
- Queue depth

**Implementation:**
@app.get("/health/live")
def liveness():
return {"status": "alive", "timestamp": datetime.now(timezone.utc)}

@app.get("/health/ready")
def readiness():
checks = {
"database": check_database(),
"cache": check_cache(),
"agents": check_agents_available()
}


all_healthy = all(c["healthy"] for c in checks.values())
status_code = 200 if all_healthy else 503

return JSONResponse(
    {"status": "ready" if all_healthy else "not_ready", "checks": checks},
    status_code=status_code
)
@app.get("/health/detail")
def health_detail():
return {
"status": "healthy",
"version": "1.0.0",
"uptime_seconds": get_uptime(),
"components": {
"database": {
"healthy": True,
"connections_active": 5,
"connections_max": 20,
"query_latency_ms": 2.3
},
"cache": {
"healthy": True,
"hit_rate": 0.95,
"memory_used_mb": 45
},
"agents": {
"total": 10,
"active": 8,
"average_trust": 0.82
},
"tasks": {
"pending": 5,
"running": 12,
"queue_depth": 5
}
}
}



**Acceptance Criteria:**
- [ ] Liveness probe implemented
- [ ] Readiness probe checks all dependencies
- [ ] Detailed health shows component status
- [ ] Health checks fast (<100ms)
- [ ] Kubernetes-compatible probe format

---

### 8.5 Grafana Dashboards 📊

**Priority:** MEDIUM  
**Complexity:** Medium  
**Estimated Effort:** 3 days

Pre-built Grafana dashboards for monitoring.

**Dashboard 1: System Overview**
- Request rate (requests/second)
- Request latency (p50, p95, p99)
- Error rate
- Active connections
- CPU/Memory usage

**Dashboard 2: Task Management**
- Task creation rate
- Task completion rate
- Task queue depth
- Task duration distribution
- Task failure rate by type
- Retry rate

**Dashboard 3: Agent Performance**
- Agent count (total, active)
- Agent trust score distribution
- Tasks per agent
- Agent success rate
- Agent response time

**Dashboard 4: Chain Execution**
- Active chains
- Chain completion rate
- Chain duration
- Step failure rate
- Chain success rate

**Dashboard 5: Scheduled Tasks**
- Active schedules
- Run success rate
- Missed runs
- Next run countdown

**Acceptance Criteria:**
- [ ] 5 dashboard JSON files created
- [ ] Dashboards use Prometheus data source
- [ ] Auto-refresh enabled
- [ ] Variables for filtering (environment, client_id)
- [ ] Alert annotations visible

---

### 8.6 Alert Rules 🚨

**Priority:** MEDIUM  
**Complexity:** Low  
**Estimated Effort:** 2 days

Prometheus alert rules for common issues.

**Critical Alerts:**

High Error Rate
alert: HighErrorRate
expr: rate(ains_http_requests_total{status=~"5.."}[5m]) > 0.05
for: 5m
labels:
severity: critical
annotations:
summary: "High error rate detected"
description: "Error rate is {{ $value }}% over the last 5 minutes"

Database Connection Pool Exhausted
alert: DatabaseConnectionPoolExhausted
expr: ains_db_connections_active >= ains_db_connections_max * 0.9
for: 2m
labels:
severity: critical
annotations:
summary: "Database connection pool nearly exhausted"

No Active Agents
alert: NoActiveAgents
expr: ains_agents_active == 0
for: 5m
labels:
severity: critical
annotations:
summary: "No active agents available"



**Warning Alerts:**

High Task Queue Depth
alert: HighTaskQueueDepth
expr: ains_tasks_in_queue > 100
for: 10m
labels:
severity: warning
annotations:
summary: "Task queue depth is high"

Low Cache Hit Rate
alert: LowCacheHitRate
expr: ains_cache_hit_rate < 0.7
for: 15m
labels:
severity: warning
annotations:
summary: "Cache hit rate is low"

Scheduled Task Missed
alert: ScheduledTaskMissed
expr: time() - ains_scheduled_tasks_last_run_timestamp > 3600
for: 5m
labels:
severity: warning
annotations:
summary: "Scheduled task hasn't run in over 1 hour"



**Acceptance Criteria:**
- [ ] Alert rules defined for all critical scenarios
- [ ] Alerts have appropriate severity levels
- [ ] Alert descriptions are actionable
- [ ] Runbooks linked in annotations
- [ ] Alerts tested in staging

---

### 8.7 Performance Profiling 🔍

**Priority:** LOW  
**Complexity:** Medium  
**Estimated Effort:** 2 days

Add profiling endpoints for performance analysis.

**Profiling Tools:**
- `py-spy` - CPU profiling
- `memory_profiler` - Memory profiling
- `line_profiler` - Line-by-line profiling

**Endpoints:**
@app.get("/debug/profile/cpu")
async def profile_cpu(duration: int = 30):
"""Generate CPU flame graph"""
# Only available in debug mode
if not settings.DEBUG:
raise HTTPException(403)


# Run py-spy for duration
# Return flame graph SVG
@app.get("/debug/profile/memory")
async def profile_memory():
"""Get current memory usage"""
# Memory snapshot
# Top memory consumers



**Acceptance Criteria:**
- [ ] CPU profiling endpoint
- [ ] Memory profiling endpoint
- [ ] Profiling only available in debug mode
- [ ] Flame graphs generated
- [ ] Documentation on interpreting results

---

## Technical Implementation

### Dependencies

Add to `requirements.txt`:
Monitoring & Observability
prometheus-client==0.19.0
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-sqlalchemy==0.42b0
opentelemetry-exporter-jaeger==1.21.0
structlog==23.2.0
py-spy==0.3.14
memory-profiler==0.61.0



### File Structure

ains/
├── observability/
│ ├── init.py
│ ├── metrics.py # Prometheus metrics
│ ├── tracing.py # OpenTelemetry setup
│ ├── logging.py # Structured logging
│ └── health.py # Health checks
├── monitoring/
│ ├── dashboards/
│ │ ├── system_overview.json
│ │ ├── task_management.json
│ │ ├── agent_performance.json
│ │ ├── chain_execution.json
│ │ └── scheduled_tasks.json
│ └── alerts/
│ └── prometheus_rules.yml
└── ...



---

## Testing Strategy

### Unit Tests
- Metrics increment correctly
- Health checks return proper status
- Logging outputs valid JSON
- Trace spans created correctly

### Integration Tests
- Metrics exposed at /metrics endpoint
- Traces exported to collector
- Logs aggregated correctly
- Health checks reflect actual state

### Load Tests
- Metrics don't impact performance significantly (<2% overhead)
- Tracing sampling doesn't overwhelm collector
- Health checks respond quickly under load

---

## Success Criteria

- [ ] All metrics exposed and documented
- [ ] Distributed tracing fully implemented
- [ ] Structured logging in production
- [ ] Health checks working in Kubernetes
- [ ] 5 Grafana dashboards created
- [ ] Alert rules covering critical scenarios
- [ ] <2% performance overhead from observability
- [ ] Documentation complete
- [ ] Team trained on using dashboards

---

## Risks & Mitigation

**Risk:** Performance overhead from metrics/tracing  
**Mitigation:** Implement sampling, benchmark overhead, make configurable

**Risk:** Too much data overwhelming storage  
**Mitigation:** Configure appropriate retention policies, use sampling

**Risk:** Alert fatigue from too many alerts  
**Mitigation:** Start with critical alerts only, tune thresholds based on baseline

**Risk:** Complexity in distributed tracing setup  
**Mitigation:** Use auto-instrumentation where possible, good documentation

---

## Timeline

**Week 1:**
- Days 1-2: Prometheus metrics implementation
- Days 3-4: OpenTelemetry tracing setup
- Day 5: Structured logging

**Week 2:**
- Days 1-2: Health check system
- Days 3-5: Grafana dashboards

**Week 3:**
- Days 1-2: Alert rules
- Days 3-4: Testing and documentation
- Day 5: Team training and sprint review

---

## Next Sprint Preview

**Sprint 9: Production Deployment**
- Docker containerization
- Kubernetes manifests
- CI/CD pipeline
- Infrastructure as Code
- Load balancing
- Auto-scaling

---

**Ready to start Sprint 8?** Let's build world-class observability! 🚀