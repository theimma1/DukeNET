# DukeNET Sprint 2 Detailed Plan
## AINS (Agent Identity & Naming System)
### November 22 - December 6, 2025 (2 Weeks)

**Sprint Goal:** Build agent discovery, registration, and trust management system - Enable agents to find each other and assess reliability

**Product Owner:** Immanuel Olajuyigbe  
**Scrum Master:** TBD  
**Development Team:** 2-3 developers  
**Sprint Capacity:** 42 story points

**Dependencies:** ✅ AICP Protocol (Sprint 1 complete)

---

## 📋 Sprint 2 Backlog

### Story 2.1: Agent Registration API 🔄 IN PROGRESS
**Story Points:** 5  
**Status:** NOT STARTED  
**Sprint Days:** Mon-Tue (Days 1-2)  
**Planned Start:** November 22, 2025

**Goal:** Enable agents to register themselves in the AINS registry with signature verification

**What to Build:**

#### Task 2.1.1: Database Schema Setup (Day 1)
**What to build:**
- PostgreSQL connection and setup
- Agents table creation with proper indexes
- Agent_tags table for many-to-many relationships
- Migration scripts

**Code structure:**
```python
# packages/ains-core/python/ains/db.py

from sqlalchemy import create_engine, Column, String, DateTime, Integer, Boolean, DECIMAL, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Agent(Base):
    __tablename__ = "agents"
    
    agent_id = Column(String(64), primary_key=True)  # SHA256(public_key)
    public_key = Column(Text, nullable=False, unique=True)
    display_name = Column(String(255))
    description = Column(Text)
    endpoint_url = Column(String(255))
    status = Column(String(20), default='ACTIVE')  # ACTIVE, INACTIVE, SUSPENDED
    created_at = Column(DateTime, default=datetime.utcnow)
    last_heartbeat = Column(DateTime)
    owner_address = Column(String(42))
    avatar_url = Column(String(255))
    trust_score = Column(DECIMAL(5,2), default=50.0)
    version = Column(String(20))

class Agent_Tag(Base):
    __tablename__ = "agent_tags"
    
    agent_id = Column(String(64), primary_key=True)
    tag = Column(String(100), primary_key=True)
```

**Acceptance Criteria:**
- [ ] PostgreSQL tables created with proper schema
- [ ] Indexes on commonly queried fields
- [ ] Migration scripts working
- [ ] Unit tests for DB operations

---

#### Task 2.1.2: Agent Registration Endpoint (Day 1-2)
**What to build:**
- POST /ains/agents endpoint
- Signature verification (Ed25519)
- Agent record creation in database
- Error handling for duplicates

**Code structure:**
```python
# packages/ains-core/python/ains/api.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

class AgentRegistration(BaseModel):
    agent_id: str
    public_key: str
    display_name: str
    description: Optional[str] = None
    endpoint: str
    signature: str  # Hex-encoded signature

@app.post("/ains/agents")
def register_agent(registration: AgentRegistration):
    """
    Register a new agent in AINS
    
    - Verify Ed25519 signature
    - Create agent record
    - Return agent profile
    """
    # 1. Verify signature
    # 2. Check if agent already exists
    # 3. Create record in database
    # 4. Return agent profile
    
    return {
        "agent_id": registration.agent_id,
        "status": "ACTIVE",
        "created_at": datetime.utcnow().isoformat(),
        "trust_score": 50.0
    }
```

**Acceptance Criteria:**
- [ ] Endpoint accepts registration requests
- [ ] Verifies Ed25519 signatures
- [ ] Stores agent in database
- [ ] Returns agent profile
- [ ] Rejects duplicate registrations
- [ ] Unit tests passing

---

#### Task 2.1.3: Integration with AICP (Day 2)
**What to build:**
- AINS can receive agent data via AICP messages
- Bidirectional communication via AICP

**Acceptance Criteria:**
- [ ] AINS server listens on AICP protocol
- [ ] Can receive agent registration via AICP messages
- [ ] Integration tests passing

