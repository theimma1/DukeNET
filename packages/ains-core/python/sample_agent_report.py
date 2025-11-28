#!/usr/bin/env python3
"""
Sample Report Generation Agent
Demonstrates document creation capabilities
"""

import requests
import time
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReportGenerationAgent:
    def __init__(self, agent_id: str, api_url: str = "http://localhost:8000"):
        self.agent_id = agent_id
        self.api_url = api_url
        self.capabilities = ["report-generation", "data-visualization", "pdf-creation"]
        self.running = False
        
    def register(self):
        """Register agent with AINS"""
        response = requests.post(
            f"{self.api_url}/ains/agents",
            json={
                "agent_id": self.agent_id,
                "display_name": "Report Generator",
                "endpoint": f"http://localhost:9002",
                "public_key": f"pk_{self.agent_id}",
                "capabilities": self.capabilities,
                "signature": "sig_placeholder",
                "metadata": {
                    "version": "1.0.0",
                    "type": "report-generator"
                }
            }
        )
        if response.status_code == 200:
            logger.info(f"✅ Agent {self.agent_id} registered")
            return True
        else:
            logger.error(f"❌ Registration failed: {response.text}")
            return False
    
    def send_heartbeat(self):
        """Send heartbeat to AINS"""
        try:
            response = requests.post(
                f"{self.api_url}/ains/agents/{self.agent_id}/heartbeat",
                json={
                    "status": "ACTIVE",
                    "metrics": {
                        "uptime_seconds": int(time.time()),
                        "reports_generated": 0,
                        "memory_usage_mb": 256.0
                    }
                }
            )
            if response.status_code == 200:
                logger.debug("❤️  Heartbeat sent")
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
    
    def poll_tasks(self):
        """Poll for assigned tasks"""
        try:
            response = requests.get(
                f"{self.api_url}/aitp/tasks",
                params={
                    "assigned_agent_id": self.agent_id,
                    "status": "ASSIGNED"
                }
            )
            if response.status_code == 200:
                data = response.json()
                tasks = data.get("tasks", []) if isinstance(data, dict) else data
                return tasks
        except Exception as e:
            logger.error(f"Task polling failed: {e}")
        return []
    
    def generate_report(self, report_data: dict) -> dict:
        """Simulate report generation"""
        time.sleep(3)  # Simulate processing
        
        return {
            "report_id": f"RPT-{int(time.time())}",
            "title": report_data.get("title", "System Report"),
            "pages": 15,
            "format": "PDF",
            "file_size_mb": 2.4,
            "charts_included": 5,
            "generation_time": 3.2,
            "timestamp": datetime.now().isoformat()
        }
    
    def execute_task(self, task):
        """Execute a report generation task"""
        task_id = task.get("task_id")
        logger.info(f"📊 Generating report: {task_id}")
        
        # Update status to ACTIVE
        requests.put(
            f"{self.api_url}/aitp/tasks/{task_id}/status",
            json={"status": "ACTIVE"}
        )
        
        # Generate the report
        result = self.generate_report(task.get("input_data", {}))
        
        # Report completion
        requests.put(
            f"{self.api_url}/aitp/tasks/{task_id}/status",
            json={
                "status": "COMPLETED",
                "result_data": result
            }
        )
        
        logger.info(f"✅ Task {task_id} completed")
    
    def run(self):
        """Main agent loop"""
        if not self.register():
            return
        
        self.running = True
        logger.info(f"🚀 {self.agent_id} running...")
        
        heartbeat_counter = 0
        
        while self.running:
            # Send heartbeat every 30 seconds
            if heartbeat_counter % 30 == 0:
                self.send_heartbeat()
            
            # Poll for tasks
            tasks = self.poll_tasks()
            for task in tasks:
                self.execute_task(task)
            
            time.sleep(1)
            heartbeat_counter += 1

if __name__ == "__main__":
    agent = ReportGenerationAgent(agent_id="report-agent-001")
    
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Agent shutting down...")
        agent.running = False
