import uuid
import time
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import msgspec
import nacl.signing
import nacl.encoding
import base64

@dataclass
class AICPMessage:
    version: str = "1.0"
    id: str = None
    timestamp: int = None
    sender: str = ""
    recipient: str = ""
    type: str = "request"
    method: str = ""
    payload: Dict[str, Any] = None
    signature: Optional[str] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = int(time.time() * 1000)
        if self.payload is None:
            self.payload = {}
    
    def serialize(self) -> bytes:
        """Binary serialization using msgspec"""
        encoder = msgspec.json.Encoder()
        return encoder.encode(asdict(self))
    
    @classmethod
    def deserialize(cls, data: bytes) -> 'AICPMessage':
        """Deserialize from binary"""
        decoder = msgspec.json.Decoder(cls)
        return decoder.decode(data)
    
    def to_json(self) -> str:
        """JSON for debugging/logs"""
        return json.dumps(asdict(self), indent=2)
    
    def sign(self, private_key_hex: str) -> 'AICPMessage':
        """Sign message with Ed25519 private key"""
        private_bytes = bytes.fromhex(private_key_hex)
        signing_key = nacl.signing.SigningKey(private_bytes)
        # Sign JSON without signature field
        unsigned_data = {k: v for k, v in asdict(self).items() if k != 'signature'}
        message_bytes = msgspec.json.encode(unsigned_data)
        signed = signing_key.sign(message_bytes)
        self.signature = base64.b64encode(signed.signature).decode()
        return self
    
    def verify(self, public_key_hex: str) -> bool:
        """Verify signature with public key"""
        if not self.signature:
            return False
        public_bytes = bytes.fromhex(public_key_hex)
        verify_key = nacl.signing.VerifyKey(public_bytes)
        # Verify same unsigned data
        unsigned_data = {k: v for k, v in asdict(self).items() if k != 'signature'}
        message_bytes = msgspec.json.encode(unsigned_data)
        try:
            verify_key.verify(message_bytes, base64.b64decode(self.signature))
            return True
        except:
            return False

if __name__ == "__main__":
    msg = AICPMessage(sender="test-agent")
    print("✅ DIRECT TEST:", msg.to_json())
