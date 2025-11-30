import time
from enum import Enum
from datetime import datetime
from typing import Dict, Optional
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerMetrics:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.total_rejections = 0
        
    def record_success(self):
        self.success_count += 1
        self.last_success_time = datetime.now()
        self.failure_count = 0
        
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
    def record_rejection(self):
        self.total_rejections += 1
        
    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_rejections": self.total_rejections,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "last_success_time": self.last_success_time.isoformat() if self.last_success_time else None,
        }

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
        backoff_multiplier: float = 1.5,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.backoff_multiplier = backoff_multiplier
        self.circuits: Dict[str, Dict] = {}
        
    def _get_circuit(self, agent_id: str) -> Dict:
        if agent_id not in self.circuits:
            self.circuits[agent_id] = {
                "state": CircuitState.CLOSED,
                "metrics": CircuitBreakerMetrics(agent_id),
                "opened_at": None,
                "half_open_calls": 0,
                "backoff_seconds": 1,
            }
        return self.circuits[agent_id]
    
    def call(self, agent_id: str, func, *args, **kwargs):
        circuit = self._get_circuit(agent_id)
        state = circuit["state"]
        
        if state == CircuitState.OPEN:
            if self._should_attempt_recovery(circuit):
                circuit["state"] = CircuitState.HALF_OPEN
                circuit["half_open_calls"] = 0
                print(f"🔄 Circuit HALF_OPEN for {agent_id}")
            else:
                circuit["metrics"].record_rejection()
                raise CircuitBreakerOpen(f"Circuit OPEN for {agent_id}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success(circuit, agent_id)
            return result
        except Exception as e:
            self._on_failure(circuit, agent_id)
            raise
    
    async def call_async(self, agent_id: str, coro):
        circuit = self._get_circuit(agent_id)
        state = circuit["state"]
        
        if state == CircuitState.OPEN:
            if self._should_attempt_recovery(circuit):
                circuit["state"] = CircuitState.HALF_OPEN
                circuit["half_open_calls"] = 0
                print(f"🔄 Circuit HALF_OPEN for {agent_id}")
            else:
                circuit["metrics"].record_rejection()
                raise CircuitBreakerOpen(f"Circuit OPEN for {agent_id}")
        
        try:
            result = await coro
            self._on_success(circuit, agent_id)
            return result
        except Exception as e:
            self._on_failure(circuit, agent_id)
            raise
    
    def _on_success(self, circuit: Dict, agent_id: str):
        circuit["metrics"].record_success()
        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["half_open_calls"] += 1
            if circuit["half_open_calls"] >= self.half_open_max_calls:
                self._close_circuit(circuit, agent_id)
        elif circuit["state"] == CircuitState.CLOSED:
            circuit["backoff_seconds"] = 1
    
    def _on_failure(self, circuit: Dict, agent_id: str):
        circuit["metrics"].record_failure()
        failures = circuit["metrics"].failure_count
        
        if circuit["state"] == CircuitState.HALF_OPEN:
            self._open_circuit(circuit, agent_id)
        elif circuit["state"] == CircuitState.CLOSED:
            print(f"⚠️ {agent_id} failure {failures}/{self.failure_threshold}")
            if failures >= self.failure_threshold:
                self._open_circuit(circuit, agent_id)
    
    def _open_circuit(self, circuit: Dict, agent_id: str):
        circuit["state"] = CircuitState.OPEN
        circuit["opened_at"] = datetime.now()
        circuit["backoff_seconds"] = min(circuit["backoff_seconds"] * self.backoff_multiplier, 60)
        print(f"🔴 Circuit OPEN for {agent_id}")
    
    def _close_circuit(self, circuit: Dict, agent_id: str):
        circuit["state"] = CircuitState.CLOSED
        circuit["metrics"].failure_count = 0
        circuit["backoff_seconds"] = 1
        print(f"🟢 Circuit CLOSED for {agent_id} - recovered!")
    
    def _should_attempt_recovery(self, circuit: Dict) -> bool:
        if circuit["opened_at"] is None:
            return False
        elapsed = (datetime.now() - circuit["opened_at"]).total_seconds()
        return elapsed >= circuit["backoff_seconds"]
    
    def get_state(self, agent_id: str):
        return self._get_circuit(agent_id)["state"]
    
    def get_metrics(self, agent_id: str) -> Dict:
        circuit = self._get_circuit(agent_id)
        return {
            "agent_id": agent_id,
            "state": circuit["state"].value,
            "metrics": circuit["metrics"].to_dict(),
            "backoff_seconds": circuit["backoff_seconds"],
        }
    
    def get_all_metrics(self) -> Dict[str, Dict]:
        return {agent_id: self.get_metrics(agent_id) for agent_id in self.circuits.keys()}
    
    def reset(self, agent_id: str):
        if agent_id in self.circuits:
            self._close_circuit(self.circuits[agent_id], agent_id)

class CircuitBreakerOpen(Exception):
    pass
