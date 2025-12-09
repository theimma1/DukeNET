# ⚡ QUICK REFERENCE CARD - SPRINT 9 & 10

**Print this or save for easy reference!**

---

## 🚀 QUICK START (Next Session)

```bash
# Terminal 1: Verify & Start API
cd /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python
source ../../../venv/bin/activate
pytest tests/integration/test_scheduling.py -v  # Should show 5 passed ✅
python -m uvicorn ains.api:app --reload --port 8000

# Terminal 2: Test API
curl http://localhost:8000/aitp/tasks/schedule  # Should respond ✅

# Terminal 3: Build next feature (see PART 1, 2, or 3 below)
```

---

## 📋 WHAT WAS BUILT (SPRINT 10)

| Component | Status | Files |
|-----------|--------|-------|
| Scheduler Core | ✅ Done | `ains/scheduler.py` (146 lines) |
| API Endpoints (9) | ✅ Done | `ains/scheduling_endpoints.py` |
| Database Models | ✅ Done | `ains/db.py` (tables created) |
| Integration Tests | ✅ Done | `tests/integration/test_scheduling.py` (5/5 passing) |
| Live API | ✅ Done | http://localhost:8000/aitp/tasks/schedule |

---

## 🎯 WHAT TO BUILD NEXT (SPRINT 9)

### PART 1: Sample Agent (90 min) ← START HERE
```
Create: sample_agent.py
Actions:
  1. Register with API
  2. Send heartbeats every 10s
  3. Poll for tasks every 5s
  4. Execute and report results
  
Test:
  - Agent registers successfully
  - Receives heartbeat confirmation
  - Polls for tasks
  - Can execute mock tasks
  - Reports completion back
```

### PART 2: E2E Tests (120 min)
```
Create: tests/e2e/
  - conftest.py (fixtures)
  - test_task_flow.py (happy path)
  - test_scheduling_flow.py (scheduling)
  - test_failure_scenarios.py (errors)
  - test_agent_integration.py (agent tests)

Test scenarios:
  1. Schedule → auto-execute → complete
  2. Agent registration → heartbeat → task poll
  3. Task assignment → execution → reporting
  4. Failure handling & retries
  
Result: 10+ E2E tests all passing
```

### PART 3: Grafana Dashboards (60 min)
```
Create:
  - docker-compose.yml
  - prometheus.yml
  - grafana dashboards

Dashboards:
  1. HTTP Metrics (request rate, latency, errors)
  2. Task Metrics (throughput, completion, failure)
  3. Agent Metrics (heartbeats, status, trust scores)
  
Access: http://localhost:3000
```

---

## 🔗 KEY API ENDPOINTS (SPRINT 10)

```bash
# Create a daily schedule at 9 AM
curl -X POST "http://localhost:8000/aitp/tasks/schedule?client_id=test&task_type=daily-report&capability_required=report-v1&cron_expression=0%209%20*%20*%20*&priority=7" \
  -H "Content-Type: application/json" \
  -d '{"input_data": {}}'

# List schedules
curl "http://localhost:8000/aitp/tasks/schedule"

# Get schedule details
curl "http://localhost:8000/aitp/tasks/schedule/sched-xxx"

# Update schedule
curl -X PUT "http://localhost:8000/aitp/tasks/schedule/sched-xxx" \
  -d '{"cron_expression": "0 10 * * *", "status": "PAUSED"}'

# Pause/Resume
curl -X POST "http://localhost:8000/aitp/tasks/schedule/sched-xxx/pause"
curl -X POST "http://localhost:8000/aitp/tasks/schedule/sched-xxx/resume"

# Execution history
curl "http://localhost:8000/aitp/tasks/schedule/sched-xxx/executions"

# Validate cron
curl -X POST "http://localhost:8000/aitp/tasks/schedule/validate?cron_expression=0%209%20*%20*%20*"

# Delete schedule
curl -X DELETE "http://localhost:8000/aitp/tasks/schedule/sched-xxx"
```

---

## 📁 FILE STRUCTURE

```
Core Project:
  /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python/

Important Files:
  ains/api.py                        Main app ⭐
  ains/scheduler.py                  Sprint 10 - Scheduling
  ains/scheduling_endpoints.py       Sprint 10 - Endpoints
  ains/db.py                         Database models
  tests/integration/test_scheduling.py    5/5 passing ✅
  ains.db                            SQLite database
  venv/                              Virtual environment
```

---

## 🔧 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| API won't start | `pkill -f uvicorn` then restart |
| Port 8000 in use | `lsof -ti:8000 \| xargs kill -9` |
| Database error | `rm -f ains.db && python init_db.py` |
| Tests fail | `pytest tests/ -v -s` for details |
| Module not found | Verify file exists: `ls -la ains/scheduling_endpoints.py` |

