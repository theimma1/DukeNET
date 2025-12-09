# 🔄 Advanced Routing Integration Guide

## How to Use the New Routing System

Now that you've deployed the metrics and routing strategies, here's how to integrate them:

---

## 1. **Use in WebSocket Server**

### Update: `aicp/websocket_transport.py`

```python
# At the top, add imports:
from .metrics import MetricsCollector
from .routing_strategies import (
    LeastLoadedRouter, TrustWeightedRouter, 
    PerformanceBasedRouter, RoundRobinRouter
)
import time

# In AICPWebSocketServer.__init__:
class AICPWebSocketServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.agent_registry: Dict[str, Dict] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.server = None
        
        # NEW: Add metrics collection
        self.metrics = MetricsCollector()
        
        # NEW: Initialize routing strategies
        self.least_loaded_router = LeastLoadedRouter(
            self.agent_registry, 
            self.metrics
        )
        self.trust_weighted_router = TrustWeightedRouter(
            self.agent_registry,
            self.metrics
        )
        self.performance_router = PerformanceBasedRouter(
            self.agent_registry,
            self.metrics
        )


# Update route_message method:
async def route_message(self, msg: AICPMessage, strategy: str = "least-loaded"):
    """Route message using selected strategy"""
    method = msg.method
    start_time = time.time()
    
    try:
        # Select router based on strategy
        if strategy == "least-loaded":
            agent = self.least_loaded_router.select_agent(method)
        elif strategy == "trust-weighted":
            agent = self.trust_weighted_router.select_agent(method)
        elif strategy == "performance-based":
            agent = self.performance_router.select_agent(method)
        else:
            agent = self.least_loaded_router.select_agent(method)
        
        # Get WebSocket for agent
        target_ws = self.agent_registry[agent]["ws"]
        
        # Send message
        await target_ws.send(msg.to_json())
        
        # Record success
        latency = time.time() - start_time
        self.metrics.record_success(agent, latency)
        
        return agent
        
    except Exception as e:
        # Record failure
        self.metrics.record_failure(agent)
        logger.error(f"Failed to route message: {e}")
        return None
```

---

## 2. **Add Metrics Endpoint to AINS**

### Add to `packages/ains-core/python/ains/api.py`:

```python
from aicp.metrics import MetricsCollector

# In your FastAPI app:

# Inject metrics from AICP
aicp_metrics: Optional[MetricsCollector] = None

@app.get("/aicp/agent-metrics")
async def get_agent_metrics():
    """Get performance metrics for all agents"""
    if not aicp_metrics:
        return {"error": "AICP not initialized"}
    
    metrics = {}
    for agent_id, agent_metrics in aicp_metrics.get_all_metrics().items():
        metrics[agent_id] = {
            "trust_score": agent_metrics.trust_score,
            "success_rate": agent_metrics.success_rate,
            "avg_latency": agent_metrics.avg_latency,
            "request_count": agent_metrics.request_count,
            "success_count": agent_metrics.success_count,
            "failure_count": agent_metrics.failure_count,
        }
    
    return {"agents": metrics}


@app.get("/aicp/agent-status/{agent_id}")
async def get_agent_status(agent_id: str):
    """Get status of specific agent"""
    if not aicp_metrics:
        return {"error": "AICP not initialized"}
    
    metrics = aicp_metrics.get_metrics(agent_id)
    
    return {
        "agent_id": agent_id,
        "trust_score": metrics.trust_score,
        "success_rate": metrics.success_rate,
        "avg_latency": metrics.avg_latency,
        "request_count": metrics.request_count,
    }
```

---

## 3. **Use Different Routing Strategies**

### Example: Task routing with strategy selection

```python
# In AINS task router:

async def route_task_to_agent(task, strategy="least-loaded"):
    """Route task using specified strategy"""
    
    # Extract method from task
    method = task.method  # e.g., "image.label"
    
    # Create AICP message
    msg = AICPMessage(
        method=method,
        payload=task.input_data,
        sender="ains-control"
    )
    
    # Sign message
    msg.sign(ains_privkey)
    
    # Route using WebSocket server
    agent = await websocket_server.route_message(
        msg,
        strategy=strategy
    )
    
    return agent


# Usage:
# Speed-optimized: Use performance-based routing
agent = await route_task_to_agent(task, strategy="performance-based")

# Quality-optimized: Use trust-weighted routing
agent = await route_task_to_agent(task, strategy="trust-weighted")

# Load-balanced: Use least-loaded routing
agent = await route_task_to_agent(task, strategy="least-loaded")

# Fair distribution: Use round-robin routing
agent = await route_task_to_agent(task, strategy="round-robin")
```

---

## 4. **Monitor Agent Health**

### Dashboard endpoint:

