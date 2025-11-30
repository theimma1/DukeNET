"""Agent Reputation & Scoring System"""

from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum
from datetime import datetime

class TaskOutcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PARTIAL = "partial"

@dataclass
class AgentReputation:
    """Track agent reputation metrics"""
    agent_id: str
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    total_tasks: int = 0
    total_earnings: float = 0.0
    avg_response_time_ms: float = 100.0
    specialization_bonus: float = 1.0  # 1.0 = base, 1.5 = specialist
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        if self.total_tasks == 0:
            return 0.0
        return self.success_count / self.total_tasks
    
    @property
    def reputation_multiplier(self) -> float:
        """0.5 (poor) to 2.0 (excellent)"""
        base = self.success_rate
        if base >= 0.95:
            return 2.0  # Excellent: 2x price
        elif base >= 0.90:
            return 1.8
        elif base >= 0.80:
            return 1.5
        elif base >= 0.70:
            return 1.2
        elif base >= 0.60:
            return 1.0
        else:
            return 0.5  # Poor: 50% price
    
    @property
    def reliability_score(self) -> float:
        """Calculate reliability based on uptime"""
        timeouts = self.timeout_count
        if self.total_tasks == 0:
            return 0.5
        timeout_rate = timeouts / self.total_tasks
        return max(0.0, 1.0 - timeout_rate)
    
    def record_success(self, response_time_ms: float):
        """Record successful task"""
        self.success_count += 1
        self.total_tasks += 1
        self.avg_response_time_ms = (
            (self.avg_response_time_ms * (self.total_tasks - 1) + response_time_ms) 
            / self.total_tasks
        )
    
    def record_failure(self):
        """Record failed task"""
        self.failure_count += 1
        self.total_tasks += 1
    
    def record_timeout(self):
        """Record timeout"""
        self.timeout_count += 1
        self.total_tasks += 1
    
    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "success_rate": f"{self.success_rate * 100:.1f}%",
            "total_tasks": self.total_tasks,
            "reputation_multiplier": f"{self.reputation_multiplier:.2f}x",
            "avg_response_time_ms": f"{self.avg_response_time_ms:.0f}ms",
            "total_earnings": f"{self.total_earnings:.2f}",
        }

class ReputationSystem:
    """Track and manage agent reputation"""
    
    def __init__(self):
        self.agents: Dict[str, AgentReputation] = {}
    
    def register_agent(self, agent_id: str) -> AgentReputation:
        """Register new agent"""
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentReputation(agent_id=agent_id)
        return self.agents[agent_id]
    
    def get_reputation(self, agent_id: str) -> AgentReputation:
        """Get agent reputation"""
        return self.agents.get(agent_id)
    
    def record_outcome(self, agent_id: str, outcome: TaskOutcome, response_time_ms: float = 0.0):
        """Record task outcome"""
        if agent_id not in self.agents:
            self.register_agent(agent_id)
        
        rep = self.agents[agent_id]
        if outcome == TaskOutcome.SUCCESS:
            rep.record_success(response_time_ms)
        elif outcome == TaskOutcome.FAILURE:
            rep.record_failure()
        elif outcome == TaskOutcome.TIMEOUT:
            rep.record_timeout()
    
    def get_price_multiplier(self, agent_id: str) -> float:
        """Get reputation-based price multiplier"""
        if agent_id not in self.agents:
            return 1.0
        return self.agents[agent_id].reputation_multiplier
    
    def get_all_reputations(self) -> Dict[str, Dict]:
        """Get all agent reputations"""
        return {
            agent_id: rep.to_dict()
            for agent_id, rep in self.agents.items()
        }
    
    def leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top agents by reputation"""
        sorted_agents = sorted(
            self.agents.values(),
            key=lambda r: r.success_rate,
            reverse=True
        )
        return [
            rep.to_dict()
            for rep in sorted_agents[:limit]
        ]
