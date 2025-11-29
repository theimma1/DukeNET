import json
import asyncio
from typing import Dict, List, Optional
from aicp.message import AICPMessage

class AICPRouter:
    def __init__(self):
        self.agents: Dict[str, Dict] = {}  # agent_id → {capabilities, endpoint, public_key}
        self.routes: Dict[str, List[str]] = {}  # method → [agent_ids]
    
    def register_agent(self, agent_id: str, capabilities: List[str], endpoint: str, public_key: str):
        """Register agent with capabilities"""
        self.agents[agent_id] = {
            "capabilities": capabilities,
            "endpoint": endpoint,
            "public_key": public_key
        }
        # Auto-index by capabilities
        for cap in capabilities:
            if cap not in self.routes:
                self.routes[cap] = []
            if agent_id not in self.routes[cap]:
                self.routes[cap].append(agent_id)
        print(f"✅ Registered {agent_id}: {capabilities}")
    
    def find_route(self, method: str) -> Optional[str]:
        """Find best agent for method"""
        # Simple: first capable agent
        for agent_id in self.routes.get(method, []):
            return agent_id
        return None
    
    async def route_message(self, msg: AICPMessage) -> Optional[AICPMessage]:
        """Route signed message to target agent"""
        target = self.find_route(msg.method)
        if not target:
            return self.error_response(msg, "No capable agent")
        
        agent = self.agents[target]
        print(f"📤 ROUTING {msg.method} → {target} ({agent['endpoint']})")
        
        # TODO: Send via WebSocket/HTTP to agent endpoint
        # Simulate delivery
        await asyncio.sleep(0.1)
        
        # Simulate response
        response = AICPMessage(
            id=str(uuid.uuid4()),
            sender=target,
            recipient=msg.sender,
            type="response",
            method=f"{msg.method}.response",
            payload={"status": "delivered", "agent": target}
        )
        return response
    
    def error_response(self, req: AICPMessage, reason: str) -> AICPMessage:
        return AICPMessage(
            id=str(uuid.uuid4()),
            sender="AINS-router",
            recipient=req.sender,
            type="error",
            method=req.method,
            payload={"error": reason}
        )

# Global router instance
router = AICPRouter()
import uuid
