# RFC: AI Communication Protocol (AICP)

**Title:** AI Communication Protocol (AICP) v1.0  
**Status:** Draft  
**Date:** 2025-11-21  
**Author:** DukeNET Team  
**Category:** Protocol Specification

---

## 1. Introduction

### 1.1 Overview

The AI Communication Protocol (AICP) is the foundational transport and messaging layer for the DukeNET ecosystem. It defines standardized, secure, low-latency communication between AI agents, analogous to TCP/IP for the traditional internet.

### 1.2 Motivation

Current AI systems lack:
- Standardized inter-agent communication
- Cryptographic identity verification
- Performance guarantees (latency, throughput)
- Built-in security at the protocol level

AICP solves these by providing:
- **Standardized Message Format:** Serializable, language-agnostic
- **Mutual Authentication:** Ed25519-based public key cryptography
- **Transport Security:** mTLS (mutual TLS) or direct encryption
- **Performance Targets:** <50ms latency, 100Gb/s throughput
- **Reliability:** Message ordering, delivery guarantees

### 1.3 Scope

AICP covers:
- Message structure and serialization
- Agent identity and authentication
- Routing and addressing
- Error handling and recovery
- Security model

Out of scope:
- Task orchestration (covered by AITP)
- Agent discovery (covered by AINS)
- Marketplace transactions (covered by Marketplace)

---

## 2. Message Format

### 2.1 Message Structure

All AICP messages follow this structure:

AICP Message
├── Header (96 bytes)
│ ├── Version (1 byte): 0x01
│ ├── Message Type (1 byte): REQUEST, RESPONSE, ACK, ERROR
│ ├── Message ID (8 bytes): UUID v4
│ ├── Timestamp (8 bytes): Unix nanoseconds
│ ├── Source Agent ID (32 bytes): Ed25519 public key hash
│ ├── Destination Agent ID (32 bytes): Ed25519 public key hash
│ ├── Payload Length (4 bytes): 0 to 1GB
│ ├── Flags (2 bytes): ENCRYPTED, SIGNED, REQUIRES_ACK, STREAMING
│ └── TTL (1 byte): 0-255 hops
│
└── Payload (variable)
├── Body (variable): JSON, MessagePack, or Protocol Buffers
├── Signature (64 bytes): Ed25519 signature over Header + Body
└── Nonce (16 bytes): For replay attack prevention

text

### 2.2 Message Types

| Type | Code | Purpose |
| :--- | :--- | :--- |
| REQUEST | 0x01 | Agent requests action/data from another agent |
| RESPONSE | 0x02 | Response to a REQUEST |
| ACK | 0x03 | Acknowledgment (no payload) |
| ERROR | 0x04 | Error notification |
| PING | 0x05 | Connection health check |
| BROADCAST | 0x06 | Message to multiple agents |

### 2.3 Serialization

Three serialization formats supported (with preference order):

1. **MessagePack** (default): Binary, fast, compact
2. **Protocol Buffers**: Schema-defined, strongly typed
3. **JSON**: Human-readable, debugging

Selection via Content-Type header in payload metadata.

---

## 3. Authentication & Security

### 3.1 Agent Identity

Each agent has a unique identity:

Agent Identity
├── Public Key: Ed25519 256-bit public key
├── Agent ID: SHA256(public_key) - 32 bytes
├── Name: Human-readable identifier (optional)
├── Capabilities: List of skills/permissions
├── Trust Score: 0-100 (managed by AINS)
└── Certificate Chain: X.509 (optional, for PKI)

text

### 3.2 Signing & Verification

**Signing Process:**
signature = Ed25519.sign(
private_key,
SHA256(header_bytes + body_bytes + nonce)
)

text

**Verification Process:**
verified = Ed25519.verify(
public_key,
message,
signature
)

text

### 3.3 Encryption

**For Encrypted Messages (ENCRYPTED flag set):**

encrypted_body = AES-256-GCM.encrypt(
key=HKDF(shared_secret, salt, info),
plaintext=body,
aad=header_bytes
)

text

Where `shared_secret` is derived via ECDH with X25519.

### 3.4 Transport Layer Security

**Option A: mTLS**
- Both client and server require valid certificates
- Recommended for production deployments
- 50ms handshake overhead

**Option B: Direct Encryption**
- Lightweight for high-frequency messaging
- Use when mTLS handshake is bottleneck
- Requires pre-shared key distribution

---

## 4. Protocol Flow

### 4.1 Basic Request-Response

Agent A Agent B
│ │
├──── REQUEST msg_id:123 ───>│
│ │
│ [Process]
│ │
│<──── RESPONSE msg_id:123 ───┤
│ │
├──────── ACK msg_id:123 ───>│
│ │

text

### 4.2 Streaming Messages

For large payloads or continuous streams:

Agent A Agent B
│ │
├─ REQUEST STREAMING msg:123 >│
│ │
│<─ RESPONSE stream_id:456 ───┤
│ │
│<─── CHUNK 1 of 10 ──────────┤
│ │
├────── ACK chunk:1 ─────────>│
│ │
│<─── CHUNK 2 of 10 ──────────┤
│ ... │
│<─── CHUNK 10 of 10 ─────────┤
│ │
├──── ACK stream:456 ────────>│

text

### 4.3 Error Handling

On error, respond with ERROR message:

{
"message_type": "ERROR",
"error_code": 4001,
"error_message": "Agent offline",
"original_message_id": "msg_id_123",
"retry_after_ms": 5000
}

text

**Common Error Codes:**
- 4001: Agent offline
- 4002: Authentication failed
- 4003: Message too large
- 4004: Timeout
- 5000: Server error

---

## 5. Performance Requirements

| Metric | Target | Tolerance |
| :--- | :--- | :--- |
| Latency (P99) | 50ms | ±10ms |
| Throughput | 100Gb/s | Per node |
| Message Size | 0-1GB | Streaming for >10MB |
| Delivery Guarantee | At-least-once | Idempotent operations |
| Connection Pooling | Enabled | Min 10 concurrent |

---

## 6. Backwards Compatibility

- Version field in header enables protocol evolution
- v1 implementations must support v1 messages
- Future versions (v2, v3) can coexist during migration
- Deprecation notices require 2 version cycles

---

## 7. Implementation Checklist

- [ ] Message serialization/deserialization
- [ ] Ed25519 key generation and signing
- [ ] mTLS certificate handling
- [ ] Message routing and delivery
- [ ] Error handling and retry logic
- [ ] Connection pooling
- [ ] Performance monitoring
- [ ] Unit tests (>90% coverage)
- [ ] Integration tests with multiple agents
- [ ] Benchmarks against target latency

---

## 8. References

- RFC 3394: Advanced Encryption Standard (AES) Key Wrap Algorithm
- RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)
- RFC 8439: ChaCha20 and Poly1305
- NIST SP 800-38D: Recommendation for Block Cipher Modes of Operation

---

**End of AICP-RFC.md**
