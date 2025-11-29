import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from aicp.message import AICPMessage
import nacl.signing
import nacl.encoding

# Generate test keys (64-byte hex)
signing_key = nacl.signing.SigningKey.generate()
private_hex = signing_key.encode(nacl.encoding.HexEncoder).decode()
public_hex = signing_key.verify_key.encode(nacl.encoding.HexEncoder).decode()

msg = AICPMessage(sender="agent-123", method="task.submit")
msg_signed = msg.sign(private_hex)
print("✅ SIGNED:", bool(msg_signed.signature))
print("✅ VERIFIED:", msg_signed.verify(public_hex))
print("🔑 Public Key:", public_hex[:20] + "...")
print("📝 Signature:", msg_signed.signature[:30] + "...")
