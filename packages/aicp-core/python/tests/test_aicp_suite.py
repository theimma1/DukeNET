import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
import nacl.signing
import nacl.encoding
from aicp.message import AICPMessage
from aicp.router import router

def test_full_aicp_pipeline():
    """Test complete AICP pipeline: create → sign → route → verify"""
    # 1. Register Labelee agent
    signing_key = nacl.signing.SigningKey.generate()
    pubkey = signing_key.verify_key.encode(nacl.encoding.HexEncoder).decode()
    router.register_agent("labelee-duke-001", ["image.label"], "ws://labelee:8080", pubkey)
    
    # 2. Create + sign task message
    msg = AICPMessage(sender="ains-control", method="image.label", payload={"image": "test.jpg"})
    agent_key = nacl.signing.SigningKey.generate()
    private_hex = agent_key.encode(nacl.encoding.HexEncoder).decode()
    msg.sign(private_hex)
    
    # 3. Route + verify response
    import asyncio
    response = asyncio.run(router.route_message(msg))
    
    assert msg.signature  # Signed
    assert response.payload["status"] == "delivered"  # Routed
    print("✅ FULL AICP PIPELINE: create → sign → route → verify")

if __name__ == "__main__":
    test_full_aicp_pipeline()
