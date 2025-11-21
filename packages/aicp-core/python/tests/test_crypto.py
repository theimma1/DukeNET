"""Tests for AICP Cryptographic Operations"""

import pytest
from aicp.crypto import KeyPair, sign_message, verify_message, generate_nonce


def test_keypair_generation():
    """Test key pair generation"""
    keypair = KeyPair()
    
    assert len(keypair.private_key) == 32
    assert len(keypair.public_key) == 32
    assert len(keypair.agent_id) == 64  # SHA256 hex


def test_keypair_serialization():
    """Test key pair export/import"""
    keypair1 = KeyPair()
    
    # Export
    data = keypair1.to_dict()
    
    # Import
    keypair2 = KeyPair.from_dict(data)
    
    assert keypair1.agent_id == keypair2.agent_id
    assert keypair1.public_key == keypair2.public_key
    assert keypair1.private_key == keypair2.private_key


def test_message_signing():
    """Test message signing and verification"""
    keypair = KeyPair()
    message = b"Hello, DukeNET!"
    
    # Sign
    signature, nonce = sign_message(keypair.private_key, message)
    
    assert len(signature) == 64
    assert len(nonce) == 16
    
    # Verify
    is_valid = verify_message(keypair.public_key, message, signature, nonce)
    assert is_valid


def test_invalid_signature():
    """Test rejection of invalid signature"""
    keypair1 = KeyPair()
    keypair2 = KeyPair()
    
    message = b"Test message"
    signature, nonce = sign_message(keypair1.private_key, message)
    
    # Try to verify with wrong public key
    is_valid = verify_message(keypair2.public_key, message, signature, nonce)
    assert not is_valid


def test_nonce_generation():
    """Test nonce generation"""
    nonce1 = generate_nonce()
    nonce2 = generate_nonce()
    
    assert len(nonce1) == 16
    assert len(nonce2) == 16
    assert nonce1 != nonce2  # Should be random
