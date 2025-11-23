"""Tests for Sprint 6: Security & Authorization"""
import pytest
import secrets
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ains.api import app
from ains.db import Base, get_db, APIKey, AuditLog, RateLimitTracker
from ains.auth import generate_api_key, hash_api_key, verify_api_key, check_rate_limit


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_security.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_database():
    """Clear database before each test"""
    db = TestingSessionLocal()
    try:
        # Delete in order (foreign keys first)
        db.query(RateLimitTracker).delete()
        db.query(AuditLog).delete()
        db.query(APIKey).delete()
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error clearing database: {e}")
    finally:
        db.close()
    yield



def test_generate_api_key():
    """Test API key generation"""
    key_id, api_key = generate_api_key()
    
    assert key_id.startswith("key_")
    assert len(key_id) == 36  # Change from 37 to 36
    assert api_key.startswith("ains_")
    assert len(api_key) > 40



def test_hash_api_key():
    """Test API key hashing"""
    api_key = "ains_test123456789"
    key_hash = hash_api_key(api_key)
    
    assert len(key_hash) == 64  # SHA-256 hex digest
    assert key_hash == hash_api_key(api_key)  # Consistent


def test_create_api_key():
    """Test creating a new API key"""
    response = client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Test Key",
        "description": "Testing API key creation",
        "scopes": ["task:read", "task:write"],
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000,
        "expires_in_days": 30
    })
    
    assert response.status_code == 200
    data = response.json()
    
    assert "key_id" in data
    assert "api_key" in data
    assert data["api_key"].startswith("ains_")
    assert data["client_id"] == "test_client"
    assert data["name"] == "Test Key"
    assert data["scopes"] == ["task:read", "task:write"]
    assert "warning" in data


def test_list_api_keys():
    """Test listing API keys"""
    # Create test keys
    for i in range(3):
        client.post("/ains/api-keys", json={
            "client_id": f"client_{i}",
            "name": f"Key {i}",
            "rate_limit_per_minute": 60,
            "rate_limit_per_hour": 1000
        })
    
    # List all keys
    response = client.get("/ains/api-keys")
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) == 3
    
    # Filter by client
    response = client.get("/ains/api-keys?client_id=client_0")
    assert response.status_code == 200
    keys = response.json()
    assert len(keys) == 1
    assert keys[0]["client_id"] == "client_0"


def test_get_api_key():
    """Test getting specific API key details"""
    # Create key
    create_response = client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Test Key",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000
    })
    key_id = create_response.json()["key_id"]
    
    # Get key details
    response = client.get(f"/ains/api-keys/{key_id}")
    assert response.status_code == 200
    data = response.json()
    
    assert data["key_id"] == key_id
    assert data["client_id"] == "test_client"
    assert data["name"] == "Test Key"


def test_update_api_key():
    """Test updating API key settings"""
    # Create key
    create_response = client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Original Name",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000
    })
    key_id = create_response.json()["key_id"]
    
    # Update key
    response = client.patch(f"/ains/api-keys/{key_id}", json={
        "name": "Updated Name",
        "rate_limit_per_minute": 120
    })
    assert response.status_code == 200
    
    # Verify update
    get_response = client.get(f"/ains/api-keys/{key_id}")
    data = get_response.json()
    assert data["name"] == "Updated Name"
    assert data["rate_limit_per_minute"] == 120


def test_revoke_api_key():
    """Test revoking an API key"""
    # Create key
    create_response = client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Test Key",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000
    })
    key_id = create_response.json()["key_id"]
    
    # Revoke key
    response = client.delete(f"/ains/api-keys/{key_id}")
    assert response.status_code == 200
    
    # Verify revoked
    get_response = client.get(f"/ains/api-keys/{key_id}")
    data = get_response.json()
    assert data["active"] is False


