# DukeNet User Guides

Complete guides for using DukeNet (AINS) in your applications.

---

## Table of Contents

1. [Quick Start Guide](#quick-start-guide)
2. [Agent Integration Guide](#agent-integration-guide)
3. [Client Integration Guide](#client-integration-guide)
4. [Advanced Features Guide](#advanced-features-guide)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Quick Start Guide

### Installation

Clone repository
git clone https://github.com/theimma1/dukenet.git
cd dukenet/python

Create virtual environment
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate

Install dependencies
pip install -r requirements.txt

Initialize database
python -c "from ains.db import Base, engine; Base.metadata.create_all(bind=engine)"

Start server
uvicorn ains.api:app --reload



### Create Your First API Key

curl -X POST http://localhost:8000/ains/api-keys
-H "Content-Type: application/json"
-d '{
"client_id": "my_app",
"name": "Development Key",
"rate_limit_per_minute": 100
}'


**Response:**
{
"key_id": "key_abc123",
"api_key": "ains_veryLongSecureToken...",
"client_id": "my_app"
}



⚠️ **Save the `api_key` - it's only shown once!**

### Submit Your First Task

curl -X POST http://localhost:8000/ains/tasks
-H "X-API-Key: ains_YOUR_KEY_HERE"
-H "Content-Type: application/json"
-d '{
"client_id": "my_app",
"task_type": "analysis",
"capability_required": "data:v1",
"input_data": {
"file": "data.csv",
"algorithm": "regression"
},
"priority": 7
}'



---

## Agent Integration Guide

### Overview

Agents are workers that execute tasks. This guide shows how to build and integrate an agent.

### 1. Register Your Agent

import requests
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding

Generate key pair
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

Register agent
response = requests.post("http://localhost:8000/ains/agents", json={
"agent_id": "agent_001",
"display_name": "My Data Processor",
"public_key": public_key.public_bytes(...).decode(),
"endpoint": "https://myagent.example.com/tasks",
"signature": sign_registration(private_key),
"tags": ["data:v1", "ml:v1"]
})

print(f"Registered! Trust score: {response.json()['trust_score']}")



### 2. Implement Task Endpoint

Your agent must expose an endpoint to receive tasks:

from flask import Flask, request, jsonify

app = Flask(name)

@app.route('/tasks', methods=['POST'])
def handle_task():
task = request.json


try:
    # Execute task
    result = process_task(
        task_type=task['task_type'],
        input_data=task['input_data']
    )
    
    # Report success
    report_completion(task['task_id'], result)
    
    return jsonify({"status": "accepted"}), 200

except Exception as e:
    # Report failure
    report_failure(task['task_id'], str(e))
    return jsonify({"error": str(e)}), 500
def process_task(task_type, input_data):
"""Implement your task processing logic"""
if task_type == "data_analysis":
# Your analysis logic
return {"accuracy": 0.94, "predictions": [...]}
# Add more task types...

def report_completion(task_id, result):
"""Report task completion to AINS"""
requests.patch(f"http://localhost:8000/ains/tasks/{task_id}", json={
"status": "COMPLETED",
"result_data": result
})

def report_failure(task_id, error):
"""Report task failure to AINS"""
requests.patch(f"http://localhost:8000/ains/tasks/{task_id}", json={
"status": "FAILED",
"error_message": error
})

if name == 'main':
app.run(host='0.0.0.0', port=5000)



### 3. Handle Webhooks

Receive task assignments via webhooks:

@app.route('/webhook', methods=['POST'])
def webhook():
payload = request.get_data(as_text=True)
signature = request.headers.get('X-Webhook-Signature')


# Verify signature
if not verify_signature(payload, signature, WEBHOOK_SECRET):
    return jsonify({"error": "Invalid signature"}), 401

event = request.json

if event['event'] == 'task.assigned':
    task_data = event['data']
    # Queue task for execution
    task_queue.put(task_data)

return jsonify({"status": "received"}), 200
def verify_signature(payload, signature, secret):
import hmac
import hashlib


expected = hmac.new(
    secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()

return hmac.compare_digest(signature, expected)


### 4. Best Practices for Agents

**Performance:**
- Report progress for long-running tasks
- Implement timeouts to prevent hanging
- Use asynchronous processing for scalability

**Reliability:**
- Implement retry logic for transient failures
- Validate input data before processing
- Log errors for debugging

**Security:**
- Verify webhook signatures
- Use HTTPS for all communications
- Validate task authenticity

**Trust Building:**
- Complete tasks successfully
- Report accurate status updates
- Handle failures gracefully
- Meet SLA commitments

---

## Client Integration Guide

### Python Client Example

import requests

class AINSClient:
def init(self, base_url, api_key):
self.base_url = base_url
self.headers = {
"X-API-Key": api_key,
"Content-Type": "application/json"
}


def submit_task(self, task_type, capability, input_data, **kwargs):
    """Submit a new task"""
    response = requests.post(
        f"{self.base_url}/ains/tasks",
        headers=self.headers,
        json={
            "client_id": "my_app",
            "task_type": task_type,
            "capability_required": capability,
            "input_data": input_data,
            **kwargs
        }
    )
    response.raise_for_status()
    return response.json()

def get_task_status(self, task_id):
    """Check task status"""
    response = requests.get(
        f"{self.base_url}/ains/tasks/{task_id}",
        headers=self.headers
    )
    response.raise_for_status()
    return response.json()

def wait_for_completion(self, task_id, timeout=300, poll_interval=5):
    """Wait for task to complete"""
    import time
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        task = self.get_task_status(task_id)
        
        if task['status'] == 'COMPLETED':
            return task['result_data']
        elif task['status'] == 'FAILED':
            raise Exception(f"Task failed: {task['error_message']}")
        elif task['status'] == 'CANCELLED':
            raise Exception("Task was cancelled")
        
        time.sleep(poll_interval)
    
    raise TimeoutError(f"Task did not complete within {timeout}s")
Usage
client = AINSClient("http://localhost:8000", "ains_YOUR_KEY_HERE")

Submit task
task = client.submit_task(
task_type="data_analysis",
capability="data:v1",
input_data={"file": "data.csv"},
priority=7
)

print(f"Task ID: {task['task_id']}")

Wait for result
result = client.wait_for_completion(task['task_id'])
print(f"Result: {result}")



### JavaScript/Node.js Client

class AINSClient {
constructor(baseUrl, apiKey) {
this.baseUrl = baseUrl;
this.apiKey = apiKey;
}


async submitTask(taskType, capability, inputData, options = {}) {
    const response = await fetch(`${this.baseUrl}/ains/tasks`, {
        method: 'POST',
        headers: {
            'X-API-Key': this.apiKey,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            client_id: 'my_app',
            task_type: taskType,
            capability_required: capability,
            input_data: inputData,
            ...options
        })
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return await response.json();
}

async getTaskStatus(taskId) {
    const response = await fetch(`${this.baseUrl}/ains/tasks/${taskId}`, {
        headers: {
            'X-API-Key': this.apiKey
        }
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    return await response.json();
}

async waitForCompletion(taskId, timeout = 300000, pollInterval = 5000) {
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
        const task = await this.getTaskStatus(taskId);

        if (task.status === 'COMPLETED') {
            return task.result_data;
        } else if (task.status === 'FAILED') {
            throw new Error(`Task failed: ${task.error_message}`);
        } else if (task.status === 'CANCELLED') {
            throw new Error('Task was cancelled');
        }

        await new Promise(resolve => setTimeout(resolve, pollInterval));
    }

    throw new Error(`Task did not complete within ${timeout}ms`);
}
}

// Usage
const client = new AINSClient('http://localhost:8000', 'ains_YOUR_KEY_HERE');

(async () => {
try {
// Submit task
const task = await client.submitTask(
'data_analysis',
'data:v1',
{ file: 'data.csv' },
{ priority: 7 }
);


    console.log(`Task ID: ${task.task_id}`);

    // Wait for result
    const result = await client.waitForCompletion(task.task_id);
    console.log('Result:', result);
} catch (error) {
    console.error('Error:', error.message);
}
})();



---

## Advanced Features Guide

### Task Dependencies

Create tasks that depend on other tasks:

Submit first task
task1 = client.submit_task(
task_type="fetch_data",
capability="api:v1",
input_data={"source": "database"}
)

Submit dependent task
task2 = client.submit_task(
task_type="process_data",
capability="data:v1",
input_data={"operation": "transform"},
depends_on=[task1['task_id']] # Won't run until task1 completes
)

Check dependency status
deps = requests.get(
f"http://localhost:8000/ains/tasks/{task2['task_id']}/dependencies",
headers=client.headers
).json()

print(f"Ready to run: {deps['ready_to_run']}")



### Task Chains

Create multi-step workflows:

chain = requests.post(
"http://localhost:8000/ains/task-chains",
headers=client.headers,
json={
"name": "Data Pipeline",
"client_id": "my_app",
"steps": [
{
"name": "fetch",
"task_type": "fetch",
"capability_required": "api:v1",
"input_data": {"source": "database"}
},
{
"name": "process",
"task_type": "process",
"capability_required": "data:v1",
"use_previous_output": True # Uses fetch output
},
{
"name": "store",
"task_type": "store",
"capability_required": "storage:v1",
"use_previous_output": True # Uses process output
}
]
}
).json()

print(f"Chain ID: {chain['chain_id']}")

Monitor chain progress
status = requests.get(
f"http://localhost:8000/ains/task-chains/{chain['chain_id']}",
headers=client.headers
).json()

print(f"Step {status['current_step']} of {status['total_steps']}")



### Scheduled Tasks

Schedule recurring tasks:

schedule = requests.post(
"http://localhost:8000/ains/scheduled-tasks",
headers=client.headers,
json={
"name": "Daily Data Sync",
"client_id": "my_app",
"cron_expression": "0 2 * * *", # 2 AM daily
"timezone": "America/New_York",
"task_type": "sync",
"capability_required": "sync:v1",
"input_data": {"source": "external_api"},
"priority": 7
}
).json()

print(f"Schedule ID: {schedule['schedule_id']}")
print(f"Next run: {schedule['next_run_at']}")

Trigger immediately
requests.post(
f"http://localhost:8000/ains/scheduled-tasks/{schedule['schedule_id']}/run-now",
headers=client.headers
)



### Task Templates

Create reusable task configurations:

Create template
template = requests.post(
"http://localhost:8000/ains/task-templates",
headers=client.headers,
json={
"name": "Standard Analysis",
"client_id": "my_app",
"task_type": "analysis",
"capability_required": "data:v1",
"default_input_data": {
"algorithm": "regression",
"validation_split": 0.2
},
"default_priority": 6,
"default_timeout": 600
}
).json()

Use template
task = requests.post(
"http://localhost:8000/ains/tasks/from-template",
headers=client.headers,
json={
"template_id": template['template_id'],
"input_data": {
"file": "data.csv" # Override/extend defaults
},
"priority": 8 # Override priority
}
).json()



### Routing Strategies

Choose how tasks are assigned to agents:

Round-robin (default)
task = client.submit_task(
task_type="analysis",
capability="data:v1",
input_data={"file": "data.csv"},
routing_strategy="round_robin"
)

Trust-weighted (favor high-trust agents)
task = client.submit_task(
task_type="critical_analysis",
capability="data:v1",
input_data={"file": "sensitive.csv"},
routing_strategy="trust_weighted"
)

Least-loaded (route to least busy agent)
task = client.submit_task(
task_type="quick_check",
capability="data:v1",
input_data={"file": "small.csv"},
routing_strategy="least_loaded"
)

Fastest-response (route to fastest agent)
task = client.submit_task(
task_type="urgent_analysis",
capability="data:v1",
input_data={"file": "urgent.csv"},
routing_strategy="fastest_response"
)



---

## Best Practices

### For Clients

**1. Use Appropriate Priorities**
Critical business tasks
priority = 9-10

Standard production tasks
priority = 6-8

Background/batch tasks
priority = 1-5



**2. Set Reasonable Timeouts**
Quick operations
timeout_seconds = 30

Data processing
timeout_seconds = 300

Long-running ML training
timeout_seconds = 3600



**3. Handle Errors Gracefully**
try:
task = client.submit_task(...)
result = client.wait_for_completion(task['task_id'])
except requests.exceptions.HTTPError as e:
if e.response.status_code == 429:
# Rate limited - back off
time.sleep(60)
retry()
elif e.response.status_code == 503:
# Service unavailable - retry with exponential backoff
backoff_retry()
else:
# Other error - log and alert
logger.error(f"Task submission failed: {e}")



**4. Use Batch Operations**
Don't do this (slow)
for item in items:
client.submit_task(...)

Do this instead (10x faster)
requests.post(
f"{client.base_url}/ains/tasks/batch",
headers=client.headers,
json={
"tasks": [
{
"client_id": "my_app",
"task_type": "process",
"capability_required": "data:v1",
"input_data": {"item": item}
}
for item in items
]
}
)



### For Agents

**1. Report Status Accurately**
Update status immediately when starting
report_status(task_id, "RUNNING")

Report progress for long tasks
report_progress(task_id, percent=50)

Always report final status
report_status(task_id, "COMPLETED", result_data=result)



**2. Implement Proper Error Handling**
try:
result = process_task(task)
report_completion(task_id, result)
except ValidationError as e:
# Client error - don't retry
report_failure(task_id, f"Invalid input: {e}")
except TransientError as e:
# Temporary error - AINS will retry
report_failure(task_id, f"Temporary failure: {e}")
except Exception as e:
# Unexpected error - log and report
logger.exception("Unexpected error")
report_failure(task_id, f"Internal error: {e}")



**3. Build Trust**
- Complete tasks successfully (>95% success rate)
- Meet SLA commitments
- Report accurate status
- Handle errors gracefully
- Stay online and responsive

**4. Optimize Performance**
- Use asynchronous processing
- Implement connection pooling
- Cache frequently used data
- Monitor resource usage

---

## Troubleshooting

### Common Issues

**1. "401 Unauthorized"**
Problem: Invalid API key
Solution: Verify your API key is correct and active



**2. "429 Too Many Requests"**
Problem: Rate limit exceeded
Solution:

Check X-RateLimit-* headers

Implement exponential backoff

Request higher rate limits



**3. "503 Service Unavailable"**
Problem: No capable agents available
Solution:

Check if agents with required capability are registered

Verify agents are online and healthy

Consider registering more agents



**4. Task Stuck in PENDING**
Problem: No agent assigned
Solutions:

Verify agents with required capability exist

Check agent trust scores (may be filtered out)

Review agent availability

Check task dependencies (may be blocked)



**5. Task Keeps Failing**
Problem: Agent repeatedly fails task
Solutions:

Check task input data validity

Review agent error logs

Verify agent has required resources

Check for capability mismatch



### Debug Mode

Enable debug logging:

import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ains')

Now all API calls will be logged


### Health Checks

Check system health:

Check API health
curl http://localhost:8000/health

Check database connection
curl http://localhost:8000/ains/health/db

Check cache connection (if Redis enabled)
curl http://localhost:8000/ains/health/cache



---

**[API Documentation →](../api/README.md)**  
**[Architecture Overview →](../architecture/README.md)**