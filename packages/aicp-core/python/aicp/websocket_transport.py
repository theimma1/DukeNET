"""
WebSocket Transport Layer for AICP
Enables real-time bidirectional agent-to-agent communication
Production-ready implementation
"""

import asyncio
import json
import logging
from typing import Dict, Callable, Optional, Set
from dataclasses import asdict
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.client import WebSocketClientProtocol
import nacl.signing
import nacl.encoding

from .message import AICPMessage

logger = logging.getLogger(__name__)


class AICPWebSocketServer:
    """Production WebSocket server for AICP agents"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, WebSocketServerProtocol] = {}
        self.agent_registry: Dict[str, Dict] = {}  # {agent_id: {pubkey, capabilities, ws}}
        self.message_handlers: Dict[str, Callable] = {}
        self.server = None
        
    async def register_handler(self, method: str, handler: Callable):
        """Register message handler for specific capability method"""
        self.message_handlers[method] = handler
        logger.info(f"Handler registered for method: {method}")
        
    async def register_agent(self, agent_id: str, pubkey: str, capabilities: list, ws: WebSocketServerProtocol):
        """Register agent with pubkey and capabilities"""
        self.agent_registry[agent_id] = {
            "pubkey": pubkey,
            "capabilities": capabilities,
            "ws": ws,
            "last_heartbeat": asyncio.get_event_loop().time()
        }
        self.clients[agent_id] = ws
        logger.info(f"✅ Agent registered: {agent_id} with capabilities {capabilities}")
        
    async def unregister_agent(self, agent_id: str):
        """Unregister agent on disconnect"""
        if agent_id in self.agent_registry:
            del self.agent_registry[agent_id]
            del self.clients[agent_id]
            logger.info(f"❌ Agent unregistered: {agent_id}")
            
    async def route_message(self, msg: AICPMessage):
        """Route AICP message to appropriate agent"""
        method = msg.method
        
        # Find agents with matching capability
        matching_agents = [
            agent_id for agent_id, info in self.agent_registry.items()
            if method in info["capabilities"]
        ]
        
        if not matching_agents:
            logger.warning(f"No agent found for method: {method}")
            return None
            
        # Route to first available agent (round-robin in production)
        target_agent = matching_agents[0]
        target_ws = self.agent_registry[target_agent]["ws"]
        
        logger.info(f"📤 Routing {method} to {target_agent}")
        
        try:
            # Send message as JSON
            await target_ws.send(msg.to_json())
            return target_agent
        except Exception as e:
            logger.error(f"Failed to route message: {e}")
            return None
            
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Handle incoming WebSocket connections"""
        agent_id = None
        
        try:
            # First message should be registration
            msg_data = await websocket.recv()
            msg = AICPMessage.from_json(msg_data)
            
            if msg.method != "agent.register":
                logger.warning("First message must be agent.register")
                await websocket.close()
                return
                
            # Extract agent info
            agent_id = msg.payload.get("agent_id")
            pubkey = msg.payload.get("pubkey")
            capabilities = msg.payload.get("capabilities", [])
            
            # Register agent
            await self.register_agent(agent_id, pubkey, capabilities, websocket)
            
            # Send registration confirmation
            response = AICPMessage(
                method="agent.register.ack",
                payload={"status": "registered", "agent_id": agent_id},
                sender="aicp-server"
            )
            await websocket.send(response.to_json())
            
            # Main message loop
            async for msg_data in websocket:
                try:
                    msg = AICPMessage.from_json(msg_data)
                    
                    # Handle heartbeat
                    if msg.method == "heartbeat":
                        self.agent_registry[agent_id]["last_heartbeat"] = asyncio.get_event_loop().time()
                        logger.debug(f"💓 Heartbeat from {agent_id}")
                        continue
                    
                    # Route task to appropriate agent
                    if msg.method in self.message_handlers:
                        handler = self.message_handlers[msg.method]
                        result = await handler(msg)
                        
                        # Send result back
                        response = AICPMessage(
                            method=f"{msg.method}.result",
                            payload=result,
                            sender="aicp-server"
                        )
                        await websocket.send(response.to_json())
                    else:
                        # Route to agent with capability
                        await self.route_message(msg)
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for agent: {agent_id}")
        finally:
            if agent_id:
                await self.unregister_agent(agent_id)
                
    async def start(self):
        """Start WebSocket server"""
        self.server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"🚀 AICP WebSocket Server listening on ws://{self.host}:{self.port}")
        return self.server


