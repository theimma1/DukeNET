"""
AINS Sample Agent - Fixed for snake_case validation
"""
import os
import sys
import time
import secrets
import requests
from datetime import datetime, timezone
from typing import Optional

# Configuration from environment
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
        
    def register(self) -> bool:
        """Register agent with AINS API"""
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
                print(f"❌ Registration failed: {resp.status_code}")
                print(f"   Response: {resp.text[:300]}")
                return False
        except Exception as e:
            print(f"❌ Registration error: {e}")
            return False
    
    def send_heartbeat(self) -> bool:
        """Send heartbeat with correct snake_case fields"""
        # Use only required fields - status is the main one
        payload = {"status": "AVAILABLE"}
        
        try:
            resp = self.session.post(
                f"{self.api_url}/ains/agents/{self.agent_id}/heartbeat",
                json=payload
            )
            if resp.status_code in (200, 204):
                print(f"💓 Heartbeat OK")
                return True
            else:
                print(f"⚠️  Heartbeat {resp.status_code}: {resp.text[:200]}")
                return False
        except Exception as e:
            print(f"❌ Heartbeat error: {e}")
            return False
    
    def register_capability(self, capability_name: str) -> bool:
        """Register capability - simplified payload"""
        payload = {
            "name": capability_name,
            "description": f"Sample {capability_name} capability",
            "inputschema": {},
            "outputschema": {},
            "pricingmodel": "free",
            "price": 0.0,
            "latencyp99ms": 100,
            "availabilitypercent": 99.9,
            "signature": self.signature
        }
        
        try:
            resp = self.session.post(
                f"{self.api_url}/ains/agents/{self.agent_id}/capabilities",
                json=payload
            )
            if resp.status_code in (200, 201):
                print(f"✅ Capability: {capability_name}")
                return True
            else:
                print(f"⚠️  Capability {resp.status_code}")
                # Don't fail - continue anyway
                return False
        except Exception as e:
            print(f"⚠️  Capability error: {e}")
            return False
    
    def poll_tasks(self) -> list:
        """Poll for assigned tasks"""
        try:
            resp = self.session.get(
                f"{self.api_url}/aitp/tasks",
                params={
                    "assignedagentid": self.agent_id,
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
        """Execute a task (mock)"""
        task_id = task.get("taskid") or task.get("task_id")
        print(f"   Executing task {task_id[:8]}...")
        
        # Simulate work
        time.sleep(0.2)
        
        return {
            "processed": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "completed"
        }
    
    def report_completion(self, task_id: str, result: dict) -> bool:
        """Report completion"""
        payload = {
            "status": "COMPLETED",
            "resultdata": result
        }
        
        try:
            resp = self.session.put(
                f"{self.api_url}/aitp/tasks/{task_id}/status",
                params={"agentid": self.agent_id},
                json=payload
            )
            if resp.status_code in (200, 204):
                print(f"   ✅ Task completed")
                return True
            else:
                print(f"   ⚠️  Report failed: {resp.status_code}")
                return False
        except Exception as e:
            print(f"   ⚠️  Report error: {e}")
            return False
    
    def run(self):
        """Main agent loop"""
        print(f"\n🚀 AINS Sample Agent: {self.agent_name}")
        print(f"📡 API: {self.api_url}\n")
        
        # Register
        if not self.register():
            print("❌ Registration failed. Exiting.")
            return
        
        # Try to register capability (optional)
        self.register_capability("sample-v1")
        
        # Main loop
        last_heartbeat = 0
        poll_count = 0
        
        try:
            while True:
                now = time.time()
                
                # Heartbeat every HEARTBEAT_INTERVAL seconds
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    self.send_heartbeat()
                    last_heartbeat = now
                
                # Poll for tasks
                poll_count += 1
                tasks = self.poll_tasks()
                
                for task in tasks:
                    result = self.execute_task(task)
                    task_id = task.get("taskid") or task.get("task_id")
                    self.report_completion(task_id, result)
                
                if poll_count % 6 == 0:  # Every 30 seconds
                    print(f"⏱️  Agent running... (polled {poll_count} times)")
                
                time.sleep(POLL_INTERVAL)
                
        except KeyboardInterrupt:
            print("\n\n👋 Agent shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    agent = AINSAgent(API_BASE_URL, AGENT_NAME)
    agent.run()
