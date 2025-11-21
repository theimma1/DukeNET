"""Tests for AICP Message Structure"""

import pytest
from aicp.message import Message, MessageHeader, MessageType


def test_message_header_creation():
    """Test message header creation with defaults"""
    header = MessageHeader(
        source_agent_id="agent_123",
        destination_agent_id="agent_456"
    )
    
    assert header.version == 0x01
    assert header.message_type == MessageType.REQUEST
    assert header.source_agent_id == "agent_123"
    assert header.destination_agent_id == "agent_456"
    assert header.message_id is not None
    assert header.timestamp > 0


def test_message_serialization():
    """Test message serialization and deserialization"""
    header = MessageHeader(
        source_agent_id="agent_123",
        destination_agent_id="agent_456"
    )
    
    body = {"action": "test", "data": [1, 2, 3]}
    
    message = Message(header=header, body=body)
    
    # Serialize
    serialized = message.serialize()
    assert isinstance(serialized, bytes)
    assert len(serialized) > 0
    
    # Deserialize
    deserialized = Message.deserialize(serialized)
    
    assert deserialized.header.source_agent_id == "agent_123"
    assert deserialized.header.destination_agent_id == "agent_456"
    assert deserialized.body == body


def test_message_types():
    """Test all message types"""
    types = [
        MessageType.REQUEST,
        MessageType.RESPONSE,
        MessageType.ACK,
        MessageType.ERROR,
        MessageType.PING,
        MessageType.BROADCAST
    ]
    
    for msg_type in types:
        header = MessageHeader(
            message_type=msg_type,
            source_agent_id="test",
            destination_agent_id="test"
        )
        assert header.message_type == msg_type