**Definition of Done:**
- [ ] All tasks completed
- [ ] >90% test coverage
- [ ] Code reviewed
- [ ] Merged to main branch
- [ ] Documentation complete

**Subtasks & Time Breakdown:**
```
Day 1: Database setup + Registration endpoint (4-5 hours)
Day 2: AICP integration + Testing (3-4 hours)
```

---

### Story 2.2: Agent Lookup by ID 🔄 IN PROGRESS
**Story Points:** 3  
**Status:** NOT STARTED  
**Sprint Days:** Tue-Wed (Days 2-3)  
**Planned Start:** November 25, 2025

**Goal:** Fast agent lookup with sub-10ms response time using Redis caching

**Tasks:**

#### Task 2.2.1: Redis Cache Setup
**What to build:**
- Redis connection and configuration
- Cache key patterns for agents
- Cache invalidation strategy

**Code structure:**
```python
# packages/ains-core/python/ains/cache.py

import redis
import json

class AgentCache:
    def __init__(self, host="localhost", port=6379):
        self.redis = redis.Redis(host=host, port=port, decode_responses=True)
        self.ttl = 300  # 5 minutes
    
    def get_agent(self, agent_id: str):
        """Get agent from cache"""
        key = f"agent:{agent_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def set_agent(self, agent_id: str, agent_data: dict):
        """Cache agent data"""
        key = f"agent:{agent_id}"
        self.redis.setex(key, self.ttl, json.dumps(agent_data))
    
    def invalidate_agent(self, agent_id: str):
        """Invalidate agent cache"""
        key = f"agent:{agent_id}"
        self.redis.delete(key)
```

---

#### Task 2.2.2: GET /ains/agents/{agent_id} Endpoint
**What to build:**
- GET endpoint for agent lookup
- Cache-first lookup strategy
- Database fallback

**Code structure:**
```python
@app.get("/ains/agents/{agent_id}")
def get_agent(agent_id: str):
    """
    Get agent by ID
    - Check cache (Redis) first
    - Fall back to database
    - Update cache
    - Return agent profile
    """
    # 1. Check cache
    # 2. If miss, query database
    # 3. Update cache
    # 4. Return agent profile
    
    return {
        "agent_id": agent_id,
        "public_key": "...",
        "display_name": "...",
        "endpoint": "...",
        "status": "ACTIVE",
        "trust_score": 75.5
    }
```

**Acceptance Criteria:**
- [ ] Endpoint accepts agent_id
- [ ] Returns full agent profile
- [ ] Uses Redis cache (<10ms target)
- [ ] Falls back to database
- [ ] Performance tested
- [ ] Unit tests passing

---

#### Task 2.2.3: Performance Testing
**What to build:**
- Benchmark cache performance
- Measure lookup time (P50, P95, P99)
- Document results

**Acceptance Criteria:**
- [ ] Sub-10ms response time achieved
- [ ] Cache hit rate >95%
- [ ] Performance report generated
- [ ] Integration tests passing

**Definition of Done:**
- [ ] All tasks completed
- [ ] >90% test coverage
- [ ] Code reviewed
- [ ] Merged to main branch

---

### Story 2.3: Capability Registry 🔄 IN PROGRESS
**Story Points:** 8  
**Status:** NOT STARTED  
**Sprint Days:** Wed-Thu (Days 3-4)  
**Planned Start:** November 26, 2025

**Goal:** Allow agents to publish their capabilities with pricing and SLO metadata

**Tasks:**

#### Task 2.3.1: Capability Data Model
**What to build:**
- Capability table in database
- Input/output schema validation
- Pricing model storage

**Code structure:**
```python
# Database schema

class Capability(Base):
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
    pricing_model = Column(String(20))  # per_call, subscription, free
    price = Column(DECIMAL(10,4))
    currency = Column(String(10), default='USD')
    
    # SLO
    latency_p99_ms = Column(Integer)
    availability_percent = Column(DECIMAL(5,2))
    
    deprecated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
```

---

