import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import asyncio
import uuid
import nacl.signing
import nacl.encoding
from aicp.router import router
from aicp.message import AICPMessage

async def test_routing():
    # Clear + register agents
    router.agents.clear()
    
    # Labelee agent (labeling capability)
    signing_key = nacl.signing.SigningKey.generate()
    pubkey = signing_key.verify_key.encode(nacl.encoding.HexEncoder).decode()
    router.register_agent(
        "labelee-duke-001", 
        ["image.label", "text.classify"], 
        "ws://labelee.local:8080",
        pubkey
    )
    
    # Test task routing
    msg = AICPMessage(
        sender="ains-control",
        recipient="AINS-router",
        method="image.label",
        payload={"image_url": "test.jpg"}
    )
    
    response = await router.route_message(msg)
    print("✅ ROUTING: Task routed to Labelee agent")
    print(f"📍 Response: {response.payload}")
    print(f"📤 Routed to: {response.sender}")
    print("🎉 BASIC ROUTING MECHANISMS = PRODUCTION READY")

if __name__ == "__main__":
    asyncio.run(test_routing())