class AICPWebSocketClient:
    """WebSocket client for agents to connect to AICP server"""
    
    def __init__(self, server_url: str, agent_id: str, privkey_hex: str, capabilities: list):
        self.server_url = server_url
        self.agent_id = agent_id
        self.privkey_hex = privkey_hex
        self.capabilities = capabilities
        self.ws: Optional[WebSocketClientProtocol] = None
        self.message_handlers: Dict[str, Callable] = {}
        
        # Derive pubkey from private key
        signing_key = nacl.signing.SigningKey(privkey_hex, encoder=nacl.encoding.HexEncoder)
        self.pubkey = signing_key.verify_key.encode(nacl.encoding.HexEncoder).decode()
        
    async def connect(self):
        """Connect to AICP server"""
        try:
            self.ws = await websockets.connect(self.server_url)
            
            # Send registration message
            reg_msg = AICPMessage(
                method="agent.register",
                payload={
                    "agent_id": self.agent_id,
                    "pubkey": self.pubkey,
                    "capabilities": self.capabilities
                },
                sender=self.agent_id
            )
            reg_msg.sign(self.privkey_hex)
            await self.ws.send(reg_msg.to_json())
            
            # Wait for registration confirmation
            response_data = await self.ws.recv()
            response = AICPMessage.from_json(response_data)
            
            if response.method == "agent.register.ack":
                logger.info(f"✅ {self.agent_id} connected to AICP server")
                return True
            else:
                logger.error(f"Registration failed: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
            
    async def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        if not self.ws:
            return
            
        try:
            msg = AICPMessage(
                method="heartbeat",
                sender=self.agent_id
            )
            await self.ws.send(msg.to_json())
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            
    async def heartbeat_loop(self, interval: int = 30):
        """Continuous heartbeat loop"""
        while True:
            await asyncio.sleep(interval)
            await self.send_heartbeat()
            
    async def register_handler(self, method: str, handler: Callable):
        """Register handler for incoming messages"""
        self.message_handlers[method] = handler
        
    async def listen(self):
        """Listen for incoming messages from server"""
        if not self.ws:
            logger.error("Not connected to server")
            return
            
        try:
            async for msg_data in self.ws:
                try:
                    msg = AICPMessage.from_json(msg_data)
                    
                    # Check signature
                    if not msg.verify(self.pubkey):
                        logger.warning(f"Invalid signature from {msg.sender}")
                        continue
                    
                    # Call handler if registered
                    if msg.method in self.message_handlers:
                        handler = self.message_handlers[msg.method]
                        await handler(msg)
                    else:
                        logger.debug(f"No handler for method: {msg.method}")
                        
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for {self.agent_id}")
            
    async def send_message(self, method: str, payload: dict, recipient: str = "*"):
        """Send AICP message to server"""
        if not self.ws:
            logger.error("Not connected")
            return
            
        msg = AICPMessage(
            method=method,
            payload=payload,
            sender=self.agent_id,
            recipient=recipient
        )
        msg.sign(self.privkey_hex)
        
        try:
            await self.ws.send(msg.to_json())
            logger.info(f"📤 Sent {method} to {recipient}")
        except Exception as e:
            logger.error(f"Send failed: {e}")
            
    async def close(self):
        """Close connection"""
        if self.ws:
            await self.ws.close()
            logger.info(f"❌ {self.agent_id} disconnected")