#### Task 2.3.2: POST /ains/agents/{agent_id}/capabilities
**What to build:**
- Endpoint to publish capability
- Schema validation
- Database storage

**Code structure:**
```python
class CapabilityPublish(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    pricing_model: str
    price: float
    latency_p99_ms: int
    availability_percent: float
    signature: str

@app.post("/ains/agents/{agent_id}/capabilities")
def publish_capability(agent_id: str, capability: CapabilityPublish):
    """Publish agent capability"""
    # 1. Verify agent exists
    # 2. Verify signature
    # 3. Validate schemas
    # 4. Store in database
    # 5. Invalidate cache
    
    return {"capability_id": "cap_...", "status": "published"}
```

**Acceptance Criteria:**
- [ ] Accepts capability data
- [ ] Validates JSON schemas
- [ ] Stores in database
- [ ] Returns capability ID
- [ ] Unit tests passing

---

#### Task 2.3.3: Capability Search & Indexing
**What to build:**
- Full-text search capability names
- Tag-based indexing
- Search endpoint

**Acceptance Criteria:**
- [ ] Can search by name
- [ ] Can filter by pricing_model
- [ ] Indexed for performance
- [ ] Unit tests passing

**Definition of Done:**
- [ ] All tasks completed
- [ ] >90% test coverage
- [ ] Code reviewed
- [ ] Merged to main branch

---

### Story 2.4: Capability Search 🔄 IN PROGRESS
**Story Points:** 8  
**Status:** NOT STARTED  
**Sprint Days:** Thu-Fri (Days 4-5)  
**Planned Start:** November 27, 2025

**Goal:** Enable agents to discover other agents by searching for capabilities

**Tasks:**

#### Task 2.4.1: GET /ains/search Endpoint
**What to build:**
- Multi-parameter search endpoint
- Filter by capability name
- Filter by tags
- Filter by minimum trust score
- Sort by multiple criteria

**Code structure:**
```python
@app.get("/ains/search")
def search_agents(
    capability: Optional[str] = None,
    tags: Optional[str] = None,  # comma-separated
    min_trust: Optional[float] = 0,
    sort_by: str = "trust_score",  # trust_score, price, latency
    limit: int = 10,
    offset: int = 0
):
    """
    Search for agents
    
    Parameters:
    - capability: Capability name to search for
    - tags: Comma-separated tags
    - min_trust: Minimum trust score (0-100)
    - sort_by: Sort field
    - limit: Max results
    - offset: Pagination offset
    """
    # 1. Build database query
    # 2. Apply filters
    # 3. Sort results
    # 4. Paginate
    # 5. Return results
    
    return {
        "results": [
            {
                "agent_id": "...",
                "display_name": "Agent 1",
                "trust_score": 92.5,
                "capability_match": 0.98,
                "pricing": {"model": "per_call", "price": 0.001}
            }
        ],
        "total": 45,
        "limit": 10,
        "offset": 0
    }
```

**Acceptance Criteria:**
- [ ] Endpoint accepts search parameters
- [ ] Filters work correctly
- [ ] Sorting works
- [ ] Pagination works
- [ ] Performance acceptable
- [ ] Unit tests passing

---

#### Task 2.4.2: Search Performance Optimization
**What to build:**
- Database indexes on search columns
- Query optimization
- Performance benchmarks

**Acceptance Criteria:**
- [ ] <100ms search response time
- [ ] Indexes created
- [ ] Query optimized
- [ ] Benchmarks documented

**Definition of Done:**
- [ ] All tasks completed
- [ ] >90% test coverage
- [ ] Code reviewed
- [ ] Merged to main branch

---

### Story 2.5: Trust Score Calculation 🔄 IN PROGRESS
**Story Points:** 8  
**Status:** NOT STARTED  
**Sprint Days:** Mon-Tue (Days 6-7)  
**Planned Start:** November 29, 2025

**Goal:** Calculate and track agent trust scores based on reputation, uptime, and performance

**Tasks:**

#### Task 2.5.1: Trust Record Schema
**What to build:**
- Database table for trust records
- Historical tracking
- Update mechanism

