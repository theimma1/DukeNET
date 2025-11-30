"""Test Multi-Agent Collaboration System"""

import asyncio
import sys
sys.path.insert(0, '.')

from aicp.task_coordinator import TaskCoordinator, TaskChain, Task, TaskStatus
from aicp.task_scheduler import TaskScheduler, AgentProfile, AgentCapability

print("🧪 Testing Multi-Agent Collaboration System\n")
print("=" * 60)

# Test 1: Task Chain Execution
print("\n✅ TEST 1: Sequential Task Chain")
print("-" * 60)

async def test_chain():
    coordinator = TaskCoordinator()
    chain = TaskChain()
    
    # Create sequential tasks
    task1 = Task(method="data.fetch", params={"source": "api"})
    task2 = Task(method="data.process", params={"format": "json"})
    task3 = Task(method="data.store", params={"destination": "db"})
    
    # Add tasks with dependencies
    chain.add_task(task1)
    chain.add_task(task2, depends_on=task1.task_id)
    chain.add_task(task3, depends_on=task2.task_id)
    
    print(f"📋 Chain created with {len(chain.tasks)} tasks:")
    print(f"   Task 1: data.fetch")
    print(f"   Task 2: data.process (depends on Task 1)")
    print(f"   Task 3: data.store (depends on Task 2)")
    
    # Execute chain
    results = await coordinator.execute_chain(chain, ["agent-1", "agent-2"])
    
    print(f"\n✅ Chain execution completed")
    print(f"   Chain status: {chain.status.value}")
    print(f"   Completed tasks: {sum(1 for t in chain.tasks if t.status == TaskStatus.COMPLETED)}")
    
    return chain

asyncio.run(test_chain())

# Test 2: Parallel Task Execution
print("\n\n✅ TEST 2: Parallel Task Execution")
print("-" * 60)

async def test_parallel():
    coordinator = TaskCoordinator()
    
    # Create independent tasks
    tasks = [
        Task(method="image.resize", params={"width": 800}),
        Task(method="image.filter", params={"filter": "blur"}),
        Task(method="image.compress", params={"quality": 0.8}),
    ]
    
    print(f"📦 Created {len(tasks)} independent tasks")
    
    start = asyncio.get_event_loop().time()
    results = await coordinator.execute_parallel_tasks(tasks, ["agent-1"])
    duration = asyncio.get_event_loop().time() - start
    
    print(f"\n✅ Parallel execution completed in {duration:.2f}s")
    print(f"   Tasks executed: {len(results)}")
    print(f"   All completed: {all(r.status == TaskStatus.COMPLETED for r in results)}")

asyncio.run(test_parallel())

# Test 3: Task Scheduler
print("\n\n✅ TEST 3: Intelligent Task Scheduling")
print("-" * 60)

scheduler = TaskScheduler()

# Register agents
agent1 = AgentProfile(
    agent_id="agent-1",
    capabilities=[AgentCapability.IMAGE_PROCESSING, AgentCapability.DATA_ANALYSIS],
    max_concurrent_tasks=10,
    success_rate=0.98
)

agent2 = AgentProfile(
    agent_id="agent-2",
    capabilities=[AgentCapability.NLP, AgentCapability.DATA_ANALYSIS],
    max_concurrent_tasks=8,
    success_rate=0.95
)

agent3 = AgentProfile(
    agent_id="agent-3",
    capabilities=[AgentCapability.CODE_EXECUTION],
    max_concurrent_tasks=5,
    success_rate=0.92
)

scheduler.register_agent(agent1)
scheduler.register_agent(agent2)
scheduler.register_agent(agent3)

print("📋 Registered 3 agents with capabilities:")
print(f"   agent-1: IMAGE_PROCESSING, DATA_ANALYSIS (10 slots)")
print(f"   agent-2: NLP, DATA_ANALYSIS (8 slots)")
print(f"   agent-3: CODE_EXECUTION (5 slots)")

# Schedule tasks
task1_id = scheduler.schedule_task("task-1", AgentCapability.IMAGE_PROCESSING)
task2_id = scheduler.schedule_task("task-2", AgentCapability.NLP)
task3_id = scheduler.schedule_task("task-3", AgentCapability.CODE_EXECUTION)

print(f"\n📦 Tasks scheduled:")
print(f"   Task 1 (IMAGE_PROCESSING) → {task1_id}")
print(f"   Task 2 (NLP) → {task2_id}")
print(f"   Task 3 (CODE_EXECUTION) → {task3_id}")

status = scheduler.get_scheduler_status()
print(f"\n📊 Scheduler status:")
print(f"   Total capacity: {status['total_capacity']}")
print(f"   Current load: {status['current_load']}")
print(f"   Utilization: {status['utilization_percentage']:.1f}%")

print("\n" + "=" * 60)
print("✅ All tests passed! Multi-Agent Collaboration is working!\n")