def test_verify_valid_api_key():
    """Test verifying a valid API key"""
    db = TestingSessionLocal()
    
    # Create API key
    key_id, api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    api_key_record = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        client_id="test_client",
        name="Test Key",
        rate_limit_per_minute=60,
        rate_limit_per_hour=1000
    )
    db.add(api_key_record)
    db.commit()
    
    # Verify key
    verified = verify_api_key(db, api_key)
    assert verified is not None
    assert verified.key_id == key_id
    assert verified.client_id == "test_client"
    
    db.close()


def test_verify_invalid_api_key():
    """Test verifying an invalid API key"""
    db = TestingSessionLocal()
    
    # Try to verify non-existent key
    verified = verify_api_key(db, "ains_invalid_key")
    assert verified is None
    
    db.close()


def test_rate_limiting():
    """Test rate limiting functionality"""
    db = TestingSessionLocal()
    
    # Create API key with low limits
    key_id, api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    api_key_record = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        client_id="test_client",
        name="Test Key",
        rate_limit_per_minute=5,  # Very low for testing
        rate_limit_per_hour=100
    )
    db.add(api_key_record)
    db.commit()
    
    # Make requests within limit
    for i in range(5):
        within_limit = check_rate_limit(db, key_id, 5, 100)
        assert within_limit is True
    
    # Next request should exceed limit
    exceeded = check_rate_limit(db, key_id, 5, 100)
    assert exceeded is False
    
    db.close()


def test_protected_endpoint_without_key():
    """Test accessing protected endpoint without API key"""
    response = client.get("/ains/protected/test")
    assert response.status_code == 401
    assert "API key required" in response.json()["detail"]


def test_protected_endpoint_with_valid_key():
    """Test accessing protected endpoint with valid API key"""
    # Create API key
    create_response = client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Test Key",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000
    })
    api_key = create_response.json()["api_key"]
    
    # Access protected endpoint
    response = client.get(
        "/ains/protected/test",
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Authentication successful!"
    assert data["client_id"] == "test_client"


def test_protected_endpoint_with_invalid_key():
    """Test accessing protected endpoint with invalid API key"""
    response = client.get(
        "/ains/protected/test",
        headers={"X-API-Key": "ains_invalid_key"}
    )
    
    assert response.status_code == 401
    assert "Invalid API key" in response.json()["detail"]


def test_audit_logging():
    """Test security audit logging"""
    # Create API key (should log event)
    client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Test Key",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000
    })
    
    # Get audit logs
    response = client.get("/ains/audit-logs")
    assert response.status_code == 200
    logs = response.json()
    
    assert len(logs) > 0
    assert any(log["event_type"] == "api_key_created" for log in logs)
    # Check for extra_metadata instead of metadata
    assert all("extra_metadata" in log for log in logs)


def test_api_key_expiration():
    """Test expired API key rejection"""
    db = TestingSessionLocal()
    
    # Create expired API key
    key_id, api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    api_key_record = APIKey(
        key_id=key_id,
        key_hash=key_hash,
        client_id="test_client",
        name="Expired Key",
        rate_limit_per_minute=60,
        rate_limit_per_hour=1000,
        expires_at=datetime.now(timezone.utc) - timedelta(days=1)  # Add timezone.utc
    )
    db.add(api_key_record)
    db.commit()
    
    # Try to verify expired key
    verified = verify_api_key(db, api_key)
    assert verified is None
    
    db.close()



def test_api_key_usage_tracking():
    """Test API key usage statistics"""
    # Create API key
    create_response = client.post("/ains/api-keys", json={
        "client_id": "test_client",
        "name": "Test Key",
        "rate_limit_per_minute": 60,
        "rate_limit_per_hour": 1000
    })
    key_id = create_response.json()["key_id"]
    api_key = create_response.json()["api_key"]
    
    # Make some requests
    for _ in range(5):
        client.get(
            "/ains/protected/test",
            headers={"X-API-Key": api_key}
        )
    
    # Check usage
    response = client.get(f"/ains/api-keys/{key_id}/usage?hours=1")
    assert response.status_code == 200
    data = response.json()
    
    assert data["key_id"] == key_id
    assert data["total_requests"] >= 5
