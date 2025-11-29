# AICP RFC 001 - Agent Intercommunication Protocol v1.0

**Status:** **PROPOSED** → **ACTIVE** (Production Live Nov 28, 2025)  
**Author:** Immanuel Olajuyigbe (DukeNET)  
**Implements:** Ed25519 + msgspec serialization  
**Reference Impl:** `aicp/message.py` (2475 bytes)

## 1. Abstract

AICP defines a **cryptographically-secure, capability-based protocol** for AI agents to discover, route, and execute tasks across decentralized networks.

**Key Properties:**
✅ Zero-trust: Ed25519 signatures on ALL messages
✅ Capability-based: "image.label" → agent routing
✅ Compact: 222 bytes serialized (vs 500+ JSON)
✅ Extensible: JSON payload + typed methods
✅ Replay-proof: UUID + timestamps

text

## 2. Message Format (Binary + msgspec)

@dataclass
class AICPMessage:
version: str # "1.0"
id: str # UUIDv4
timestamp: int # Unix ms
sender: str # pubkey_hash (32 bytes)
recipient: str # pubkey_hash OR "*"
type: str # "request" | "response" | "heartbeat"
method: str # "image.label" | "text.classify"
payload: Any # JSON dict
signature: str # base64(Ed25519(msg_hash))

text

**Serialized Size:** 222 bytes avg  
**Signature:** 64 bytes (88 b64)

## 3. Crypto Layer (Ed25519)

Private Key: 32 bytes (hex encoded)
Public Key: 32 bytes (agent ID = hash(pubkey))
Signature: sign(sha256(message_bytes))

Verification: verify(pubkey, message_bytes, signature)

text

**Example:**
SENDER: c1adf48636cc391e619c... (truncated)
SIGNATURE: M1hUzlcH0RwcQq4ss2OIMraiNcYnjN...
VERIFIED: True ✅

text

## 4. Capability Routing

METHOD → AGENT REGISTRY
"image.label" → labelee-duke-REAL
"text.classify" → nlp-agent-001
"data.process" → compute-farm-v2

text

**Router Algorithm:**
1. Extract `method` from request
2. Query capability registry: `SELECT agent WHERE capabilities LIKE '%method%'`
3. Return highest trust/availability agent
4. Route signed AICPMessage

## 5. Message Flow (End-to-End)

[ AINS ] ──(1)──> [ ROUTER ] ──(2)──> [ LABELEE ]
| POST /tasks | Query caps | Forward pass
| | | 111M params
↓ ↓ ↓
[ Response ] <─────── [ Signed ] <─────── [ AICP ]

text

**Full Trace (Production):**
✅ AICPMessage created: method="image.label"
✅ Signed: True (Ed25519)
✅ Routed: labelee-duke-REAL
✅ Inferred: torch.Size()
✅ Response signed: True
✅ Verified: True ✅

text

## 6. Wire Format (Binary)

08 01 76 65 72 73 69 6f 6e 3a 31 2e 30 # "version:1.0"
... (UUID, timestamp)
... (sender pubkey hash)
6d 65 74 68 6f 64 3a 69 6d 61 67 65 2e 6c 61 62 65 6c # "method:image.label"
... (JSON payload)
... (64-byte Ed25519 signature)

text

## 7. Error Codes

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Invalid signature | `verify() == False` |
| 404 | No agent for capability | `"image.label" not found` |
| 429 | Rate limited | `>60 req/min per agent` |
| 500 | Inference failed | `torch.cuda.OOMError` |

## 8. Security Considerations

- **Replay Protection:** UUIDv4 + monotonic timestamps
- **Agent Identity:** `hash(Ed25519_pubkey)` (collision resistant)
- **Payload Safety:** JSON only (no code execution)
- **Rate Limiting:** Per-sender, exponential backoff

## 9. Reference Implementation

pip install msgspec nacl
python -m aicp.message # 222 bytes serialized ✅

text

**Production Usage:**
msg = AICPMessage(method="image.label", payload={"url": "img.jpg"})
msg.sign(private_hex) # <1ms
router.route(msg) # Capability match
result = await agent.handle(msg) # Labelee inference

text

## 10. Future Extensions (v2.0)

- [ ] Multi-party signing (threshold crypto)
- [ ] Streaming payloads (large images/videos)  
- [ ] Payment channels (agent micropayments)
- [ ] WebSocket transport layer
- [ ] Agent attestation (remote proving)

---

**RFC 001 Status:** **ACTIVE** (DukeNET Production)  
**First Deployment:** Nov 28, 2025 8:45PM CST  
**Agents Live:** 3 (labelee-duke-REAL + others)  
**Tasks Executed:** 50+ (image.label verified)
