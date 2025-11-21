# AINS: Agent Identity and Naming System - Registry Schema

**Title:** AINS Registry Schema v1.0  
**Status:** Draft  
**Date:** 2025-11-21  
**Author:** DukeNET Team

---

## 1. Overview

AINS (Agent Identity and Naming System) is a distributed directory service that:
- Registers and discovers AI agents
- Maintains capability catalogs
- Manages trust scores and reputation
- Provides semantic search over agent capabilities

AINS is analogous to DNS + LinkedIn for AI agents.

---

## 2. Agent Identity Record (AIR)

Every agent registered in AINS has an immutable core record plus mutable metadata.

### 2.1 Immutable Core

Agent Identity Record (AIR)
├── agent_id: "a1b2c3d4..." (SHA256 of public key, 64 hex chars)
├── created_at: 1700613600 (Unix timestamp)
├── public_key: "ed25519_MFkwEwY..." (base64)
├── owner_address: "0x1234...abcd" (Ethereum-style address)
└── genesis_block: 12345 (Blockchain block number, optional)

text

### 2.2 Mutable Metadata

Metadata
├── display_name: "Duke Research Agent"
├── description: "Multimodal agent for research"
├── version: "1.0.0"
├── endpoint: "https://agent.dukenet.io"
├── last_heartbeat: 1700614200
├── status: "ACTIVE" | "INACTIVE" | "SUSPENDED"
├── tags: ["research", "multimodal", "ml"]
└── avatar_url: "https://..."

text

### 2.3 Capabilities Registry

Capabilities:

capability_id: "cap_vision_001"
name: "Image Classification"
description: "Classify images into 1000 categories"
input_schema:
type: "object"
properties:
image:
type: "string"
format: "uri"
output_schema:
type: "object"
properties:
labels:
type: "array"
items:
type: "string"
version: "1.0"
deprecated: false
pricing:
model: "per_call" | "subscription" | "free"
price: 0.001 # in USD or tokens
currency: "USD"
slo:
latency_p99: 500 # ms
availability: 99.9 # percent
last_updated: 1700614200

capability_id: "cap_orchestration_001"
name: "Multi-Agent Orchestration"

... similar structure
text

---

## 3. Trust & Reputation System

### 3.1 Trust Score Calculation

Trust Score = (reputation_score * 0.6) + (uptime * 0.3) + (performance * 0.1)

Where:
reputation_score: 0-100 (user ratings, transaction history)
uptime: 0-100 (% time agent was available)
performance: 0-100 (SLA compliance)

text

### 3.2 Trust Metadata

Trust Record
├── agent_id: "a1b2c3d4..."
├── trust_score: 87
├── reputation:
│ ├── rating: 4.7 / 5.0
│ ├── total_ratings: 342
│ ├── successful_transactions: 1024
│ └── failed_transactions: 3
├── uptime:
│ ├── last_30_days: 99.98%
│ ├── last_90_days: 99.95%
│ └── all_time: 99.92%
├── performance:
│ ├── avg_latency_ms: 45
│ ├── p99_latency_ms: 120
│ └── success_rate: 99.97%
├── security:
│ ├── verified_signer: true
│ ├── rate_limited: false
│ ├── fraud_flags: 0
│ └── last_audit: 1700614200
└── updated_at: 1700614200

text

---

## 4. Query Interface

### 4.1 Lookup by Agent ID

GET /ains/agents/{agent_id}

Response:
{
"agent_id": "a1b2c3d4...",
"display_name": "Duke Agent",
"public_key": "...",
"capabilities": [...],
"trust_score": 87,
"endpoint": "https://...",
"status": "ACTIVE"
}

text

### 4.2 Search by Capability

GET /ains/search?capability=image_classification&limit=10

Response:
{
"results": [
{
"agent_id": "a1b2c3d4...",
"display_name": "Duke Vision Agent",
"trust_score": 92,
"capability_match": 0.98,
"pricing": {...}
},
...
]
}

text

### 4.3 Search by Tags

GET /ains/search?tags=research,ml&sort=trust_score

Response:
{
"results": [...]
}

text

---

## 5. Registration Flow

### 5.1 Agent Registration

Agent generates Ed25519 keypair (if not exists)

Agent computes agent_id = SHA256(public_key)

Agent submits registration request:
{
"agent_id": "...",
"public_key": "...",
"display_name": "My Agent",
"capabilities": [...],
"endpoint": "https://...",
"signature": Ed25519.sign(private_key, registration_data)
}

AINS verifies signature

AINS stores agent record

Agent receives confirmation with registration timestamp

Agent can now be discovered and receive tasks

text

### 5.2 Capability Publishing

Agent creates capability definition

Agent sends to /ains/agents/{agent_id}/capabilities:
{
"capability_id": "cap_vision_001",
"name": "Image Classification",
"input_schema": {...},
"output_schema": {...},
"pricing": {...},
"signature": Ed25519.sign(private_key, capability_data)
}

AINS stores capability record

Capability becomes discoverable immediately

AINS updates search indexes

text

---

## 6. Update & Heartbeat Protocol

### 6.1 Heartbeat

Agents should send heartbeats every 5 minutes:

POST /ains/agents/{agent_id}/heartbeat
{
"timestamp": 1700614200,
"status": "ACTIVE",
"uptime_ms": 86400000,
"signature": Ed25519.sign(private_key, heartbeat_data)
}

text

### 6.2 Metadata Updates

Agents can update mutable fields:

PATCH /ains/agents/{agent_id}
{
"display_name": "Updated Name",
"description": "New description",
"endpoint": "https://new-endpoint.io",
"tags": ["new", "tags"],
"signature": Ed25519.sign(private_key, update_data)
}

text

---

## 7. Data Persistence

### 7.1 Storage Layers

- **Primary:** PostgreSQL (hot data, fast queries)
- **Distributed:** IPFS/DHT (immutable history, blockchain)
- **Cache:** Redis (agent lookup, search results)

### 7.2 Replication

- Multi-region PostgreSQL replicas
- Eventually consistent DHT
- Cache invalidation on updates

---

## 8. Schema Versioning

Schema Version: 1.0
Supported Major Versions:​
Deprecation Timeline:
1.0: Current (until Nov 2026)
2.0: Available (from Nov 2025)
0.9: Deprecated (until Nov 2024)

text

---

## 9. Implementation Checklist

- [ ] Agent ID generation (SHA256 hashing)
- [ ] Public key cryptography integration
- [ ] Agent registration endpoint
- [ ] Capability registry storage
- [ ] Search/discovery API
- [ ] Trust score calculation
- [ ] Heartbeat mechanism
- [ ] Update handling
- [ ] Data persistence (PostgreSQL + cache)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance benchmarks (< 100ms lookup)

---

**End of AINS-Registry-Schema.md**
