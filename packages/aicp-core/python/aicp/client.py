"""AICP Client for Sending Messages"""

import socket
import logging
from typing import Optional, Dict, Any
from .message import Message, MessageHeader, MessageType
from .crypto import KeyPair, sign_message

logger = logging.getLogger(__name__)


class AICPClient:
    """AICP Client for agent-to-agent communication"""
    
    def __init__(self, keypair: KeyPair, server_host: str = "localhost", server_port: int = 8001):
        """
        Initialize AICP client.
        
        Args:
            keypair: Agent's key pair for signing messages
            server_host: Server hostname
            server_port: Server port
        """
        self.keypair = keypair
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
    
    def connect(self):
        """Establish connection to AICP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.server_host, self.server_port))
        logger.info(f"Connected to {self.server_host}:{self.server_port}")
    
    def disconnect(self):
        """Close connection"""
        if self.socket:
            self.socket.close()
            self.socket = None
            logger.info("Disconnected from server")
    
    def send_message(
        self,
        destination_agent_id: str,
        body: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST
    ) -> Message:
        """
        Send a message to another agent.
        
        Args:
            destination_agent_id: Target agent's ID
            body: Message payload
            message_type: Type of message
        
        Returns:
            Signed message that was sent
        """
        # Create message
        header = MessageHeader(
            message_type=message_type,
            source_agent_id=self.keypair.agent_id,
            destination_agent_id=destination_agent_id,
            payload_length=len(str(body))
        )
        
        message = Message(header=header, body=body)
        
        # Serialize message
        message_bytes = message.serialize()
        
        # Sign message
        signature, nonce = sign_message(
            self.keypair.private_key,
            message_bytes
        )
        
        message.signature = signature
        message.nonce = nonce
        
        # Send message
        if not self.socket:
            self.connect()
        
        # Send message length first (4 bytes, big-endian)
        signed_message_bytes = message.serialize()
        message_length = len(signed_message_bytes)
        self.socket.sendall(message_length.to_bytes(4, byteorder='big'))
        
        # Send message
        self.socket.sendall(signed_message_bytes)
        
        logger.info(f"Sent {message_type.name} message to {destination_agent_id[:8]}...")
        
        return message
    
    def receive_message(self) -> Optional[Message]:
        """
        Receive a message from the server.
        
        Returns:
            Received message or None if connection closed
        """
        if not self.socket:
            raise RuntimeError("Not connected to server")
        
        # Receive message length
        length_bytes = self.socket.recv(4)
        if not length_bytes:
            return None
        
        message_length = int.from_bytes(length_bytes, byteorder='big')
        
        # Receive message
        message_bytes = b''
        while len(message_bytes) < message_length:
            chunk = self.socket.recv(min(4096, message_length - len(message_bytes)))
            if not chunk:
                raise ConnectionError("Connection closed unexpectedly")
            message_bytes += chunk
        
        # Deserialize
        message = Message.deserialize(message_bytes)
        
        logger.info(f"Received {message.header.message_type.name} message")
        
        return message
    
    def ping(self, destination_agent_id: str) -> float:
        """
        Send a PING message and measure round-trip time.
        
        Args:
            destination_agent_id: Target agent ID
        
        Returns:
            Round-trip time in milliseconds
        """
        import time
        
        start_time = time.time()
        
        self.send_message(
            destination_agent_id=destination_agent_id,
            body={"type": "ping"},
            message_type=MessageType.PING
        )
        
        response = self.receive_message()
        
        end_time = time.time()
        rtt_ms = (end_time - start_time) * 1000
        
        logger.info(f"Ping RTT: {rtt_ms:.2f}ms")
        
        return rtt_ms
