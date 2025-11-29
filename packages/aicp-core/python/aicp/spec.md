# AICP Message Structure v0.1

class AICPMessage:
version: str = "1.0" # Protocol version
id: str # Unique message ID (UUID)
timestamp: int # Unix timestamp (ms)
sender: str # Sender agent ID
recipient: str # Target agent ID or "broadcast"
type: str # "request", "response", "heartbeat", "error"
method: str # "task.submit", "capability.query", etc.
payload: dict # JSON-serializable data
signature: str # Ed25519 signature (later)