**Code structure:**
```python
class TrustRecord(Base):
    __tablename__ = "trust_records"
    
    record_id = Column(Integer, primary_key=True)
    agent_id = Column(String(64), ForeignKey("agents.agent_id"))
    
    # Scores
    trust_score = Column(DECIMAL(5,2))
    reputation_score = Column(DECIMAL(5,2))
    rating = Column(DECIMAL(3,2))  # 0-5.0
    total_ratings = Column(Integer, default=0)
    
    # Transactions
    successful_transactions = Column(Integer, default=0)
    failed_transactions = Column(Integer, default=0)
    
    # Uptime
    uptime_30d = Column(DECIMAL(5,2))
    uptime_90d = Column(DECIMAL(5,2))
    uptime_all_time = Column(DECIMAL(5,2))
    
    # Performance
    avg_latency_ms = Column(Integer)
    p99_latency_ms = Column(Integer)
    success_rate = Column(DECIMAL(5,2))
    
    # Security
    verified_signer = Column(Boolean, default=False)
    rate_limited = Column(Boolean, default=False)
    fraud_flags = Column(Integer, default=0)
    last_audit = Column(DateTime)
    
    updated_at = Column(DateTime, default=datetime.utcnow)
```

---

#### Task 2.5.2: Trust Score Calculation Algorithm
**What to build:**
- Formula: Trust = (reputation × 0.6) + (uptime × 0.3) + (performance × 0.1)
- Update mechanism after transactions
- Historical tracking

**Code structure:**
```python
def calculate_trust_score(agent_id: str) -> float:
    """
    Calculate trust score for agent
    
    Formula:
    Trust = (Reputation × 0.6) + (Uptime × 0.3) + (Performance × 0.1)
    
    where:
    - Reputation = (successful_tx / total_tx) × average_rating × 100
    - Uptime = average of 30d, 90d, all_time uptime percentages
    - Performance = 100 - (avg_latency_ms / max_latency_ms) × 100
    """
    record = get_trust_record(agent_id)
    
    # Calculate components
    reputation = (record.successful_transactions / 
                  (record.successful_transactions + record.failed_transactions)) * \
                 (record.rating / 5.0) * 100
    
    uptime = (record.uptime_30d + record.uptime_90d + record.uptime_all_time) / 3
    
    performance = 100 - (record.avg_latency_ms / 1000.0) * 100
    
    # Weighted calculation
    trust_score = (reputation * 0.6) + (uptime * 0.3) + (performance * 0.1)
    
    return trust_score
```

**Acceptance Criteria:**
- [ ] Formula implemented correctly
- [ ] Updates after transactions
- [ ] Historical records maintained
- [ ] Unit tests passing

---

#### Task 2.5.3: Trust Update Mechanism
**What to build:**
- Trigger trust updates after transactions
- Batch update process
- Cache invalidation

**Acceptance Criteria:**
- [ ] Trust scores update after transactions
- [ ] Performance acceptable
- [ ] Cache invalidated on updates
- [ ] Unit tests passing

**Definition of Done:**
- [ ] All tasks completed
- [ ] >90% test coverage
- [ ] Code reviewed
- [ ] Merged to main branch

---

### Story 2.6: Heartbeat Protocol 🔄 IN PROGRESS
**Story Points:** 5  
**Status:** NOT STARTED  
**Sprint Days:** Tue-Wed (Days 7-8)  
**Planned Start:** November 30, 2025

**Goal:** Monitor agent health via heartbeat messages (5-min interval)

**Tasks:**

#### Task 2.6.1: Heartbeat Endpoint
**What to build:**
- POST /ains/agents/{agent_id}/heartbeat
- Update last_heartbeat timestamp
- Record agent status

