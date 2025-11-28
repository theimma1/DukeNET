#!/usr/bin/env python3
"""
Multi-Agent System Demo
Demonstrates DukeNet AINS with multiple agents working together
"""

import requests
import time
import json
from datetime import datetime
import subprocess
import sys
import signal

API_URL = "http://localhost:8000"

class DemoOrchestrator:
    def __init__(self):
        self.agent_processes = []
        
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)
    
    def print_step(self, step, text):
        """Print formatted step"""
        print(f"\n[STEP {step}] {text}")
        print("-" * 70)
    
    def check_api_health(self):
        """Verify API is running"""
        self.print_step(1, "Checking API Health")
        try:
            response = requests.get(f"{API_URL}/health", timeout=5)
            if response.status_code == 200:
                print("✅ API is healthy and running")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print(f"   Make sure API is running at {API_URL}")
            return False
    
    def start_agents(self):
        """Start all sample agents"""
        self.print_step(2, "Starting Sample Agents")
        
        agents = [
            ("Data Processor", "sample_agent.py"),
            ("Image Analyzer", "sample_agent_image.py"),
            ("Report Generator", "sample_agent_report.py"),
            ("ML Inference", "sample_agent_ml.py")
        ]
        
        for name, script in agents:
            try:
                print(f"🚀 Starting {name}...")
                process = subprocess.Popen(
                    [sys.executable, script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.agent_processes.append((name, process))
                time.sleep(1)
                print(f"   ✅ {name} started (PID: {process.pid})")
            except Exception as e:
                print(f"   ❌ Failed to start {name}: {e}")
        
        print(f"\n✅ Started {len(self.agent_processes)} agents")
        time.sleep(5)  # Wait for registration
    
    def list_agents(self):
        """List registered agents"""
        self.print_step(3, "Listing Registered Agents")
        
        try:
            response = requests.get(f"{API_URL}/ains/agents")
            if response.status_code == 200:
                agents = response.json()
                agent_list = agents.get("agents", []) if isinstance(agents, dict) else agents
                
                print(f"\n📋 Registered Agents: {len(agent_list)}")
                for agent in agent_list:
                    agent_id = agent.get("agent_id", "unknown")
                    name = agent.get("display_name", agent.get("agent_name", "N/A"))
                    caps = agent.get("capabilities", [])
                    status = agent.get("status", "unknown")
                    print(f"   • {name} ({agent_id})")
                    print(f"     Status: {status}")
                    print(f"     Capabilities: {', '.join(caps)}")
            else:
                print(f"❌ Failed to list agents: {response.status_code}")
        except Exception as e:
            print(f"❌ Error listing agents: {e}")
    
    def create_tasks(self):
        """Create tasks for different agents"""
        self.print_step(4, "Creating Tasks for Each Agent")
        
        tasks = [
            {
                "client_id": "demo-client",
                "task_type": "data-processing",
                "capability_required": "data-processing",
                "priority": 8,
                "input_data": {
                    "dataset": "customer_data.csv",
                    "operation": "clean_and_transform"
                },
                "description": "Process customer dataset"
            },
            {
                "client_id": "demo-client",
                "task_type": "image-analysis",
                "capability_required": "image-analysis",
                "priority": 7,
                "input_data": {
                    "image_url": "https://example.com/image.jpg",
                    "operations": ["detect", "classify"]
                },
                "description": "Analyze product image"
            },
            {
                "client_id": "demo-client",
                "task_type": "report-generation",
                "capability_required": "report-generation",
                "priority": 6,
                "input_data": {
                    "title": "Q4 2025 Performance Report",
                    "data_source": "analytics_db",
                    "format": "PDF"
                },
                "description": "Generate quarterly report"
            },
            {
                "client_id": "demo-client",
                "task_type": "ml-inference",
                "capability_required": "ml-inference",
                "priority": 9,
                "input_data": {
                    "text": "This product is amazing!",
                    "model": "sentiment-analysis"
                },
                "description": "Sentiment analysis"
            }
        ]
        
        created_tasks = []
        
        for i, task_data in enumerate(tasks, 1):
            try:
                response = requests.post(f"{API_URL}/aitp/tasks", json=task_data)
                if response.status_code in [200, 201]:
                    task = response.json()
                    task_id = task.get("task_id", "unknown")
                    print(f"✅ Created task {i}: {task_data['description']} ({task_id})")
                    created_tasks.append(task_id)
                else:
                    print(f"❌ Failed to create task {i}: {response.text}")
            except Exception as e:
                print(f"❌ Error creating task {i}: {e}")
            
            time.sleep(0.5)
        
        return created_tasks
    
    def monitor_tasks(self, task_ids, duration=30):
        """Monitor task execution"""
        self.print_step(5, f"Monitoring Task Execution ({duration}s)")
        
        start_time = time.time()
        
        while time.time() - start_time < duration:
            completed = 0
            active = 0
            pending = 0
            
            for task_id in task_ids:
                try:
                    response = requests.get(f"{API_URL}/aitp/tasks/{task_id}")
                    if response.status_code == 200:
                        task = response.json()
                        status = task.get("status", "UNKNOWN")
                        
                        if status == "COMPLETED":
                            completed += 1
                        elif status == "ACTIVE":
                            active += 1
                        else:
                            pending += 1
                except:
                    pass
            
            # Clear line and print status
            print(f"\r📊 Tasks - Completed: {completed}/{len(task_ids)} | Active: {active} | Pending: {pending}", end="", flush=True)
            
            if completed == len(task_ids):
                print("\n✅ All tasks completed!")
                break
            
            time.sleep(2)
        
        print()  # New line
    
    def show_results(self, task_ids):
        """Display task results"""
        self.print_step(6, "Task Results")
        
        for i, task_id in enumerate(task_ids, 1):
            try:
                response = requests.get(f"{API_URL}/aitp/tasks/{task_id}")
                if response.status_code == 200:
                    task = response.json()
                    status = task.get("status", "UNKNOWN")
                    result = task.get("result_data", {})
                    
                    print(f"\n📦 Task {i} ({task_id})")
                    print(f"   Status: {status}")
                    print(f"   Type: {task.get('task_type', 'N/A')}")
                    
                    if result:
                        print(f"   Result: {json.dumps(result, indent=6)}")
                    else:
                        print(f"   Result: No data yet")
            except Exception as e:
                print(f"   ❌ Error fetching task {task_id}: {e}")
    
    def show_metrics(self):
        """Display system metrics"""
        self.print_step(7, "System Metrics")
        
        try:
            response = requests.get(f"{API_URL}/metrics")
            if response.status_code == 200:
                metrics = response.text
                
                # Extract key metrics
                http_requests = [line for line in metrics.split('\n') if 'ains_http_requests_total{' in line]
                agents_total = [line for line in metrics.split('\n') if line.startswith('ains_agents_total')]
                
                print("\n📈 HTTP Requests:")
                for line in http_requests[:5]:
                    print(f"   {line}")
                
                print("\n👥 Agents:")
                for line in agents_total:
                    print(f"   {line}")
                    
                print(f"\n🌐 Full metrics available at: {API_URL}/metrics")
        except Exception as e:
            print(f"❌ Error fetching metrics: {e}")
    
    def cleanup(self):
        """Stop all agent processes"""
        self.print_header("Cleaning Up")
        
        for name, process in self.agent_processes:
            try:
                print(f"🛑 Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()
        
        print("✅ All agents stopped")
    
    def run_demo(self):
        """Run complete demo"""
        self.print_header("🚀 DukeNet AINS Multi-Agent Demo")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # Check API
            if not self.check_api_health():
                return
            
            # Start agents
            self.start_agents()
            
            # List agents
            self.list_agents()
            
            # Create tasks
            task_ids = self.create_tasks()
            
            if not task_ids:
                print("❌ No tasks created, exiting demo")
                return
            
            # Monitor execution
            self.monitor_tasks(task_ids, duration=40)
            
            # Show results
            self.show_results(task_ids)
            
            # Show metrics
            self.show_metrics()
            
            self.print_header("✅ Demo Complete!")
            print("\n📊 Check Grafana dashboard: http://localhost:3000")
            print("📈 Check Prometheus: http://localhost:9090")
            print(f"🌐 API: {API_URL}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Demo interrupted by user")
        finally:
            self.cleanup()

if __name__ == "__main__":
    demo = DemoOrchestrator()
    demo.run_demo()
