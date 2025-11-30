"""Dynamic Pricing Engine"""

from dataclasses import dataclass
from typing import Dict, Optional
from enum import Enum

class TaskComplexity(Enum):
    SIMPLE = 1.0        # Basic tasks
    MEDIUM = 1.5        # Standard tasks
    COMPLEX = 2.0       # Advanced tasks
    EXPERT = 3.0        # Specialized tasks

@dataclass
class PricingConfig:
    """Pricing configuration"""
    base_price: float = 1.0              # Base unit price
    capability_premium: float = 1.0      # Specialization multiplier
    reputation_multiplier: float = 1.0   # Quality multiplier
    demand_factor: float = 1.0           # Market demand
    speed_bonus_percent: float = 0.1     # 10% bonus for speediness
    urgency_multiplier: float = 1.0      # Rush job multiplier

class PricingEngine:
    """Calculate dynamic prices based on multiple factors"""
    
    def __init__(self, reputation_system=None):
        self.reputation_system = reputation_system
        self.task_count = 0  # For demand tracking
        self.demand_factor = 1.0
    
    def calculate_price(
        self,
        agent_id: str,
        base_price: float,
        complexity: TaskComplexity = TaskComplexity.MEDIUM,
        is_urgent: bool = False,
        estimated_time_ms: float = 100.0
    ) -> Dict[str, float]:
        """
        Calculate final price for a task
        
        Returns:
            Dict with breakdown of pricing
        """
        
        # Get agent reputation multiplier
        reputation_mult = 1.0
        if self.reputation_system:
            reputation_mult = self.reputation_system.get_price_multiplier(agent_id)
        
        # Complexity multiplier
        complexity_mult = complexity.value
        
        # Urgency multiplier
        urgency_mult = 1.5 if is_urgent else 1.0
        
        # Demand factor (simulated)
        # In real system: market_demand / available_agents
        demand_mult = self.demand_factor
        
        # Calculate final price
        price = (
            base_price *
            reputation_mult *
            complexity_mult *
            urgency_mult *
            demand_mult
        )
        
        return {
            "base_price": base_price,
            "reputation_multiplier": reputation_mult,
            "complexity_multiplier": complexity_mult,
            "urgency_multiplier": urgency_mult,
            "demand_multiplier": demand_mult,
            "final_price": price,
            "breakdown": {
                "base": base_price,
                "reputation": base_price * (reputation_mult - 1.0),
                "complexity": base_price * (complexity_mult - 1.0),
                "urgency": base_price * (urgency_mult - 1.0),
                "demand": base_price * (demand_mult - 1.0),
            }
        }
    
    def suggest_bid(
        self,
        agent_id: str,
        base_price: float,
        complexity: TaskComplexity = TaskComplexity.MEDIUM
    ) -> float:
        """Suggest bid price for agent"""
        pricing = self.calculate_price(agent_id, base_price, complexity)
        return pricing["final_price"]
    
    def update_demand(self, task_count: int, available_agents: int):
        """Update demand factor based on market conditions"""
        if available_agents > 0:
            self.demand_factor = 1.0 + (task_count / available_agents) * 0.5
        else:
            self.demand_factor = 1.0