**Code structure:**
```python
class Heartbeat(BaseModel):
    timestamp: int  # Unix timestamp
    status: str  # ACTIVE, DEGRADED, OFFLINE
    uptime_ms: int  # Agent uptime in milliseconds
    metrics: Optional[dict] = None

@app.post("/ains/agents/{agent_id}/heartbeat")
def send_heartbeat(agent_id: str, heartbeat: Heartbeat):
    """
    Receive heartbeat from agent
    - Update last_heartbeat
    - Update status
    - Track uptime
    """
    agent = get_agent(agent_id)
    agent.last_heartbeat = datetime.utcnow()
    agent.status = heartbeat.status
    
    # Update uptime metrics
    update_uptime_metrics(agent_id, heartbeat.uptime_ms)
    
    # Invalidate cache
    cache.invalidate_agent(agent_id)
    
    return {"acknowledged": True, "next_heartbeat_in": 300}
```

**Acceptance Criteria:**
- [ ] Endpoint accepts heartbeats
- [ ] Updates last_heartbeat timestamp
- [ ] Tracks uptime
- [ ] Returns next heartbeat interval
- [ ] Unit tests passing

---

#### Task 2.6.2: Agent Status Monitoring
**What to build:**
- Mark agents as INACTIVE if no heartbeat for 10 minutes
- Batch status update process
- Monitoring alerts (optional)

**Code structure:**
```python
async def monitor_agent_health():
    """
    Monitoring task - runs every 60 seconds
    - Check for stale heartbeats
    - Mark agents as INACTIVE
    - Update trust scores
    """
    inactive_threshold = datetime.utcnow() - timedelta(minutes=10)
    
    # Find agents with stale heartbeats
    stale_agents = db.query(Agent).filter(
        Agent.last_heartbeat < inactive_threshold,
        Agent.status == 'ACTIVE'
    ).all()
    
    # Mark as inactive
    for agent in stale_agents:
        agent.status = 'INACTIVE'
        cache.invalidate_agent(agent.agent_id)
```

**Acceptance Criteria:**
- [ ] Monitors agent heartbeats
- [ ] Marks inactive agents correctly
- [ ] Updates trust scores
- [ ] Unit tests passing

---

#### Task 2.6.3: Integration Tests
**What to build:**
- Test heartbeat sending and receiving
- Test status transitions
- Test uptime calculation

**Acceptance Criteria:**
- [ ] Heartbeat tests passing
- [ ] Status monitoring tests passing
- [ ] Integration tests passing

**Definition of Done:**
- [ ] All tasks completed
- [ ] >90% test coverage
- [ ] Code reviewed
- [ ] Merged to main branch

---

## 🎯 Sprint 2 Schedule

### Week 1 (Nov 22-29)

**Monday Nov 25:**
- Sprint kickoff meeting
- Story 2.1: Agent Registration - Database setup
- Daily standup 9:00 AM CST

**Tuesday Nov 26:**
- Story 2.1: Registration endpoint
- Story 2.2 started: Agent Lookup setup
- Daily standup 9:00 AM CST

**Wednesday Nov 27:**
- Story 2.2: Complete agent lookup
- Story 2.3 started: Capability model
- Daily standup 9:00 AM CST

**Thursday Nov 28:**
- Thanksgiving - Optional work
- Story 2.3: Capability endpoint
- Daily standup (optional)

**Friday Nov 29:**
- Story 2.3: Capability search
- Code review and testing
- Daily standup (optional)

### Week 2 (Nov 30 - Dec 6)

**Monday Dec 1:**
- Story 2.4: Search implementation
- Story 2.5 started: Trust scores
- Daily standup 9:00 AM CST

**Tuesday Dec 2:**
- Story 2.4: Search optimization
- Story 2.5: Trust calculation
- Daily standup 9:00 AM CST

**Wednesday Dec 3:**
- Story 2.5: Trust updates
- Story 2.6 started: Heartbeat
- Daily standup 9:00 AM CST

**Thursday Dec 4:**
- Story 2.6: Status monitoring
- Testing and bug fixes
- Daily standup 9:00 AM CST

**Friday Dec 5:**
- Final integration testing
- Sprint review (demo day)
- Sprint retrospective
- Daily standup 9:00 AM CST

---

## 👥 Team Assignments

