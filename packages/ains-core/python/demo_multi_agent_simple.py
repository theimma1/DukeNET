#!/usr/bin/env python3
"""
Simple Multi-Agent Demo - Fixed Version
"""

import requests
import time
import subprocess
import sys
import signal

API_URL = "http://localhost:8000"

class Demo:
    def __init__(self):
        self.processes = []
    
    def start_agents(self):
        print("\n🚀 Starting 4 sample agents...")
        agents = ["sample_agent.py", "sample_agent_image.py", "sample_agent_report.py", "sample_agent_ml.py"]
        
        for agent in agents:
            try:
                p = subprocess.Popen([sys.executable, agent], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.processes.append(p)
                print(f"   ✅ {agent} started")
                time.sleep(1)
            except Exception as e:
                print(f"   ❌ {agent} failed: {e}")
        
        time.sleep(5)
    
    def list_agents(self):
        print("\n📋 Registered Agents:")
        try:
            response = requests.get(f"{API_URL}/ains/agents")
            if response.status_code == 200:
                agents = response.json()
                print(f"   Found {len(agents)} agents")
                for agent in agents:
                    if isinstance(agent, dict):
                        print(f"   • {agent.get('agent_id')}: {agent.get('display_name')}")
        except Exception as e:
            print(f"   Error: {e}")
    
    def check_health(self):
        print("\n✅ Checking API...")
        try:
            response = requests.get(f"{API_URL}/health")
            if response.status_code == 200:
                print("   ✅ API is healthy")
                return True
        except:
            print("   ❌ API not running")
            return False
        return False
    
    def cleanup(self):
        print("\n🛑 Stopping agents...")
        for p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=2)
            except:
                p.kill()
        print("   ✅ All stopped")
    
    def run(self):
        print("=" * 70)
        print("  🚀 DukeNet AINS Multi-Agent Demo (FIXED)")
        print("=" * 70)
        
        try:
            if not self.check_health():
                print("\n❌ Start the API first: python -m uvicorn ains.api:app --reload --port 8000")
                return
            
            self.start_agents()
            self.list_agents()
            
            print("\n" + "=" * 70)
            print("✅ Demo Complete!")
            print("=" * 70)
            print("\n📊 Grafana: http://localhost:3000")
            print("📈 Prometheus: http://localhost:9090")
            print("🌐 API: http://localhost:8000")
            print("\nPress Ctrl+C to stop agents")
            
            # Keep running
            while True:
                time.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
        finally:
            self.cleanup()

if __name__ == "__main__":
    demo = Demo()
    demo.run()
