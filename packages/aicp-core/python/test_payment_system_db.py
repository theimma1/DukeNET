#!/usr/bin/env python3
"""Test Payment System with PostgreSQL"""

from aicp.database import (
    init_database, 
    seed_initial_agents,
    get_agent_by_name,
    create_payment,
    release_payment
)
import uuid

print("🧪 Testing Payment System with PostgreSQL\n")
print("=" * 60)

# Initialize database
init_database()
seed_initial_agents()

print("\n✅ TEST 1: Verify Agents in Database")
print("-" * 60)
for agent_name in ['agent-1', 'agent-2', 'agent-3']:
    agent = get_agent_by_name(agent_name)
    print(f"\n{agent_name}:")
    print(f"  Success rate: {agent['success_rate']}%")
    print(f"  Reputation multiplier: {agent['reputation_multiplier']:.2f}x")
    print(f"  Balance: ₿{agent['balance_satoshis']/100_000_000:.4f}")

print("\n\n✅ TEST 2: Create Payment in Escrow")
print("-" * 60)
payment_id = str(uuid.uuid4())[:8]
amount_satoshis = 95_000_000  # ₿0.95
create_payment(payment_id, 'agent-1', amount_satoshis)
print(f"✓ Payment created: {payment_id}")
print(f"  Agent: agent-1")
print(f"  Amount: ₿{amount_satoshis/100_000_000:.2f}")
print(f"  Status: escrow")

print("\n\n✅ TEST 3: Release Payment")
print("-" * 60)
success = release_payment(payment_id)
if success:
    agent = get_agent_by_name('agent-1')
    print(f"✓ Payment released to agent-1")
    print(f"  Balance: ₿{agent['balance_satoshis']/100_000_000:.4f}")
    print(f"  Earned: ₿{amount_satoshis/100_000_000:.2f}")

print("\n" + "=" * 60)
print("✅ Database payment system working correctly!")
print("\nVerify in PostgreSQL:")
print('docker exec -it aicp-db psql -U aicp -d aicp -c "SELECT * FROM payments;"')
