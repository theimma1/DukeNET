# ADR-001: DukeNET Protocol Stack Architecture

**Status:** Accepted  
**Date:** 2025-11-21  
**Author:** Immanuel Olajuyigbe

---

## Context

DukeNET needs to establish foundational protocols for AI agent communication. We must decide:

1. **How many protocol layers?**
   - Single monolithic protocol vs. layered stack
2. **Which serialization format?**
   - MessagePack vs. Protocol Buffers vs. JSON
3. **Authentication approach?**
   - Public key cryptography vs. shared secrets vs. tokens
4. **Performance vs. Security trade-off?**

---

## Decision

We adopt a **three-layer protocol stack**:

1. **Transport Layer (AICP):** Low-level messaging, authentication, encryption
2. **Application Layer (AITP):** Task orchestration, routing, decomposition
3. **Service Layer (AINS):** Agent discovery, naming, reputation

### Serialization

Primary: **MessagePack** (fast, compact, binary)  
Secondary: **Protocol Buffers** (schema-driven)  
Fallback: **JSON** (debugging, human-readable)

### Authentication

**Ed25519 public key cryptography**:
- Fast signing/verification (~1ms)
- Small key size (32 bytes)
- Modern standard (RFC 8032)
- Resistant to timing attacks

### Security Model

**Mutual authentication** at protocol level:
- Every message signed with source's private key
- Receiver verifies with source's public key
- Zero-trust architecture (verify every message)

---

## Rationale

| Decision | Rationale |
| :--- | :--- |
| Three layers | Separation of concerns, modularity, reusability |
| MessagePack | 2-10x faster than JSON, smaller payload size |
| Ed25519 | Better than RSA for our use case, standardized |
| Mutual auth | Prevents spoofing, replay attacks, impersonation |

---

## Consequences

**Positive:**
- Clear separation of concerns
- Extensible design (easy to add protocols)
- Strong security posture
- High performance

**Negative:**
- More complex than single monolithic protocol
- Requires clients to understand three layers
- Debugging may be harder with multiple layers

---

## Alternatives Considered

### 1. Monolithic Protocol
- **Pros:** Simpler, faster development
- **Cons:** Harder to modify, tightly coupled

### 2. REST API Instead of Binary
- **Pros:** Simple, HTTP well-understood
- **Cons:** 3-5x slower, larger payload, not ideal for real-time

### 3. HTTPS + JSON
- **Pros:** Already proven, libraries available
- **Cons:** 10-50ms overhead per request (too slow for 50ms target)

---

## Implementation Plan

- Phase 1: AICP (protocol layer)
- Phase 2: AINS (service layer)
- Phase 3: AITP (application layer)
- Phase 4: Integration testing

---

**End of ADR-001**
