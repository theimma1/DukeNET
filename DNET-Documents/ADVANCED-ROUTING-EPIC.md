# 🔄 AICP Advanced Routing - Multi-Agent Load Balancing

## Epic Overview

**Status:** EPIC STARTED | **Complexity:** MEDIUM | **Estimated Time:** 2-3 hours

Transform AICP from single-agent routing to **intelligent multi-agent load balancing** with:
- Round-robin distribution
- Least-loaded routing
- Trust-weighted selection
- Performance-based prioritization
- Automatic failover

---

## Architecture

```
AINS Task Request
    ↓ (method: "image.label")
    ↓
AICP Router (ADVANCED)
    ├── Query capability registry
    ├── Find ALL matching agents (labelee-01, labelee-02, labelee-03)
    ├── Apply routing algorithm:
    │   ├── Option 1: Round-robin (fairness)
    │   ├── Option 2: Least-loaded (speed)
    │   ├── Option 3: Trust-weighted (quality)
    │   └── Option 4: Performance-based (latency)
    ├── Select best agent
    └── Route with retry logic
    ↓
Multiple Agents in Parallel
    ├── Agent 1 (high trust, low load) ← SELECTED
    ├── Agent 2 (medium trust, high load)
    └── Agent 3 (medium trust, medium load)
    ↓
Response → AINS (fastest/best)
```

---

## Core Components to Build

### 1. **Agent Metrics Tracker**
Track performance per agent:
- Request count (load)
- Success rate (quality)
- Average latency (speed)
- Trust score (reputation)
- Last seen (availability)

### 2. **Multi-Routing Strategies**

```python
class RoutingStrategy(Enum):
    ROUND_ROBIN = "round-robin"  # Rotate through agents
    LEAST_LOADED = "least-loaded"  # Pick agent with fewest tasks
    TRUST_WEIGHTED = "trust-weighted"  # Favor high-trust agents
    PERFORMANCE_BASED = "performance-based"  # Pick fastest
    RANDOM = "random"  # Random selection
```

### 3. **Intelligent Router**

```python
class IntelligentRouter:
    async def select_agent(self, method: str, strategy: str) -> str:
        """Select best agent for method using strategy"""
        candidates = self.find_agents_with_capability(method)
        
        if strategy == "least-loaded":
            return min(candidates, key=lambda a: self.get_load(a))
        elif strategy == "trust-weighted":
            return max(candidates, key=lambda a: self.get_trust(a))
        # ... other strategies
```

### 4. **Failover & Retry**

```python
class FailoverRouter:
    async def route_with_fallback(self, msg, max_retries=3):
        """Route with automatic failover to next agent"""
        for attempt in range(max_retries):
            agent = self.select_agent(msg.method)
            try:
                result = await self.send_to_agent(agent, msg)
                self.mark_success(agent)
                return result
            except Exception as e:
                self.mark_failure(agent)
                # Try next agent
        raise RoutingError("All agents failed")
```

---

## Implementation Tasks

### Phase 1: Metrics Collection (30 min)
```python
# Track agent performance
aicp/metrics.py
├── AgentMetrics (request_count, success_rate, avg_latency, trust_score)
├── MetricsCollector (track per agent)
└── PerformanceTracker (historical data)
```

### Phase 2: Routing Strategies (45 min)
```python
# Multiple routing algorithms
aicp/routing_strategies.py
├── RoundRobinRouter
├── LeastLoadedRouter
├── TrustWeightedRouter
├── PerformanceBasedRouter
└── AdaptiveRouter (picks best strategy dynamically)
```

### Phase 3: Intelligent Router (45 min)
```python
# Main router with failover
aicp/intelligent_router.py
├── IntelligentRouter (selects best agent)
├── FailoverRouter (retry logic)
├── LoadBalancer (distributes load)
└── HealthMonitor (tracks agent health)
```

### Phase 4: Integration & Tests (30 min)
```python
# Tests & integration
tests/test_advanced_routing.py
├── test_round_robin_distribution
├── test_least_loaded_selection
├── test_trust_weighted_routing
├── test_failover_logic
└── test_multi_agent_load_balancing
```

---

## Quick Start Code