---

## 📊 TEST COMMANDS

```bash
# Run all integration tests (should be 5 passing)
pytest tests/integration/test_scheduling.py -v

# Run with coverage
pytest tests/ --cov=ains --cov-report=html -v

# Run specific test
pytest tests/integration/test_scheduling.py::TestCronValidation::test_valid_cron_expressions -v

# Run E2E tests (when created)
pytest tests/e2e/ -v
```

---

## 🎯 CRON EXPRESSION EXAMPLES

| Expression | Meaning |
|-----------|---------|
| `0 9 * * *` | Every day at 9 AM |
| `0 */4 * * *` | Every 4 hours |
| `0 9 * * 1-5` | Weekdays at 9 AM |
| `0 0 1 * *` | First day of month |
| `*/15 * * * *` | Every 15 minutes |
| `0 12 * * 0` | Sundays at noon |

---

## 📝 KEY METRICS

| Metric | Value |
|--------|-------|
| Response time | 50-100ms |
| Cron validation | <1ms |
| Tests passing | 5/5 (100%) |
| Code lines | 500+ |
| Endpoints | 9/9 working |
| Coverage | 37% baseline |

---

## 💾 DATABASE STATUS

| Table | Status | Purpose |
|-------|--------|---------|
| scheduled_tasks | ✅ Ready | Store schedule definitions |
| schedule_executions | ✅ Ready | Store execution history |
| agents | ✅ Ready | Agent registry |
| tasks | ✅ Ready | Task definitions |
| capabilities | ✅ Ready | Agent capabilities |
| api_keys | ✅ Ready | API authentication |
| rate_limit_tracker | ✅ Ready | Rate limiting |
| audit_logs | ✅ Ready | Security auditing |

---

## 🚨 CRITICAL REMINDERS

1. **Keep ains.db file!** Don't delete unless resetting
2. **Keep venv running** - Virtual environment must be activated
3. **Keep API running** - Server must be on port 8000 during testing
4. **Follow conventions** - All endpoints under `/aitp/tasks/` prefix
5. **Test before committing** - Run pytest before pushing

---

## 📚 DOCUMENTATION FILES

| File | Purpose |
|------|---------|
| SPRINT_9_10_RESUMPTION_GUIDE.md | ← DETAILED IMPLEMENTATION GUIDE |
| EXECUTIVE_SUMMARY.md | ← Project overview |
| SPRINT_10_FINAL_STATUS.md | Sprint 10 complete status |
| NEXT_STEPS.md | Strategic roadmap |
| SYSTEM_STATUS.md | System architecture |

---

## ⏱️ TIME BREAKDOWN

| Task | Duration | Status |
|------|----------|--------|
| Sprint 10 Complete | 2-3 hrs | ✅ DONE |
| Part 1: Sample Agent | 1.5 hrs | ⏳ TODO |
| Part 2: E2E Tests | 2 hrs | ⏳ TODO |
| Part 3: Grafana | 1 hr | ⏳ TODO |
| **TOTAL** | **~6.5 hrs** | **50% DONE** |

---

## 🎉 SUCCESS CRITERIA

### Sprint 10 ✅ ACHIEVED
- [x] Scheduler module working
- [x] 9 endpoints live
- [x] 5/5 tests passing
- [x] Database persisting
- [x] API verified working

### Sprint 9 TO ACHIEVE
- [ ] Agent polling tasks
- [ ] E2E tests validating flows
- [ ] Grafana dashboards showing metrics
- [ ] Complete system end-to-end working

---

## 🔗 QUICK LINKS

- **API Server**: http://localhost:8000
- **Metrics**: http://localhost:8000/metrics
- **Health Check**: http://localhost:8000/health
- **Grafana** (when running): http://localhost:3000
- **Prometheus** (when running): http://localhost:9090

---

## 📞 DEBUGGING CHECKLIST

Before asking for help, check:
- [ ] Is venv activated? (`which python` should show venv path)
- [ ] Is API running? (check terminal for "Uvicorn running")
- [ ] Is database accessible? (test a simple query)
- [ ] Are tests passing? (`pytest tests/integration/test_scheduling.py`)
- [ ] Is endpoint responding? (curl to /aitp/tasks/schedule)

---

## 🏁 NEXT SESSION START

```bash
# Copy-paste this:
cd /Users/immanuelolajuyigbe/DukeNET/packages/ains-core/python && source ../../../venv/bin/activate && python -m uvicorn ains.api:app --reload --port 8000
```

Then follow PART 1, 2, or 3 instructions from SPRINT_9_10_RESUMPTION_GUIDE.md

---

**Last Updated:** November 28, 2025, 4:18 AM CST  
**Status:** Ready for continuation  
**Next Action:** Build sample agent (PART 1)
