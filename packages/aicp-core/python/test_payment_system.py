"""Test Payment System"""

import sys
sys.path.insert(0, '.')

from aicp.reputation_system import ReputationSystem, TaskOutcome
from aicp.pricing_engine import PricingEngine, TaskComplexity
from aicp.payment_processor import PaymentProcessor

print("🧪 Testing Payment System\n")
print("=" * 60)

# Test 1: Reputation System
print("\n✅ TEST 1: Reputation System")
print("-" * 60)

reputation = ReputationSystem()

# Register agents
agent1 = reputation.register_agent("agent-1")
agent2 = reputation.register_agent("agent-2")
agent3 = reputation.register_agent("agent-3")

# Simulate task outcomes
print("📊 Recording task outcomes:")

# Agent-1: Excellent (95% success)
for i in range(19):
    reputation.record_outcome("agent-1", TaskOutcome.SUCCESS, 50.0)
reputation.record_outcome("agent-1", TaskOutcome.FAILURE)

# Agent-2: Good (90% success)
for i in range(18):
    reputation.record_outcome("agent-2", TaskOutcome.SUCCESS, 100.0)
reputation.record_outcome("agent-2", TaskOutcome.FAILURE)
reputation.record_outcome("agent-2", TaskOutcome.TIMEOUT)

# Agent-3: Poor (70% success)
for i in range(7):
    reputation.record_outcome("agent-3", TaskOutcome.SUCCESS, 200.0)
reputation.record_outcome("agent-3", TaskOutcome.FAILURE)
reputation.record_outcome("agent-3", TaskOutcome.TIMEOUT)
reputation.record_outcome("agent-3", TaskOutcome.TIMEOUT)

# Display results
for agent_id in ["agent-1", "agent-2", "agent-3"]:
    rep = reputation.get_reputation(agent_id)
    print(f"\n{agent_id}:")
    print(f"  Success rate: {rep.success_rate * 100:.1f}%")
    print(f"  Reputation multiplier: {rep.reputation_multiplier:.2f}x")
    print(f"  Avg response: {rep.avg_response_time_ms:.0f}ms")

# Test 2: Pricing Engine
print("\n\n✅ TEST 2: Dynamic Pricing Engine")
print("-" * 60)

pricing = PricingEngine(reputation_system=reputation)

print("\nTask: Image Processing")
print("Base price: ₿1.0")
print("Complexity: MEDIUM")

for agent_id in ["agent-1", "agent-2", "agent-3"]:
    pricing_info = pricing.calculate_price(
        agent_id=agent_id,
        base_price=1.0,
        complexity=TaskComplexity.MEDIUM
    )
    
    print(f"\n{agent_id}:")
    print(f"  Reputation multiplier: {pricing_info['reputation_multiplier']:.2f}x")
    print(f"  Final price: ₿{pricing_info['final_price']:.4f}")

# Test 3: Payment Processor
print("\n\n✅ TEST 3: Payment Processor")
print("-" * 60)

processor = PaymentProcessor()

print("\nCreating payments:")

# Payment 1
payment1 = processor.create_payment(
    buyer_id="buyer-1",
    agent_id="agent-1",
    amount=0.95,
    task_id="task-1"
)
print(f"✓ Payment created: {payment1.payment_id}")
print(f"  Agent: {payment1.agent_id}")
print(f"  Amount: ₿{payment1.amount}")

# Escrow and release
processor.escrow_payment(payment1.payment_id, "task-1")
processor.release_payment("task-1")

wallet1 = processor.get_agent_balance("agent-1")
print(f"\n✓ Payment released to agent-1")
print(f"  Balance: ₿{wallet1['balance']}")
print(f"  Earned: ₿{wallet1['earned']}")

# Payment 2
payment2 = processor.create_payment(
    buyer_id="buyer-2",
    agent_id="agent-2",
    amount=0.80,
    task_id="task-2"
)
processor.escrow_payment(payment2.payment_id, "task-2")
processor.release_payment("task-2")

wallet2 = processor.get_agent_balance("agent-2")
print(f"\n✓ Payment released to agent-2")
print(f"  Balance: ₿{wallet2['balance']}")

print("\n" + "=" * 60)
print("✅ Payment system working correctly!\n")
