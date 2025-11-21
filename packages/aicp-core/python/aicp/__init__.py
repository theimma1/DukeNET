"""AICP: AI Communication Protocol - Python Implementation"""

from .message import Message, MessageType, MessageHeader
from .crypto import KeyPair, sign_message, verify_message
from .client import AICPClient
from .server import AICPServer

__version__ = "0.1.0"

__all__ = [
    "Message",
    "MessageType", 
    "MessageHeader",
    "KeyPair",
    "sign_message",
    "verify_message",
    "AICPClient",
    "AICPServer",
]
