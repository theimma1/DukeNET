"""Integration tests for AICP Client and Server"""

import pytest
import threading
import time
from aicp import AICPClient, AICPServer, KeyPair, MessageType, Message, MessageHeader


@pytest.fixture
def server_keypair():
    """Create server keypair"""
    return KeyPair()


@pytest.fixture
def client_keypair():
    """Create client keypair"""
    return KeyPair()


@pytest.fixture
def server(server_keypair, client_keypair):
    """Start AICP server in background thread"""
    srv = AICPServer(host="localhost", port=8002)
    
    # Register both agents
    srv.register_agent(server_keypair.agent_id, server_keypair.public_key)
    srv.register_agent(client_keypair.agent_id, client_keypair.public_key)
    
    # Register handler for REQUEST messages
    def request_handler(message: Message) -> Message:
        response_header = MessageHeader(
            message_type=MessageType.RESPONSE,
            source_agent_id=server_keypair.agent_id,
            destination_agent_id=message.header.source_agent_id
        )
        return Message(
            header=response_header,
            body={"status": "success", "echo": message.body}
        )
    
    srv.register_handler(MessageType.REQUEST, request_handler)
    
    # Start server in thread
    server_thread = threading.Thread(target=srv.start)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(0.5)  # Let server start
    
    yield srv
    
    srv.stop()


def test_client_server_communication(server, client_keypair, server_keypair):
    """Test basic client-server communication"""
    client = AICPClient(client_keypair, server_host="localhost", server_port=8002)
    
    # Send message
    sent_message = client.send_message(
        destination_agent_id=server_keypair.agent_id,
        body={"action": "test", "data": "hello"}
    )
    
    assert sent_message.header.message_type == MessageType.REQUEST
    assert sent_message.signature is not None
    assert sent_message.nonce is not None
    
    # Receive response
    response = client.receive_message()
    
    assert response is not None
    assert response.header.message_type == MessageType.RESPONSE
    assert response.body["status"] == "success"
    assert response.body["echo"]["action"] == "test"
    
    client.disconnect()


def test_client_ping(server, client_keypair, server_keypair):
    """Test PING functionality"""
    # Register PING handler
    def ping_handler(message: Message) -> Message:
        response_header = MessageHeader(
            message_type=MessageType.RESPONSE,
            source_agent_id=server_keypair.agent_id,
            destination_agent_id=message.header.source_agent_id
        )
        return Message(header=response_header, body={"pong": True})
    
    server.register_handler(MessageType.PING, ping_handler)
    
    client = AICPClient(client_keypair, server_host="localhost", server_port=8002)
    
    # Ping server
    rtt = client.ping(server_keypair.agent_id)
    
    assert rtt > 0
    assert rtt < 1000  # Should be under 1 second
    
    client.disconnect()


def test_multiple_messages(server, client_keypair, server_keypair):
    """Test sending multiple messages"""
    client = AICPClient(client_keypair, server_host="localhost", server_port=8002)
    
    # Send 5 messages
    for i in range(5):
        client.send_message(
            destination_agent_id=server_keypair.agent_id,
            body={"message_number": i}
        )
        
        response = client.receive_message()
        assert response.body["echo"]["message_number"] == i
    
    client.disconnect()
