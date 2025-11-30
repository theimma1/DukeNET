"""Intelligent Task Scheduler"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

class AgentCapability(Enum):
    IMAGE_PROCESSING = "image_processing"
    NLP = "nlp"
    DATA_ANALYSIS = "data_analysis"
    CODE_EXECUTION = "code_execution"

@dataclass
class AgentProfile:
    """Agent capability profile"""
    agent_id: str
    capabilities: List[AgentCapability]
    max_concurrent_tasks: int = 10
    current_load: int = 0
    success_rate: float = 0.95
    avg_response_time_ms: float = 100.0
    
    @property
    def available_capacity(self) -> int:
        return max(0, self.max_concurrent_tasks - self.current_load)
    
    @property
    def utilization_percentage(self) -> float:
        return (self.current_load / self.max_concurrent_tasks) * 100.0
    
    def can_handle(self, capability: AgentCapability) -> bool:
        return capability in self.capabilities

class TaskScheduler:
    """Intelligent task scheduler"""
    
    def __init__(self):
        self.agents: Dict[str, AgentProfile] = {}
        self.scheduled_tasks: Dict[str, tuple] = {}
    
    def register_agent(self, agent: AgentProfile):
        """Register an agent with its capabilities"""
        self.agents[agent.agent_id] = agent
    
    def schedule_task(self, task_id: str, required_capability: Optional[AgentCapability] = None) -> Optional[str]:
        """Schedule a task to the best available agent"""
        best_agent = self._find_best_agent(required_capability)
        
        if not best_agent:
            return None
        
        best_agent.current_load += 1
        self.scheduled_tasks[task_id] = (best_agent.agent_id,)
        return best_agent.agent_id
    
    def _find_best_agent(self, required_capability: Optional[AgentCapability] = None) -> Optional[AgentProfile]:
        """Find best agent for task"""
        candidates = []
        
        for agent in self.agents.values():
            if required_capability and not agent.can_handle(required_capability):
                continue
            if agent.available_capacity <= 0:
                continue
            
            score = (
                agent.utilization_percentage * 2.0 +
                (1.0 - agent.success_rate) * 100.0 +
                agent.avg_response_time_ms / 10.0
            )
            
            candidates.append((score, agent))
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    def complete_task(self, task_id: str):
        """Mark task as complete"""
        if task_id in self.scheduled_tasks:
            agent_id, = self.scheduled_tasks[task_id]
            if agent_id in self.agents:
                self.agents[agent_id].current_load = max(0, self.agents[agent_id].current_load - 1)
            del self.scheduled_tasks[task_id]
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get overall scheduler status"""
        total_capacity = sum(a.max_concurrent_tasks for a in self.agents.values())
        total_load = sum(a.current_load for a in self.agents.values())
        
        return {
            "agents_count": len(self.agents),
            "total_capacity": total_capacity,
            "current_load": total_load,
            "utilization_percentage": (total_load / total_capacity * 100.0) if total_capacity > 0 else 0,
        }
