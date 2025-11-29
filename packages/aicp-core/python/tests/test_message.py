import sys
import os
# Fix Python path to find aicp module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from aicp.message import AICPMessage

def test_message_serialization():
    msg = AICPMessage(
        sender="agent-123",
        recipient="agent-456",
        type="request",
        method="task.submit",
        payload={"data": "hello world"}
    )
    
    # Serialize → Deserialize roundtrip
    binary = msg.serialize()
    msg2 = AICPMessage.deserialize(binary)
    
    assert msg2.sender == "agent-123"
    assert msg2.id == msg.id  # Same UUID
    assert msg2.payload == {"data": "hello world"}
    
    print("✅ AICP Message serialization: PASS")
    print(f"📦 Binary size: {len(binary)} bytes")
    print(f"📄 JSON preview:\n{msg.to_json()}")

if __name__ == "__main__":
    test_message_serialization()
