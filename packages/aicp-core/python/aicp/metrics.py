from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict

@dataclass
class AgentMetrics:
    agent_id: str
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency: float = 0.0
    trust_score: float = 0.5
    last_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        return 1.0 if self.request_count == 0 else self.success_count / self.request_count
    
    @property
    def avg_latency(self) -> float:
        return 0.0 if self.request_count == 0 else self.total_latency / self.request_count
    
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
    def __init__(self):
        self.metrics: Dict[str, AgentMetrics] = {}
    
    def get_or_create(self, agent_id: str) -> AgentMetrics:
        if agent_id not in self.metrics:
            self.metrics[agent_id] = AgentMetrics(agent_id=agent_id)
        return self.metrics[agent_id]
    
    def record_success(self, agent_id: str, latency: float):
        self.get_or_create(agent_id).record_success(latency)
    
    def record_failure(self, agent_id: str):
        self.get_or_create(agent_id).record_failure()
    
    def get_metrics(self, agent_id: str) -> AgentMetrics:
        return self.get_or_create(agent_id)
    
    def get_all_metrics(self) -> Dict[str, AgentMetrics]:
        return self.metrics