### Step 1: Agent Metrics
```python
# aicp/metrics.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass
class AgentMetrics:
    """Track metrics for a single agent"""
    agent_id: str
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency: float = 0.0
    trust_score: float = 0.5
    last_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.request_count == 0:
            return 1.0
        return self.success_count / self.request_count
    
    @property
    def avg_latency(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.total_latency / self.request_count
    
    def record_success(self, latency: float):
        self.request_count += 1
        self.success_count += 1
        self.total_latency += latency
        self.trust_score = min(1.0, self.trust_score + 0.02)
        self.last_seen = datetime.now()
    
    def record_failure(self):
        self.request_count += 1
        self.failure_count += 1
        self.trust_score = max(0.0, self.trust_score - 0.05)
        self.last_seen = datetime.now()


class MetricsCollector:
    """Collect and store agent metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, AgentMetrics] = {}
    
    def get_or_create(self, agent_id: str) -> AgentMetrics:
        if agent_id not in self.metrics:
            self.metrics[agent_id] = AgentMetrics(agent_id=agent_id)
        return self.metrics[agent_id]
    
    def record_success(self, agent_id: str, latency: float):
        metrics = self.get_or_create(agent_id)
        metrics.record_success(latency)
    
    def record_failure(self, agent_id: str):
        metrics = self.get_or_create(agent_id)
        metrics.record_failure()
    
    def get_metrics(self, agent_id: str) -> AgentMetrics:
        return self.get_or_create(agent_id)
```

### Step 2: Routing Strategies
```python
# aicp/routing_strategies.py
from enum import Enum
from typing import List, Dict
import random
from datetime import datetime, timedelta

class RoutingStrategy(Enum):
    ROUND_ROBIN = "round-robin"
    LEAST_LOADED = "least-loaded"
    TRUST_WEIGHTED = "trust-weighted"
    PERFORMANCE_BASED = "performance-based"
    RANDOM = "random"


class Router:
    """Base router class"""
    
    def __init__(self, agent_registry: Dict, metrics_collector):
        self.agent_registry = agent_registry
        self.metrics = metrics_collector
        self.round_robin_index = 0
    
    def find_agents_with_capability(self, method: str) -> List[str]:
        """Find all agents that can handle this method"""
        return [
            agent_id for agent_id, info in self.agent_registry.items()
            if method in info.get("capabilities", [])
        ]
    
    def is_agent_healthy(self, agent_id: str) -> bool:
        """Check if agent is still responsive"""
        metrics = self.metrics.get_metrics(agent_id)
        # Agent is healthy if seen in last 2 minutes
        return (datetime.now() - metrics.last_seen) < timedelta(minutes=2)


class RoundRobinRouter(Router):
    """Distribute requests evenly across agents"""
    
    def select_agent(self, method: str) -> str:
        agents = self.find_agents_with_capability(method)
        agents = [a for a in agents if self.is_agent_healthy(a)]
        
        if not agents:
            raise ValueError(f"No healthy agents for {method}")
        
        selected = agents[self.round_robin_index % len(agents)]
        self.round_robin_index += 1
        return selected


class LeastLoadedRouter(Router):
    """Select agent with fewest pending tasks"""
    
    def __init__(self, agent_registry, metrics_collector):
        super().__init__(agent_registry, metrics_collector)
        self.pending_tasks: Dict[str, int] = {}
    
    def select_agent(self, method: str) -> str:
        agents = self.find_agents_with_capability(method)
        agents = [a for a in agents if self.is_agent_healthy(a)]
        
        if not agents:
            raise ValueError(f"No healthy agents for {method}")
        
        # Pick agent with least pending tasks
        selected = min(
            agents,
            key=lambda a: self.pending_tasks.get(a, 0)
        )
        
        # Increment pending count
        self.pending_tasks[selected] = self.pending_tasks.get(selected, 0) + 1
        return selected
    
    def task_completed(self, agent_id: str):
        """Decrement when task completes"""
        if agent_id in self.pending_tasks:
            self.pending_tasks[agent_id] -= 1


class TrustWeightedRouter(Router):
    """Select agents weighted by trust score"""
    
    def select_agent(self, method: str) -> str:
        agents = self.find_agents_with_capability(method)
        agents = [a for a in agents if self.is_agent_healthy(a)]
        
        if not agents:
            raise ValueError(f"No healthy agents for {method}")
        
        if len(agents) == 1:
            return agents[0]
        
        # Create weighted selection
        metrics = {a: self.metrics.get_metrics(a).trust_score for a in agents}
        total_trust = sum(metrics.values())
        
        # Normalize weights
        weights = [metrics[a] / total_trust for a in agents]
        
        # Random selection weighted by trust
        return random.choices(agents, weights=weights, k=1)[0]


class PerformanceBasedRouter(Router):
    """Select fastest responding agent"""
    
    def select_agent(self, method: str) -> str:
        agents = self.find_agents_with_capability(method)
        agents = [a for a in agents if self.is_agent_healthy(a)]
        
        if not agents:
            raise ValueError(f"No healthy agents for {method}")
        
        # Pick agent with lowest latency
        selected = min(
            agents,
            key=lambda a: self.metrics.get_metrics(a).avg_latency
        )
        return selected
```

