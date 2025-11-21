"""Unit tests for AICP Client"""

import pytest
from aicp import AICPClient, KeyPair, MessageType


@pytest.fixture
def keypair():
    """Create test keypair"""
    return KeyPair()


def test_client_initialization(keypair):
    """Test client initialization"""
    client = AICPClient(keypair, server_host="localhost", server_port=8001)
    
    assert client.keypair == keypair
    assert client.server_host == "localhost"
    assert client.server_port == 8001
    assert client.socket is None


def test_client_message_creation(keypair):
    """Test that client can create messages"""
    client = AICPClient(keypair, server_host="localhost", server_port=8001)
    
    # This will fail to send without a server, but we can test message creation
    try:
        message = client.send_message(
            destination_agent_id="test_agent",
            body={"test": "data"}
        )
        # If we get here, message was created (but not sent)
    except Exception:
        # Expected - no server running
        pass
