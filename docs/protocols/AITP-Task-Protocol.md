# AITP: AI Task Protocol

**Title:** AI Task Protocol (AITP) v1.0  
**Status:** Draft  
**Date:** 2025-11-21  
**Author:** DukeNET Team

---

## 1. Overview

AITP defines how agents:
- Request complex, multi-step tasks
- Decompose tasks into subtasks
- Route subtasks to capable agents
- Track progress and aggregate results
- Handle failures and retries

AITP is analogous to HTTP for task orchestration.

---

## 2. Task Definition Format

### 2.1 Basic Task Structure

Task:
task_id: "task_uuid_v4"
name: "Research Paper Analysis"
description: "Analyze a research paper and extract key findings"

goal: |
Extract key findings from the research paper including:
- Main hypothesis
- Methodology
- Key results
- Limitations

input:
type: "object"
properties:
paper_pdf_url:
type: "string"
format: "uri"
max_pages:
type: "integer"
default: 50

output:
type: "object"
properties:
hypothesis:
type: "string"
methodology:
type: "string"
results:
type: "array"
items:
type: "string"
limitations:
type: "string"

created_at: 1700614200
created_by: "agent_id_requester"
priority: "HIGH" | "NORMAL" | "LOW"
status: "PENDING" | "EXECUTING" | "COMPLETED" | "FAILED"

text

### 2.2 Task Metadata

Metadata:
deadline: 1700700600 # Unix timestamp
timeout_seconds: 3600
retry_policy:
max_retries: 3
backoff_strategy: "exponential" # exponential, linear, fixed
backoff_base_ms: 1000

cost_limit: 10.00 # USD or tokens
estimated_cost: 5.50
actual_cost: 0.00

tags: ["research", "nlp", "analysis"]
dependencies: [] # task_ids this depends on

text

---

## 3. Task Decomposition

Complex tasks can be decomposed into subtasks.

### 3.1 Decomposition Schema

Subtasks:

subtask_id: "subtask_1"
name: "Extract Text from PDF"
agent_capability: "pdf_text_extraction"

input:
paper_pdf_url: "${parent.input.paper_pdf_url}"
max_pages: "${parent.input.max_pages}"

output_mapping:
extracted_text: "raw_text"

priority: 1

subtask_id: "subtask_2"
name: "Analyze Text with NLP"
agent_capability: "nlp_analysis"

depends_on: ["subtask_1"]

input:
text: "${subtask_1.output.raw_text}"

output_mapping:
analysis: "nlp_results"

priority: 2

subtask_id: "subtask_3"
name: "Aggregate Results"
agent_capability: "orchestration"

depends_on: ["subtask_1", "subtask_2"]

input:
raw_text: "${subtask_1.output.raw_text}"
nlp_results: "${subtask_2.output.nlp_results}"

output_mapping: {}

priority: 3

text

### 3.2 Data Flow

subtask_1 (extract text)
↓
subtask_2 (analyze text) ← uses output from subtask_1
↓
subtask_3 (aggregate) ← uses outputs from subtask_1 & 2
↓
final output

text

---

## 4. Task Routing

### 4.1 Agent Selection Criteria

When routing a task, consider:

Selection Criteria:

capability_match: 0.0 - 1.0 (how well agent matches task)