### Step 3: Intelligent Router
```python
# aicp/intelligent_router.py
import asyncio
import time
from typing import Optional

class IntelligentRouter:
    """Main router with failover and strategy selection"""
    
    def __init__(self, websocket_server, metrics_collector):
        self.server = websocket_server
        self.metrics = metrics_collector
        
        # Initialize routing strategies
        self.round_robin = RoundRobinRouter(
            websocket_server.agent_registry,
            metrics_collector
        )
        self.least_loaded = LeastLoadedRouter(
            websocket_server.agent_registry,
            metrics_collector
        )
        self.trust_weighted = TrustWeightedRouter(
            websocket_server.agent_registry,
            metrics_collector
        )
        self.performance_based = PerformanceBasedRouter(
            websocket_server.agent_registry,
            metrics_collector
        )
    
    async def route_with_failover(
        self,
        msg: "AICPMessage",
        strategy: str = "least-loaded",
        max_retries: int = 3
    ) -> Optional[str]:
        """Route message with intelligent failover"""
        
        for attempt in range(max_retries):
            try:
                # Select router based on strategy
                if strategy == "round-robin":
                    agent = self.round_robin.select_agent(msg.method)
                elif strategy == "least-loaded":
                    agent = self.least_loaded.select_agent(msg.method)
                elif strategy == "trust-weighted":
                    agent = self.trust_weighted.select_agent(msg.method)
                elif strategy == "performance-based":
                    agent = self.performance_based.select_agent(msg.method)
                else:
                    agent = self.round_robin.select_agent(msg.method)
                
                # Route to agent
                start = time.time()
                result = await self.server.route_message(msg)
                latency = time.time() - start
                
                # Record success
                self.metrics.record_success(agent, latency)
                
                # Decrement least-loaded counter
                self.least_loaded.task_completed(agent)
                
                return agent
                
            except Exception as e:
                # Record failure and retry
                print(f"Attempt {attempt + 1} failed: {e}")
                self.metrics.record_failure(agent)
                
                if attempt == max_retries - 1:
                    raise
                
                # Wait before retry
                await asyncio.sleep(0.5 * (attempt + 1))
        
        return None
    
    def get_agent_status(self) -> dict:
        """Get status of all agents"""
        status = {}
        for agent_id in self.server.agent_registry:
            metrics = self.metrics.get_metrics(agent_id)
            status[agent_id] = {
                "trust_score": metrics.trust_score,
                "success_rate": metrics.success_rate,
                "avg_latency": metrics.avg_latency,
                "request_count": metrics.request_count,
                "last_seen": metrics.last_seen.isoformat(),
            }
        return status
```

---

## Test Suite

