"""Multi-Agent Task Coordination System"""

import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return 0.0

@dataclass
class Task:
    """Represents a single task"""
    method: str
    params: Dict[str, Any]
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 0
    timeout: float = 30.0
    dependencies: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING

@dataclass
class TaskChain:
    """Represents a chain of tasks with dependencies"""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tasks: List[Task] = field(default_factory=list)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: TaskStatus = TaskStatus.PENDING
    
    def add_task(self, task: Task, depends_on: Optional[str] = None):
        """Add task to chain"""
        self.tasks.append(task)
        if depends_on:
            if task.task_id not in self.dependency_graph:
                self.dependency_graph[task.task_id] = []
            self.dependency_graph[task.task_id].append(depends_on)
            task.dependencies.append(depends_on)
    
    def get_executable_tasks(self, completed_tasks: set) -> List[Task]:
        """Get tasks ready to execute"""
        executable = []
        for task in self.tasks:
            if task.status == TaskStatus.PENDING:
                deps = self.dependency_graph.get(task.task_id, [])
                if all(dep_id in completed_tasks for dep_id in deps):
                    executable.append(task)
        return executable

class TaskCoordinator:
    """Coordinates task execution across agents"""
    
    def __init__(self):
        self.chains: Dict[str, TaskChain] = {}
        self.results: Dict[str, TaskResult] = {}
    
    async def execute_chain(
        self,
        chain: TaskChain,
        agents: List[str]
    ) -> Dict[str, TaskResult]:
        """Execute a task chain"""
        self.chains[chain.chain_id] = chain
        chain.status = TaskStatus.RUNNING
        results = {}
        completed = set()
        
        while len(completed) < len(chain.tasks):
            executable = chain.get_executable_tasks(completed)
            if not executable:
                break
            
            tasks = await asyncio.gather(*[
                self._execute_task(task, agents)
                for task in executable
            ])
            
            for task, result in zip(executable, tasks):
                results[task.task_id] = result
                self.results[task.task_id] = result
                if result.status == TaskStatus.COMPLETED:
                    completed.add(task.task_id)
                else:
                    chain.status = TaskStatus.FAILED
                    return results
        
        chain.status = TaskStatus.COMPLETED
        return results
    
    async def _execute_task(self, task: Task, agents: List[str]) -> TaskResult:
        """Execute a single task"""
        result = TaskResult(task_id=task.task_id, status=TaskStatus.RUNNING)
        result.started_at = datetime.now()
        
        try:
            task.status = TaskStatus.RUNNING
            await asyncio.sleep(0.1)
            
            result.status = TaskStatus.COMPLETED
            result.result = {"method": task.method, "params": task.params}
            result.agent_id = agents[0]
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            result.status = TaskStatus.FAILED
            result.error = str(e)
            task.status = TaskStatus.FAILED
        finally:
            result.completed_at = datetime.now()
        
        return result
    
    async def execute_parallel_tasks(
        self,
        tasks: List[Task],
        agents: List[str]
    ) -> List[TaskResult]:
        """Execute multiple independent tasks in parallel"""
        results = await asyncio.gather(*[
            self._execute_task(task, agents)
            for task in tasks
        ])
        
        for task, result in zip(tasks, results):
            self.results[task.task_id] = result
        
        return results
    
    def get_chain_status(self, chain_id: str):
        """Get chain execution status"""
        if chain_id not in self.chains:
            return None
        
        chain = self.chains[chain_id]
        return {
            "chain_id": chain_id,
            "status": chain.status.value,
            "total_tasks": len(chain.tasks),
            "completed_tasks": sum(1 for t in chain.tasks if t.status == TaskStatus.COMPLETED),
        }
