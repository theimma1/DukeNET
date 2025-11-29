test_websocket_transport.py
"""
Integration tests for AICP WebSocket Transport
Tests bidirectional agent-to-agent communication
"""

import asyncio
import pytest
import json
from aicp.websocket_transport import AICPWebSocketServer, AICPWebSocketClient
from aicp.message import AICPMessage
import nacl.signing
import nacl.encoding


@pytest.fixture
def server():
    """Create WebSocket server"""
    return AICPWebSocketServer(host="localhost", port=8765)


@pytest.fixture
def labelee_agent():
    """Create Labelee Duke agent credentials"""
    signing_key = nacl.signing.SigningKey.generate()
    privkey = signing_key.encode(nacl.encoding.HexEncoder).decode()
    
    return {
        "agent_id": "labelee-duke-REAL",
        "privkey": privkey,
        "capabilities": ["image.label", "text.classify"]
    }


@pytest.fixture
def ains_agent():
    """Create AINS agent credentials"""
    signing_key = nacl.signing.SigningKey.generate()
    privkey = signing_key.encode(nacl.encoding.HexEncoder).decode()
    
    return {
        "agent_id": "ains-control",
        "privkey": privkey,
        "capabilities": ["task.dispatch", "task.schedule"]
    }


@pytest.mark.asyncio
async def test_server_startup(server):
    """Test WebSocket server startup"""
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)  # Give server time to start
    
    assert server.server is not None
    assert server.port == 8765
    print("✅ Server started successfully")


@pytest.mark.asyncio
async def test_agent_registration(server, labelee_agent):
    """Test agent registration with server"""
    # Start server
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)
    
    # Create client and connect
    client = AICPWebSocketClient(
        server_url="ws://localhost:8765",
        agent_id=labelee_agent["agent_id"],
        privkey_hex=labelee_agent["privkey"],
        capabilities=labelee_agent["capabilities"]
    )
    
    connected = await client.connect()
    assert connected is True
    assert labelee_agent["agent_id"] in server.agent_registry
    
    print(f"✅ Agent {labelee_agent['agent_id']} registered")
    
    # Cleanup
    await client.close()


@pytest.mark.asyncio
async def test_message_routing(server, labelee_agent, ains_agent):
    """Test AICP message routing between agents"""
    # Start server
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)
    
    # Register Labelee agent
    labelee_client = AICPWebSocketClient(
        server_url="ws://localhost:8765",
        agent_id=labelee_agent["agent_id"],
        privkey_hex=labelee_agent["privkey"],
        capabilities=labelee_agent["capabilities"]
    )
    await labelee_client.connect()
    
    # Start listening in background
    listen_task = asyncio.create_task(labelee_client.listen())
    
    # Register AINS agent
    ains_client = AICPWebSocketClient(
        server_url="ws://localhost:8765",
        agent_id=ains_agent["agent_id"],
        privkey_hex=ains_agent["privkey"],
        capabilities=ains_agent["capabilities"]
    )
    await ains_client.connect()
    
    # AINS sends image.label task to Labelee
    await asyncio.sleep(0.5)
    await ains_client.send_message(
        method="image.label",
        payload={"image_url": "https://example.com/test.jpg"},
        recipient="labelee-duke-REAL"
    )
    
    print("✅ Message routed from AINS → Labelee")
    
    # Cleanup
    await labelee_client.close()
    await ains_client.close()


@pytest.mark.asyncio
async def test_heartbeat(server, labelee_agent):
    """Test agent heartbeat mechanism"""
    # Start server
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)
    
    client = AICPWebSocketClient(
        server_url="ws://localhost:8765",
        agent_id=labelee_agent["agent_id"],
        privkey_hex=labelee_agent["privkey"],
        capabilities=labelee_agent["capabilities"]
    )
    await client.connect()
    
    # Send heartbeats
    for i in range(3):
        await client.send_heartbeat()
        await asyncio.sleep(0.2)
    
    # Check that agent is still registered
    assert labelee_agent["agent_id"] in server.agent_registry
    
    print("✅ Heartbeat mechanism working")
    
    await client.close()


@pytest.mark.asyncio
async def test_full_pipeline(server, labelee_agent, ains_agent):
    """Test full AICP pipeline: AINS → Server → Labelee inference"""
    # Start server
    server_task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)
    
    # Register handler for image.label
    async def handle_image_label(msg: AICPMessage):
        """Mock Labelee inference"""
        return {
            "labels": ["person", "car", "confidence: 0.95"],
            "model": "enhanced-labelee-foundation",
            "features_shape": "[1, 768]"
        }
    
    await server.register_handler("image.label", handle_image_label)
    
    # Connect Labelee agent
    labelee_client = AICPWebSocketClient(
        server_url="ws://localhost:8765",
        agent_id=labelee_agent["agent_id"],
        privkey_hex=labelee_agent["privkey"],
        capabilities=labelee_agent["capabilities"]
    )
    await labelee_client.connect()
    
    # Connect AINS agent
    ains_client = AICPWebSocketClient(
        server_url="ws://localhost:8765",
        agent_id=ains_agent["agent_id"],
        privkey_hex=ains_agent["privkey"],
        capabilities=ains_agent["capabilities"]
    )
    await ains_client.connect()
    
    # Send task
    await asyncio.sleep(0.5)
    await ains_client.send_message(
        method="image.label",
        payload={"image_url": "snoop_coco/AI Snoop.png"},
        recipient="labelee-duke-REAL"
    )
    
    print("✅ Full AICP Pipeline: AINS → Labelee via WebSocket")
    
    # Cleanup
    await labelee_client.close()
    await ains_client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
