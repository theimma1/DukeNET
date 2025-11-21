import pytest
from ains.cache import cache

def test_cache_set_get_invalidate():
    agent_id = "agent_cache_test"
    agent_data = {"agent_id": agent_id, "display_name": "Cached Agent"}

    # Initially cache miss
    assert cache.get_agent(agent_id) is None

    # Set cache
    cache.set_agent(agent_id, agent_data)
    cached = cache.get_agent(agent_id)
    assert cached == agent_data

    # Invalidate cache
    cache.invalidate_agent(agent_id)
    assert cache.get_agent(agent_id) is None

def test_cache_fallback():
    # You can add tests for fallback cache if implemented
    pass
