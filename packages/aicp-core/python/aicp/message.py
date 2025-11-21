"""AICP Message Structure and Serialization"""

import uuid
import time
import msgpack
from enum import IntEnum
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


class MessageType(IntEnum):
    """AICP Message Types"""
    REQUEST = 0x01
    RESPONSE = 0x02
    ACK = 0x03
    ERROR = 0x04
    PING = 0x05
    BROADCAST = 0x06


@dataclass
class MessageHeader:
    """AICP Message Header (96 bytes)"""
    version: int = 0x01
    message_type: MessageType = MessageType.REQUEST
    message_id: str = None
    timestamp: int = None
    source_agent_id: str = None
    destination_agent_id: str = None
    payload_length: int = 0
    flags: int = 0
    ttl: int = 255
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
        if self.timestamp is None:
            self.timestamp = int(time.time() * 1_000_000_000)  # nanoseconds


@dataclass
class Message:
    """AICP Message with Header and Payload"""
    header: MessageHeader
    body: Dict[str, Any]
    signature: Optional[bytes] = None
    nonce: Optional[bytes] = None
    
    def serialize(self) -> bytes:
        """Serialize message to bytes using MessagePack"""
        data = {
            "header": asdict(self.header),
            "body": self.body,
            "signature": self.signature,
            "nonce": self.nonce,
        }
        return msgpack.packb(data, use_bin_type=True)
    
    @classmethod
    def deserialize(cls, data: bytes) -> "Message":
        """Deserialize message from bytes"""
        unpacked = msgpack.unpackb(data, raw=False)
        
        header_dict = unpacked["header"]
        header = MessageHeader(
            version=header_dict["version"],
            message_type=MessageType(header_dict["message_type"]),
            message_id=header_dict["message_id"],
            timestamp=header_dict["timestamp"],
            source_agent_id=header_dict["source_agent_id"],
            destination_agent_id=header_dict["destination_agent_id"],
            payload_length=header_dict["payload_length"],
            flags=header_dict["flags"],
            ttl=header_dict["ttl"],
        )
        
        return cls(
            header=header,
            body=unpacked["body"],
            signature=unpacked.get("signature"),
            nonce=unpacked.get("nonce"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "header": asdict(self.header),
            "body": self.body,
            "signature": self.signature.hex() if self.signature else None,
            "nonce": self.nonce.hex() if self.nonce else None,
        }
