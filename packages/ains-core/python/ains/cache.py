"""AINS Redis Caching Layer"""

import json
from typing import Optional, Dict

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class AgentCache:
    """Redis cache for agent data (falls back to in-memory if Redis unavailable)"""
    
    def __init__(self, host: str = "localhost", port: int = 6379):
        if REDIS_AVAILABLE:
            try:
                self.redis = redis.Redis(host=host, port=port, decode_responses=True)
                self.redis.ping()  # Test connection
                self.use_redis = True
            except:
                self.use_redis = False
                self.memory_cache = {}
        else:
            self.use_redis = False
            self.memory_cache = {}
        
        self.ttl = 300  # 5 minutes
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """Get agent from cache"""
        if self.use_redis:
            key = f"agent:{agent_id}"
            data = self.redis.get(key)
            return json.loads(data) if data else None
        else:
            return self.memory_cache.get(f"agent:{agent_id}")
    
    def set_agent(self, agent_id: str, agent_data: dict):
        """Cache agent data"""
        if self.use_redis:
            key = f"agent:{agent_id}"
            self.redis.setex(key, self.ttl, json.dumps(agent_data))
        else:
            self.memory_cache[f"agent:{agent_id}"] = agent_data
    
    def invalidate_agent(self, agent_id: str):
        """Invalidate agent cache"""
        if self.use_redis:
            key = f"agent:{agent_id}"
            self.redis.delete(key)
        else:
            self.memory_cache.pop(f"agent:{agent_id}", None)
    
    def get_capability(self, capability_id: str) -> Optional[Dict]:
        """Get capability from cache"""
        if self.use_redis:
            key = f"capability:{capability_id}"
            data = self.redis.get(key)
            return json.loads(data) if data else None
        else:
            return self.memory_cache.get(f"capability:{capability_id}")
    
    def set_capability(self, capability_id: str, capability_data: dict):
        """Cache capability data"""
        if self.use_redis:
            key = f"capability:{capability_id}"
            self.redis.setex(key, self.ttl, json.dumps(capability_data))
        else:
            self.memory_cache[f"capability:{capability_id}"] = capability_data
    
    def invalidate_capability(self, capability_id: str):
        """Invalidate capability cache"""
        if self.use_redis:
            key = f"capability:{capability_id}"
            self.redis.delete(key)
        else:
            self.memory_cache.pop(f"capability:{capability_id}", None)


# Global cache instance
cache = AgentCache()
