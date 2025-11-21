"""AICP Server for Receiving Messages"""

import socket
import threading
import logging
from typing import Callable, Dict
from .message import Message, MessageType
from .crypto import verify_message

logger = logging.getLogger(__name__)


class AICPServer:
    """AICP Server for handling incoming agent messages"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8001):
        """
        Initialize AICP server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.handlers: Dict[MessageType, Callable] = {}
        self.agent_registry: Dict[str, bytes] = {}  # agent_id -> public_key
    
    def register_agent(self, agent_id: str, public_key: bytes):
        """Register an agent's public key"""
        self.agent_registry[agent_id] = public_key
        logger.info(f"Registered agent {agent_id[:8]}...")
    
    def register_handler(self, message_type: MessageType, handler: Callable):
        """
        Register a handler for a message type.
        
        Args:
            message_type: Type of message to handle
            handler: Callback function (message: Message) -> Message
        """
        self.handlers[message_type] = handler
        logger.info(f"Registered handler for {message_type.name}")
    
    def start(self):
        """Start the server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        
        self.running = True
        logger.info(f"AICP Server listening on {self.host}:{self.port}")
        
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                logger.info(f"Connection from {address}")
                
                # Handle client in a new thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("Server stopped")
    
    def _handle_client(self, client_socket: socket.socket):
        """Handle a client connection"""
        try:
            while True:
                # Receive message length
                length_bytes = client_socket.recv(4)
                if not length_bytes:
                    break
                
                message_length = int.from_bytes(length_bytes, byteorder='big')
                
                # Receive message
                message_bytes = b''
                while len(message_bytes) < message_length:
                    chunk = client_socket.recv(min(4096, message_length - len(message_bytes)))
                    if not chunk:
                        raise ConnectionError("Connection closed")
                    message_bytes += chunk
                
                # Deserialize
                message = Message.deserialize(message_bytes)
                
                # Verify signature
                source_agent_id = message.header.source_agent_id
                if source_agent_id in self.agent_registry:
                    public_key = self.agent_registry[source_agent_id]
                    
                    # Get message bytes without signature/nonce for verification
                    temp_message = Message(header=message.header, body=message.body)
                    message_for_verification = temp_message.serialize()
                    
                    is_valid = verify_message(
                        public_key,
                        message_for_verification,
                        message.signature,
                        message.nonce
                    )
                    
                    if not is_valid:
                        logger.warning(f"Invalid signature from {source_agent_id[:8]}...")
                        continue
                
                # Handle message
                response = self._handle_message(message)
                
                # Send response if any
                if response:
                    response_bytes = response.serialize()
                    response_length = len(response_bytes)
                    client_socket.sendall(response_length.to_bytes(4, byteorder='big'))
                    client_socket.sendall(response_bytes)
                
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            client_socket.close()
    
    def _handle_message(self, message: Message) -> Message:
        """
        Handle an incoming message.
        
        Args:
            message: Received message
        
        Returns:
            Response message
        """
        message_type = message.header.message_type
        
        logger.info(f"Handling {message_type.name} message from {message.header.source_agent_id[:8]}...")
        
        # Get handler for this message type
        handler = self.handlers.get(message_type)
        
        if handler:
            return handler(message)
        else:
            logger.warning(f"No handler for {message_type.name}")
            return None
