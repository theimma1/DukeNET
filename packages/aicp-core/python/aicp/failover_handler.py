from typing import List, Dict, Any
from datetime import datetime
from aicp.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState

class FailoverRouter:
    def __init__(self, max_retries: int = 3):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            half_open_max_calls=3,
            backoff_multiplier=1.5,
        )
        self.max_retries = max_retries
        self.routing_log: List[Dict] = []
        
    async def route_task(self, task_id: str, agents: List[str], task_func, *args, **kwargs) -> Any:
        for attempt_num in range(self.max_retries):
            for agent_id in agents:
                try:
                    state = self.circuit_breaker.get_state(agent_id)
                    
                    if state == CircuitState.OPEN:
                        self._log_routing(task_id, agent_id, "SKIPPED", "Circuit OPEN")
                        continue
                    
                    print(f"📤 Routing {task_id} to {agent_id}")
                    result = await self.circuit_breaker.call_async(agent_id, task_func(agent_id, *args, **kwargs))
                    
                    self._log_routing(task_id, agent_id, "SUCCESS", "OK")
                    print(f"✅ Task {task_id} succeeded on {agent_id}")
                    return result
                    
                except CircuitBreakerOpen:
                    self._log_routing(task_id, agent_id, "REJECTED", "Circuit OPEN")
                except Exception as e:
                    self._log_routing(task_id, agent_id, "FAILED", str(e))
                    print(f"❌ {agent_id}: {e}")
        
        raise AllAgentsFailed(f"Task {task_id} failed on all agents")
    
    def _log_routing(self, task_id: str, agent_id: str, status: str, reason: str):
        self.routing_log.append({
            "task_id": task_id,
            "agent_id": agent_id,
            "status": status,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_health_status(self) -> Dict[str, Any]:
        all_metrics = self.circuit_breaker.get_all_metrics()
        open_circuits = sum(1 for m in all_metrics.values() if m["state"] == "open")
        half_open = sum(1 for m in all_metrics.values() if m["state"] == "half_open")
        
        return {
            "total_agents": len(all_metrics),
            "open_circuits": open_circuits,
            "half_open_circuits": half_open,
            "healthy_agents": len(all_metrics) - open_circuits - half_open,
            "agents": all_metrics,
            "routing_events": len(self.routing_log),
        }
    
    def get_recent_failures(self, limit: int = 20) -> List[Dict]:
        return [e for e in reversed(self.routing_log) if e["status"] != "SUCCESS"][-limit:]
    
    def reset_agent(self, agent_id: str):
        self.circuit_breaker.reset(agent_id)

class AllAgentsFailed(Exception):
    pass
