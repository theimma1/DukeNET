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
    def __init__(self, agent_registry: Dict, metrics_collector):
        self.agent_registry = agent_registry
        self.metrics = metrics_collector
        self.round_robin_index = 0
    
    def find_agents_with_capability(self, method: str) -> List[str]:
        return [a for a, i in self.agent_registry.items() if method in i.get("capabilities", [])]
    
    def is_agent_healthy(self, agent_id: str) -> bool:
        return (datetime.now() - self.metrics.get_metrics(agent_id).last_seen) < timedelta(minutes=2)

class RoundRobinRouter(Router):
    def select_agent(self, method: str) -> str:
        agents = [a for a in self.find_agents_with_capability(method) if self.is_agent_healthy(a)]
        if not agents: raise ValueError(f"No healthy agents for {method}")
        selected = agents[self.round_robin_index % len(agents)]
        self.round_robin_index += 1
        return selected

class LeastLoadedRouter(Router):
    def __init__(self, agent_registry, metrics_collector):
        super().__init__(agent_registry, metrics_collector)
        self.pending_tasks: Dict[str, int] = {}
    
    def select_agent(self, method: str) -> str:
        agents = [a for a in self.find_agents_with_capability(method) if self.is_agent_healthy(a)]
        if not agents: raise ValueError(f"No healthy agents for {method}")
        selected = min(agents, key=lambda a: self.pending_tasks.get(a, 0))
        self.pending_tasks[selected] = self.pending_tasks.get(selected, 0) + 1
        return selected
    
    def task_completed(self, agent_id: str):
        if agent_id in self.pending_tasks:
            self.pending_tasks[agent_id] = max(0, self.pending_tasks[agent_id] - 1)

class TrustWeightedRouter(Router):
    def select_agent(self, method: str) -> str:
        agents = [a for a in self.find_agents_with_capability(method) if self.is_agent_healthy(a)]
        if not agents: raise ValueError(f"No healthy agents for {method}")
        if len(agents) == 1: return agents[0]
        metrics = {a: self.metrics.get_metrics(a).trust_score for a in agents}
        total = sum(metrics.values())
        weights = [metrics[a] / total for a in agents]
        return random.choices(agents, weights=weights, k=1)[0]

class PerformanceBasedRouter(Router):
    def select_agent(self, method: str) -> str:
        agents = [a for a in self.find_agents_with_capability(method) if self.is_agent_healthy(a)]
        if not agents: raise ValueError(f"No healthy agents for {method}")
        return min(agents, key=lambda a: self.metrics.get_metrics(a).avg_latency)

class RandomRouter(Router):
    def select_agent(self, method: str) -> str:
        agents = [a for a in self.find_agents_with_capability(method) if self.is_agent_healthy(a)]
        if not agents: raise ValueError(f"No healthy agents for {method}")
        return random.choice(agents)