### Recommended Structure

| Role | Developer | Assignment |
| --- | --- | --- |
| **Tech Lead** | Immanuel Olajuyigbe | Stories 2.1, 2.2, Code review |
| **Backend Dev 1** | [TBD] | Story 2.3, 2.4 (Capabilities) |
| **Backend Dev 2** | [TBD] | Story 2.5, 2.6 (Trust & Health) |

### Daily Responsibilities

**Tech Lead:**
- Code reviews (2-3 hours/day)
- Unblock team members
- Architecture decisions
- Integration with AICP

**Backend Dev 1:**
- Implement Story 2.3, 2.4
- Write tests
- Integration testing
- Documentation

**Backend Dev 2:**
- Implement Story 2.5, 2.6
- Write tests
- Performance optimization
- Documentation

---

## 📊 Sprint Metrics & Success Criteria

### Completion Goals
| Story | Target | Actual | Status |
| --- | --- | --- | --- |
| 2.1: Registration | ✅ Done | TBD | In Progress |
| 2.2: Lookup | ✅ Done | TBD | Planned |
| 2.3: Capability | ✅ Done | TBD | Planned |
| 2.4: Search | ✅ Done | TBD | Planned |
| 2.5: Trust | ✅ Done | TBD | Planned |
| 2.6: Heartbeat | ✅ Done | TBD | Planned |
| **TOTAL** | **42 pts** | TBD | **On Track** |

### Quality Targets
| Metric | Target | Status |
| --- | --- | --- |
| Test Coverage | >90% | TBD |
| Tests Passing | 100% | TBD |
| Code Quality | >8.0 | TBD |
| Performance | Per targets | TBD |

---

## 🚀 Deliverables for Sprint 2

### Code
```
packages/ains-core/python/
├── ains/
│   ├── __init__.py
│   ├── db.py (Database models)
│   ├── cache.py (Redis caching)
│   ├── api.py (FastAPI endpoints)
│   ├── trust.py (Trust calculation)
│   └── health.py (Heartbeat monitoring)
├── tests/
│   ├── test_db.py
│   ├── test_cache.py
│   ├── test_api.py
│   ├── test_trust.py
│   ├── test_health.py
│   └── integration/
│       └── test_ains_aicp.py
├── migrations/ (Database migrations)
├── pyproject.toml
└── README.md
```

### Documentation
```
docs/
├── protocols/
│   └── AINS-Registry-Schema.md (Updated)
└── SPRINT_2_PLAN.md (This file)
```

---

## ⚠️ Risks & Mitigation

| Risk | Impact | Mitigation |
| --- | --- | --- |
| DB connection issues | High | Set up PostgreSQL early, test connections |
| Redis cache performance | Medium | Performance test daily, optimize queries |
| Trust calculation bugs | Critical | Unit tests first, security review |
| Search performance | Medium | Index optimization, query profiling |

---

## ✅ Definition of Done for Sprint 2

A story is **DONE** when:
1. **Code Complete** - All acceptance criteria implemented
2. **Testing** - >90% coverage, integration tests pass
3. **Documentation** - Code docs, API docs, examples
4. **Review** - Code reviewed and approved
5. **Deployment** - Merged to main, CI/CD passes
6. **Acceptance** - Product Owner approves

---

## 🎉 Success Looks Like

**By Friday December 5, 2025 at 5 PM CST:**

✅ 6 stories completed (42 story points)
✅ Full agent registry working
✅ Search and discovery operational
✅ Trust scoring implemented
✅ Heartbeat monitoring active
✅ >90% code coverage
✅ All tests passing
✅ Demo with real agent discovery
✅ Ready for AITP integration

---

## 🚀 Impact on Product

**After Sprint 2:**
- Agents can register themselves ✅
- Agents can discover other agents ✅
- Trust system working ✅
- Health monitoring active ✅
- Ready for Sprint 3: AITP (Task Protocol)

---

**Sprint 2 is READY TO LAUNCH! 🚀**

Start with Story 2.1: Agent Registration API on November 22, 2025
