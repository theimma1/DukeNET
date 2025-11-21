"""AICP Cryptographic Operations - Ed25519 Signing and Verification"""

import hashlib
import secrets
from typing import Tuple, Optional
from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder
from nacl.exceptions import BadSignatureError


class KeyPair:
    """Ed25519 Key Pair for Agent Identity"""
    
    def __init__(self, private_key: Optional[bytes] = None):
        """
        Initialize key pair.
        
        Args:
            private_key: Optional 32-byte private key. If None, generates new keypair.
        """
        if private_key:
            self.signing_key = SigningKey(private_key)
        else:
            self.signing_key = SigningKey.generate()
        
        self.verify_key = self.signing_key.verify_key
        self.agent_id = self._compute_agent_id()
    
    def _compute_agent_id(self) -> str:
        """Compute agent ID as SHA256(public_key)"""
        public_key_bytes = bytes(self.verify_key)
        return hashlib.sha256(public_key_bytes).hexdigest()
    
    @property
    def private_key(self) -> bytes:
        """Get private key bytes"""
        return bytes(self.signing_key)
    
    @property
    def public_key(self) -> bytes:
        """Get public key bytes"""
        return bytes(self.verify_key)
    
    @property
    def public_key_b64(self) -> str:
        """Get base64-encoded public key"""
        return self.verify_key.encode(encoder=Base64Encoder).decode('utf-8')
    
    def to_dict(self) -> dict:
        """Export key pair to dictionary"""
        return {
            "agent_id": self.agent_id,
            "public_key": self.public_key_b64,
            "private_key": Base64Encoder.encode(self.private_key).decode('utf-8')
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "KeyPair":
        """Import key pair from dictionary"""
        private_key = Base64Encoder.decode(data["private_key"])
        return cls(private_key=private_key)


def sign_message(private_key: bytes, message_bytes: bytes, nonce: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Sign an AICP message.
    
    Args:
        private_key: Ed25519 private key (32 bytes)
        message_bytes: Serialized message to sign
        nonce: Optional nonce (16 bytes). If None, generates random nonce.
    
    Returns:
        Tuple of (signature, nonce)
    """
    if nonce is None:
        nonce = secrets.token_bytes(16)
    
    # Hash the message + nonce
    payload = message_bytes + nonce
    message_hash = hashlib.sha256(payload).digest()
    
    # Sign the hash
    signing_key = SigningKey(private_key)
    signature = signing_key.sign(message_hash).signature
    
    return signature, nonce


def verify_message(public_key: bytes, message_bytes: bytes, signature: bytes, nonce: bytes) -> bool:
    """
    Verify an AICP message signature.
    
    Args:
        public_key: Ed25519 public key (32 bytes)
        message_bytes: Serialized message
        signature: Message signature (64 bytes)
        nonce: Nonce used in signing (16 bytes)
    
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Reconstruct the hash
        payload = message_bytes + nonce
        message_hash = hashlib.sha256(payload).digest()
        
        # Verify signature
        verify_key = VerifyKey(public_key)
        verify_key.verify(message_hash, signature)
        
        return True
    except BadSignatureError:
        return False


def generate_nonce() -> bytes:
    """Generate a cryptographically secure 16-byte nonce"""
    return secrets.token_bytes(16)