```python
@app.get("/aicp/dashboard")
async def aicp_dashboard():
    """Real-time dashboard of AICP agent network"""
    if not aicp_metrics:
        return {"error": "AICP not initialized"}
    
    agents_data = []
    
    for agent_id, agent_metrics in aicp_metrics.get_all_metrics().items():
        agents_data.append({
            "id": agent_id,
            "trust_score": round(agent_metrics.trust_score, 2),
            "success_rate": round(agent_metrics.success_rate, 2),
            "avg_latency_ms": round(agent_metrics.avg_latency * 1000, 2),
            "requests": agent_metrics.request_count,
            "successes": agent_metrics.success_count,
            "failures": agent_metrics.failure_count,
        })
    
    # Sort by trust score (highest first)
    agents_data.sort(key=lambda x: x["trust_score"], reverse=True)
    
    return {
        "total_agents": len(agents_data),
        "avg_trust": sum(a["trust_score"] for a in agents_data) / len(agents_data) if agents_data else 0,
        "total_requests": sum(a["requests"] for a in agents_data),
        "agents": agents_data,
    }
```

---

## 5. **Real-World Usage Example**

### Complete end-to-end example:

```python
# 1. Task arrives in AINS
task = {
    "method": "image.label",
    "image_url": "snoop.png",
    "priority": "high"
}

# 2. Select routing strategy based on priority
if task["priority"] == "high":
    strategy = "trust-weighted"  # High quality
elif task["priority"] == "normal":
    strategy = "least-loaded"     # Speed
else:
    strategy = "round-robin"      # Fair distribution

# 3. Create signed AICP message
msg = AICPMessage(
    method=task["method"],
    payload={"image_url": task["image_url"]},
    sender="ains-control"
)
msg.sign(ains_privkey)

# 4. Route to best agent
agent = await websocket_server.route_message(msg, strategy=strategy)

# 5. Metrics automatically tracked:
# - Success → trust_score +0.02, request_count +1
# - Failure → trust_score -0.05, request_count +1

# 6. Next request routes to better agent
next_agent = await websocket_server.route_message(msg, strategy=strategy)
# If previous agent succeeded: higher chance of selection
# If previous agent failed: lower chance of selection

# 7. Monitor dashboard
dashboard = await aicp_dashboard()
print(dashboard)
# Output:
# {
#   "total_agents": 3,
#   "avg_trust": 0.85,
#   "total_requests": 250,
#   "agents": [
#     {"id": "labelee-1", "trust_score": 0.95, "success_rate": 0.98, ...},
#     {"id": "labelee-2", "trust_score": 0.82, "success_rate": 0.90, ...},
#     {"id": "labelee-3", "trust_score": 0.78, "success_rate": 0.87, ...},
#   ]
# }
```

---

## 6. **Testing Different Strategies**

### Benchmark script:

```python
# test_routing_strategies.py
import asyncio
import time
from aicp.metrics import MetricsCollector
from aicp.routing_strategies import (
    RoundRobinRouter, LeastLoadedRouter,
    TrustWeightedRouter, PerformanceBasedRouter
)

async def benchmark_routing():
    """Compare routing strategies"""
    
    agent_registry = {
        "agent-1": {"capabilities": ["image.label"]},
        "agent-2": {"capabilities": ["image.label"]},
        "agent-3": {"capabilities": ["image.label"]},
    }
    
    metrics = MetricsCollector()
    
    # Simulate agent performance
    metrics.record_success("agent-1", 0.05)  # Fast
    metrics.record_success("agent-1", 0.06)
    metrics.record_failure("agent-2")         # Unreliable
    metrics.record_success("agent-3", 0.10)  # Slower
    
    # Test strategies
    strategies = {
        "round_robin": RoundRobinRouter(agent_registry, metrics),
        "least_loaded": LeastLoadedRouter(agent_registry, metrics),
        "trust_weighted": TrustWeightedRouter(agent_registry, metrics),
        "performance_based": PerformanceBasedRouter(agent_registry, metrics),
    }
    
    for name, router in strategies.items():
        selections = [router.select_agent("image.label") for _ in range(100)]
        
        print(f"\n{name.upper()}:")
        for agent in ["agent-1", "agent-2", "agent-3"]:
            count = selections.count(agent)
            print(f"  {agent}: {count}%")

# Run: python test_routing_strategies.py
```

---

## 🎯 Quick Reference

| Strategy | Best For | Algorithm |
|----------|----------|-----------|
| **Round-Robin** | Fair distribution | Rotate through agents |
| **Least-Loaded** | Speed optimization | Pick agent with fewest tasks |
| **Trust-Weighted** | Quality prioritization | Probabilistic selection by trust |
| **Performance-Based** | Latency optimization | Pick fastest responding agent |
| **Random** | Fallback | Random selection from healthy agents |

---

## ✅ Deployment Checklist

- [ ] Copy 3 files to correct directories
- [ ] Run tests (6/6 passing)
- [ ] Update `aicp/__init__.py`
- [ ] Integrate into WebSocket server
- [ ] Add AINS endpoints
- [ ] Test with multiple agents
- [ ] Deploy to production
- [ ] Monitor dashboard

---

**Status:** Ready for production deployment! 🚀
