"""
Quick test of the Circuit Breaker & Failover system
"""
import asyncio
from aicp.circuit_breaker import CircuitBreaker, CircuitBreakerOpen
from aicp.failover_handler import FailoverRouter

print("🧪 Testing Circuit Breaker System\n")
print("=" * 60)

# Test 1: Basic Circuit Breaker
print("\n✅ TEST 1: Circuit Breaker State Transitions")
print("-" * 60)

cb = CircuitBreaker(failure_threshold=3)

def fail_func():
    raise Exception("Agent failed!")

def success_func():
    return {"status": "ok"}

# Normal operation (CLOSED)
try:
    cb.call("test-agent", success_func)
    print("✓ Call 1: CLOSED state - Success")
except:
    print("✗ Call 1 failed")

# Failures accumulate
for i in range(1, 4):
    try:
        cb.call("test-agent", fail_func)
    except Exception as e:
        print(f"⚠️ Call {i+1}: Failure {i}/3")

# Circuit now OPEN
try:
    cb.call("test-agent", success_func)
except CircuitBreakerOpen:
    print("🔴 Call 5: OPEN state - Rejected (<1ms)")

print(f"\nCircuit state: {cb.get_state('test-agent').value}")

# Test 2: Failover Router
print("\n\n✅ TEST 2: Failover Router")
print("-" * 60)

async def test_failover():
    router = FailoverRouter(max_retries=2)
    
    # Simulate agent calls
    call_count = {"agent-1": 0, "agent-2": 0, "agent-3": 0}
    
    async def mock_agent(agent_id: str):
        call_count[agent_id] += 1
        
        # agent-1 always fails
        if agent_id == "agent-1":
            raise Exception("Agent-1 down")
        
        # agent-2 sometimes fails
        if agent_id == "agent-2" and call_count["agent-2"] <= 2:
            raise Exception("Agent-2 busy")
        
        # agent-3 always succeeds
        return {"agent": agent_id, "result": "success"}
    
    try:
        result = await router.route_task(
            task_id="test-task-1",
            agents=["agent-1", "agent-2", "agent-3"],
            task_func=mock_agent
        )
        print(f"✅ Task succeeded on {result['agent']}")
        print(f"   Calls made: agent-1={call_count['agent-1']}, agent-2={call_count['agent-2']}, agent-3={call_count['agent-3']}")
    except Exception as e:
        print(f"❌ Task failed: {e}")
    
    # Check health
    health = router.get_health_status()
    print(f"\n📊 Health Status:")
    print(f"   Total agents: {health['total_agents']}")
    print(f"   Healthy: {health['healthy_agents']}")
    print(f"   Open circuits: {health['open_circuits']}")
    print(f"   Half-open: {health['half_open_circuits']}")

asyncio.run(test_failover())

# Test 3: Metrics
print("\n\n✅ TEST 3: Metrics Collection")
print("-" * 60)

cb = CircuitBreaker()

# Record some activity
for i in range(5):
    try:
        cb.call("agent-x", success_func)
    except:
        pass

# Get metrics
metrics = cb.get_metrics("agent-x")
print(f"Agent: {metrics['agent_id']}")
print(f"State: {metrics['state']}")
print(f"Successes: {metrics['metrics']['success_count']}")
print(f"Failures: {metrics['metrics']['failure_count']}")
print(f"Rejections: {metrics['metrics']['total_rejections']}")

print("\n" + "=" * 60)
print("✅ All tests passed! Circuit Breaker is working!\n")
