"""
AINS Sample Agent - HEARTBEAT FIXED
Correct status values: ACTIVE, DEGRADED, OFFLINE
"""
import os
import sys
import time
import secrets
import requests
from datetime import datetime, timezone

API_BASE_URL = os.getenv("AINS_API_URL", "http://localhost:8000")
AGENT_NAME = os.getenv("AGENT_NAME", f"sample-agent-{secrets.token_hex(4)}")
HEARTBEAT_INTERVAL = int(os.getenv("HEARTBEAT_INTERVAL", "30"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

class AINSAgent:
    def __init__(self, api_url: str, agent_name: str):
        self.api_url = api_url.rstrip("/")
        self.agent_name = agent_name
        self.agent_id = None
        self.public_key = secrets.token_hex(32)
        self.signature = secrets.token_hex(64)
        self.session = requests.Session()
        self.start_time = time.time()
        
    def register(self) -> bool:
        """Register agent"""
        self.agent_id = secrets.token_hex(16)
        payload = {
            "agent_id": self.agent_id,
            "public_key": self.public_key,
            "display_name": self.agent_name,
            "endpoint": f"http://{self.agent_name}:8080",
            "signature": self.signature
        }
        try:
            resp = self.session.post(f"{self.api_url}/ains/agents", json=payload)
            if resp.status_code in (200, 201):
                print(f"✅ Agent registered: {self.agent_id}")
                return True
            else:
                print(f"❌ Registration {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat - Valid status: ACTIVE, DEGRADED, OFFLINE"""
        uptime_ms = int((time.time() - self.start_time) * 1000)
        
        payload = {
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "status": "ACTIVE",  # ✅ FIXED: Use ACTIVE instead of AVAILABLE
            "uptime_ms": uptime_ms,
            "metrics": {}
        }
        
        try:
            resp = self.session.post(
                f"{self.api_url}/ains/agents/{self.agent_id}/heartbeat",
                json=payload
            )
            if resp.status_code in (200, 204):
                print(f"💓 Heartbeat OK")
                return True
            else:
                print(f"⚠️  Heartbeat {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
            return False
    
    def register_capability(self, capability_name: str) -> bool:
        """Register capability"""
        payload = {
            "name": capability_name,
            "description": f"Sample capability",
            "input_schema": {},
            "output_schema": {},
            "pricing_model": "free",
            "price": 0.0,
            "latency_p99_ms": 100,
            "availability_percent": 99.9,
            "signature": self.signature
        }
        
        try:
            resp = self.session.post(
                f"{self.api_url}/ains/agents/{self.agent_id}/capabilities",
                json=payload
            )
            if resp.status_code in (200, 201):
                print(f"✅ Capability registered")
                return True
            else:
                print(f"⚠️  Capability {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"⚠️  Capability error: {e}")
            return False
    
    def poll_tasks(self) -> list:
        """Poll for tasks"""
        try:
            resp = self.session.get(
                f"{self.api_url}/aitp/tasks",
                params={
                    "assigned_agent_id": self.agent_id,
                    "status": "ASSIGNED",
                    "limit": 10
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                tasks = data if isinstance(data, list) else data.get("tasks", [])
                if tasks:
                    print(f"📋 Found {len(tasks)} task(s)")
                return tasks
            return []
        except Exception as e:
            print(f"⚠️  Poll error: {e}")
            return []
    
    def execute_task(self, task: dict) -> dict:
        """Execute task"""
        task_id = task.get("task_id") or task.get("taskid")
        print(f"   🔧 Executing {task_id[:8]}...")
        time.sleep(0.2)
        return {"processed": True, "timestamp": datetime.now(timezone.utc).isoformat()}
    
    def report_completion(self, task_id: str, result: dict) -> bool:
        """Report completion"""
        payload = {"status": "COMPLETED", "result_data": result}
        try:
            resp = self.session.put(
                f"{self.api_url}/aitp/tasks/{task_id}/status",
                params={"agent_id": self.agent_id},
                json=payload
            )
            if resp.status_code in (200, 204):
                print(f"   ✅ Task completed")
                return True
            else:
                print(f"   ⚠️  Completion failed {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            print(f"   ❌ Completion error: {e}")
            return False
    
    def run(self):
        """Main loop"""
        print(f"\n🚀 AINS Agent: {self.agent_name}")
        print(f"📡 API: {self.api_url}\n")
        
        if not self.register():
            print("❌ Registration failed - exiting")
            return
        
        self.register_capability("sample-v1")
        
        last_heartbeat = 0
        poll_count = 0
        
        try:
            while True:
                now = time.time()
                
                # Send heartbeat
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    self.send_heartbeat()
                    last_heartbeat = now
                
                # Poll for tasks
                poll_count += 1
                tasks = self.poll_tasks()
                for task in tasks:
                    result = self.execute_task(task)
                    task_id = task.get("task_id") or task.get("taskid")
                    if task_id:
                        self.report_completion(task_id, result)
                
                # Status update every 30 seconds
                if poll_count % 6 == 0:
                    print(f"⏱️  Running ({poll_count} polls)")
                
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n👋 Shutting down gracefully")
            sys.exit(0)

if __name__ == "__main__":
    agent = AINSAgent(API_BASE_URL, AGENT_NAME)
    agent.run()