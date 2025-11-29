"""WebSocket Transport Tests"""
import pytest
import asyncio
from aicp.websocket_transport import AICPWebSocketServer, AICPWebSocketClient
from aicp.message import AICPMessage
import nacl.signing
import nacl.encoding

@pytest.mark.asyncio
async def test_server_startup():
    """Test server startup"""
    server = AICPWebSocketServer(host="localhost", port=9999)
    task = asyncio.create_task(server.start())
    await asyncio.sleep(0.5)
    assert server.server is not None
    print("✅ Server startup test passed")

@pytest.mark.asyncio
async def test_client_init():
    """Test client initialization"""
    signing_key = nacl.signing.SigningKey.generate()
    privkey = signing_key.encode(nacl.encoding.HexEncoder).decode()
    
    client = AICPWebSocketClient(
        server_url="ws://localhost:9999",
        agent_id="test-agent",
        privkey_hex=privkey,
        capabilities=["test.method"]
    )
    
    assert client.agent_id == "test-agent"
    assert client.pubkey is not None
    print("✅ Client init test passed")

@pytest.mark.asyncio
async def test_message_creation():
    """Test message creation"""
    msg = AICPMessage(
        method="image.label",
        payload={"url": "test.jpg"},
        sender="test"
    )
    assert msg.method == "image.label"
    print("✅ Message creation test passed")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
