#!/usr/bin/env python3
"""
Simple AICP Client-Server Communication Example
Demonstrates two agents communicating via AICP protocol
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from aicp import AICPClient, AICPServer, KeyPair, MessageType, Message, MessageHeader
import threading
import time


def main():
    print("🚀 DukeNET AICP Communication Demo\n")
    
    # Step 1: Create keypairs
    print("1️⃣  Generating agent keypairs...")
    agent1_keypair = KeyPair()
    agent2_keypair = KeyPair()
    
    print(f"   Agent 1 ID: {agent1_keypair.agent_id[:16]}...")
    print(f"   Agent 2 ID: {agent2_keypair.agent_id[:16]}...\n")
    
    # Step 2: Start server
    print("2️⃣  Starting AICP server...")
    server = AICPServer(host="localhost", port=8003)
    
    server.register_agent(agent1_keypair.agent_id, agent1_keypair.public_key)
    server.register_agent(agent2_keypair.agent_id, agent2_keypair.public_key)
    
    def request_handler(message: Message) -> Message:
        print(f"   📥 Server received: {message.body}")
        response_header = MessageHeader(
            message_type=MessageType.RESPONSE,
            source_agent_id=agent2_keypair.agent_id,
            destination_agent_id=message.header.source_agent_id
        )
        return Message(
            header=response_header,
            body={"status": "success", "message": "Request processed", "echoed": message.body}
        )
    
    server.register_handler(MessageType.REQUEST, request_handler)
    
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    time.sleep(1)
    print("   ✅ Server running on localhost:8003\n")
    
    # Step 3: Create client
    print("3️⃣  Creating AICP client...")
    client = AICPClient(agent1_keypair, server_host="localhost", server_port=8003)
    print("   ✅ Client initialized\n")
    
    # Step 4: Send message
    print("4️⃣  Sending signed message...")
    message_body = {"action": "greeting", "data": "Hello from Agent 1!", "timestamp": time.time()}
    
    sent_message = client.send_message(
        destination_agent_id=agent2_keypair.agent_id,
        body=message_body
    )
    
    print(f"   📤 Sent: {message_body}")
    print(f"   🔐 Signature: {sent_message.signature.hex()[:32]}...\n")
    
    # Step 5: Receive response
    print("5️⃣  Waiting for response...")
    response = client.receive_message()
    
    if response:
        print(f"   📨 Response: {response.body}\n")
    
    # Step 6: PING
    print("6️⃣  Measuring latency...")
    
    def ping_handler(message: Message) -> Message:
        response_header = MessageHeader(
            message_type=MessageType.RESPONSE,
            source_agent_id=agent2_keypair.agent_id,
            destination_agent_id=message.header.source_agent_id
        )
        return Message(header=response_header, body={"pong": True})
    
    server.register_handler(MessageType.PING, ping_handler)
    
    rtt = client.ping(agent2_keypair.agent_id)
    print(f"   ⚡ Round-trip time: {rtt:.2f}ms\n")
    
    # Clean up
    print("7️⃣  Cleaning up...")
    client.disconnect()
    server.stop()
    print("   ✅ Done\n")
    
    print("🎉 Demo complete!")
    print(f"   - Agents authenticated via Ed25519")
    print(f"   - Messages signed and verified")
    print(f"   - Latency: {rtt:.2f}ms")


if __name__ == "__main__":
    main()