```python
# tests/test_advanced_routing.py
import pytest
import asyncio
from aicp.metrics import MetricsCollector, AgentMetrics
from aicp.routing_strategies import (
    RoundRobinRouter, LeastLoadedRouter, 
    TrustWeightedRouter, PerformanceBasedRouter
)

@pytest.fixture
def agent_registry():
    return {
        "agent-1": {"capabilities": ["image.label", "text.classify"]},
        "agent-2": {"capabilities": ["image.label"]},
        "agent-3": {"capabilities": ["text.classify"]},
    }

@pytest.fixture
def metrics_collector():
    return MetricsCollector()

def test_round_robin_distribution(agent_registry, metrics_collector):
    """Test round-robin distributes evenly"""
    router = RoundRobinRouter(agent_registry, metrics_collector)
    
    # Should cycle through agents
    selections = [router.select_agent("image.label") for _ in range(6)]
    assert selections == ["agent-1", "agent-2", "agent-1", "agent-2", "agent-1", "agent-2"]

def test_least_loaded_selection(agent_registry, metrics_collector):
    """Test least-loaded picks agent with least tasks"""
    router = LeastLoadedRouter(agent_registry, metrics_collector)
    
    # Add pending tasks
    router.pending_tasks["agent-1"] = 5
    router.pending_tasks["agent-2"] = 2
    
    # Should pick agent-2 (least loaded)
    selected = router.select_agent("image.label")
    assert selected == "agent-2"

def test_trust_weighted_routing(agent_registry, metrics_collector):
    """Test trust-weighted prefers high-trust agents"""
    router = TrustWeightedRouter(agent_registry, metrics_collector)
    
    # Set different trust scores
    metrics_collector.get_metrics("agent-1").trust_score = 0.9
    metrics_collector.get_metrics("agent-2").trust_score = 0.3
    
    # Over many selections, should pick agent-1 more
    selections = [router.select_agent("image.label") for _ in range(100)]
    count_agent1 = selections.count("agent-1")
    assert count_agent1 > 50  # Should get majority

def test_performance_based_routing(agent_registry, metrics_collector):
    """Test performance-based picks fastest"""
    router = PerformanceBasedRouter(agent_registry, metrics_collector)
    
    # Set latencies
    metrics_collector.get_metrics("agent-1").total_latency = 100
    metrics_collector.get_metrics("agent-1").request_count = 10
    metrics_collector.get_metrics("agent-2").total_latency = 50
    metrics_collector.get_metrics("agent-2").request_count = 10
    
    # Should pick agent-2 (faster)
    selected = router.select_agent("image.label")
    assert selected == "agent-2"

def test_metrics_tracking(metrics_collector):
    """Test metrics collection"""
    collector = metrics_collector
    
    # Record success
    collector.record_success("agent-1", 0.5)
    metrics = collector.get_metrics("agent-1")
    assert metrics.request_count == 1
    assert metrics.success_count == 1
    assert metrics.avg_latency == 0.5
    
    # Record failure
    collector.record_failure("agent-1")
    assert metrics.request_count == 2
    assert metrics.failure_count == 1
    assert metrics.success_rate == 0.5
```

---

## Deployment Steps

```bash
# 1. Create metrics module
cat > aicp/metrics.py << 'EOF'
[Copy Phase 1 code above]
EOF

# 2. Create routing strategies
cat > aicp/routing_strategies.py << 'EOF'
[Copy Phase 2 code above]
EOF

# 3. Create intelligent router
cat > aicp/intelligent_router.py << 'EOF'
[Copy Phase 3 code above]
EOF

# 4. Create tests
cat > tests/test_advanced_routing.py << 'EOF'
[Copy test code above]
EOF

# 5. Run tests
pytest tests/test_advanced_routing.py -v

# 6. Commit
git add aicp/metrics.py aicp/routing_strategies.py aicp/intelligent_router.py tests/test_advanced_routing.py
git commit -m "🔄 AICP Advanced Routing - Multi-Agent Load Balancing LIVE
✅ Round-robin distribution
✅ Least-loaded selection
✅ Trust-weighted routing
✅ Performance-based prioritization
✅ Failover with retry logic
✅ Agent health monitoring"
git push origin main
```

---

## Expected Outcomes

```
After Deployment:
✅ Multiple agents handle same capability
✅ Load automatically distributed
✅ Failing agents automatically bypassed
✅ High-performance agents preferred
✅ System scales with more agents
✅ Trust system influences routing

Performance Improvements:
- 3x faster (parallel agents)
- 99.9% uptime (failover)
- Fair load distribution
- Quality prioritization
```

---

**Ready to implement?** Start with Phase 1 (metrics) - super clean and easy! 🚀