trust_score: 0 - 100 (agent's reputation)

availability: 0.0 - 1.0 (currently free/busy)

latency: milliseconds

cost: price per unit

specialization: how many times agent has done this task

text

### 4.2 Routing Algorithm

FOR each subtask:

Query AINS for agents with required capability

Filter by min_trust_score (configurable, default 50)

Check agent availability (ping via AICP)

Calculate score:
score = (capability_match * 0.3) +
(trust_score / 100 * 0.3) +
(1 - latency/1000 * 0.2) +
(1 - cost/max_cost * 0.2)

Select agent with highest score

Send task via AICP

text

---

## 5. Execution Model

### 5.1 Task States

PENDING → EXECUTING → COMPLETED
↓ ↓ ↓
│ RETRYING SUCCESS
│ ↓
└──────FAILED

text

### 5.2 State Transitions

| From | To | Trigger | Condition |
| :--- | :--- | :--- | :--- |
| PENDING | EXECUTING | Agent accepted | Agent confirmed receipt |
| EXECUTING | COMPLETED | Agent finished | Time limit not exceeded |
| COMPLETED | SUCCESS | Valid output | Output schema matches |
| EXECUTING | RETRYING | Agent error | Retries remaining |
| RETRYING | EXECUTING | Backoff complete | New agent selected |
| EXECUTING | FAILED | Max retries exceeded | No more attempts |

### 5.3 Progress Tracking

Progress:
task_id: "task_uuid"
current_step: 2
total_steps: 3
percent_complete: 66

steps:
- step_id: 1
name: "Extract Text"
status: "COMPLETED"
started_at: 1700614200
completed_at: 1700614220
agent_id: "agent_1"

text
- step_id: 2
  name: "Analyze Text"
  status: "EXECUTING"
  started_at: 1700614220
  agent_id: "agent_2"
  
- step_id: 3
  name: "Aggregate Results"
  status: "PENDING"
  agent_id: null
text

---

## 6. Error Handling & Retry

### 6.1 Retry Policy

Retry Policy:
max_retries: 3
backoff_strategy: "exponential"

Example with exponential backoff (base 1000ms):
Attempt 1: Immediate
Attempt 2: Wait 1000ms then retry
Attempt 3: Wait 2000ms then retry
Attempt 4: Wait 4000ms then retry
Give up: All retries exhausted

text

### 6.2 Fallback Strategies

Fallback:
on_agent_offline:
strategy: "SELECT_NEXT_BEST"
# Try next best agent from AINS

on_timeout:
strategy: "RETRY_WITH_TIMEOUT_EXTENSION"
extended_timeout_seconds: 7200

on_cost_exceeded:
strategy: "FAIL_AND_NOTIFY"
notification: "Task exceeded budget"

on_capability_unavailable:
strategy: "DEFER"
# Try again in 5 minutes

text

---

## 7. Cost Model

### 7.1 Pricing

Cost Calculation:
subtask_cost = agent_pricing.price_per_unit * units_consumed

Examples:
- Image classification: $0.001 per image
- NLP analysis: $0.01 per 1000 tokens
- Agent orchestration: $0.10 per task

text

### 7.2 Cost Tracking

Cost Ledger:
task_id: "task_uuid"
budget: 10.00

entries:
- subtask_id: "subtask_1"
agent_id: "agent_1"
units: 1
price_per_unit: 0.001
total: 0.001

text
- subtask_id: "subtask_2"
  agent_id: "agent_2"
  units: 5000
  price_per_unit: 0.00001
  total: 0.050
total_cost: 0.051
remaining_budget: 9.949

text

---

## 8. API Endpoints

### 8.1 Submit Task

POST /aitp/tasks
Content-Type: application/json

{
"name": "Research Paper Analysis",
"description": "...",
"goal": "...",
"input": {...},
"output": {...},
"metadata": {...}
}

Response (201):
{
"task_id": "task_uuid",
"status": "PENDING",
"created_at": 1700614200
}

text

### 8.2 Get Task Status

GET /aitp/tasks/{task_id}

Response:
{
"task_id": "task_uuid",
"status": "EXECUTING",
"progress": {...},
"current_step": 2,
"estimated_completion": 1700614800,
"cost_so_far": 0.051
}

text

### 8.3 Get Task Result

GET /aitp/tasks/{task_id}/result

Response (when completed):
{
"task_id": "task_uuid",
"status": "COMPLETED",
"result": {...},
"cost": 0.051,
"execution_time_ms": 12345
}

text

---

## 9. Implementation Checklist

- [ ] Task definition schema validation
- [ ] Task decomposition engine
- [ ] Agent routing algorithm
- [ ] Task state machine
- [ ] Progress tracking
- [ ] Retry mechanism
- [ ] Cost calculation
- [ ] API endpoints
- [ ] Database schema
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance benchmarks

---

**End of AITP-Task-Protocol.md**
