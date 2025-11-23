"""Authentication and authorization module"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from .db import APIKey, RateLimitTracker, AuditLog, get_db


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
    
    Returns:
        tuple: (key_id, api_key) - key_id for storage, api_key for client
    """
    key_id = f"key_{secrets.token_hex(16)}"
    api_key = f"ains_{secrets.token_urlsafe(32)}"
    return key_id, api_key


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_api_key(db: Session, api_key: str) -> Optional[APIKey]:
    """
    Verify an API key and return the associated APIKey record.
    
    Args:
        db: Database session
        api_key: The API key to verify
    
    Returns:
        APIKey object if valid, None otherwise
    """
    if not api_key or not api_key.startswith("ains_"):
        return None
    
    key_hash = hash_api_key(api_key)
    
    # Find active key with matching hash
    api_key_record = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.active == True
    ).first()
    
    if not api_key_record:
        return None
    
    # Check expiration (handle both timezone-aware and naive datetimes)
    if api_key_record.expires_at:
        now = datetime.now(timezone.utc)
        expires_at = api_key_record.expires_at
        
        # If expires_at is naive, make it aware (assume UTC)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < now:
            return None
    
    # Update last used timestamp
    api_key_record.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    return api_key_record


def check_rate_limit(db: Session, key_id: str, rate_limit_per_minute: int, rate_limit_per_hour: int) -> bool:
    """
    Check if the API key has exceeded rate limits.
    
    Args:
        db: Database session
        key_id: API key ID
        rate_limit_per_minute: Max requests per minute
        rate_limit_per_hour: Max requests per hour
    
    Returns:
        True if within limits, False if exceeded
    """
    now = datetime.now(timezone.utc)
    
    # Check minute window
    minute_start = now.replace(second=0, microsecond=0)
    minute_tracker = db.query(RateLimitTracker).filter(
        RateLimitTracker.key_id == key_id,
        RateLimitTracker.window_start == minute_start,
        RateLimitTracker.window_type == 'minute'
    ).first()
    
    if minute_tracker:
        if minute_tracker.request_count >= rate_limit_per_minute:
            return False
        minute_tracker.request_count += 1
    else:
        minute_tracker = RateLimitTracker(
            key_id=key_id,
            window_start=minute_start,
            window_type='minute',
            request_count=1
        )
        db.add(minute_tracker)
    
    # Check hour window
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    hour_tracker = db.query(RateLimitTracker).filter(
        RateLimitTracker.key_id == key_id,
        RateLimitTracker.window_start == hour_start,
        RateLimitTracker.window_type == 'hour'
    ).first()
    
    if hour_tracker:
        if hour_tracker.request_count >= rate_limit_per_hour:
            return False
        hour_tracker.request_count += 1
    else:
        hour_tracker = RateLimitTracker(
            key_id=key_id,
            window_start=hour_start,
            window_type='hour',
            request_count=1
        )
        db.add(hour_tracker)
    
    db.commit()
    return True


def log_security_event(
    db: Session,
    event_type: str,
    action: str,
    success: bool,
    client_id: Optional[str] = None,
    key_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    error_message: Optional[str] = None,
    extra_metadata: Optional[dict] = None
):
    """Log a security event to the audit log"""
    audit_entry = AuditLog(
        event_type=event_type,
        client_id=client_id,
        key_id=key_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        success=success,
        error_message=error_message,
        extra_metadata=extra_metadata or {}
    )
    db.add(audit_entry)
    db.commit()


# FastAPI dependency for authentication
async def require_api_key(
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    FastAPI dependency to require valid API key authentication.
    
    Usage:
        @app.get("/protected")
        def protected_route(api_key: APIKey = Depends(require_api_key)):
            ...
    """
    if not x_api_key:
        log_security_event(
            db, "auth_failed", "missing_api_key", False,
            error_message="No API key provided"
        )
        raise HTTPException(status_code=401, detail="API key required")
    
    api_key_record = verify_api_key(db, x_api_key)
    
    if not api_key_record:
        log_security_event(
            db, "auth_failed", "invalid_api_key", False,
            error_message="Invalid API key"
        )
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Check rate limits
    if not check_rate_limit(
        db,
        api_key_record.key_id,
        api_key_record.rate_limit_per_minute,
        api_key_record.rate_limit_per_hour
    ):
        log_security_event(
            db, "rate_limit_exceeded", "request_blocked", False,
            client_id=api_key_record.client_id,
            key_id=api_key_record.key_id
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Log successful authentication
    log_security_event(
        db, "auth_success", "api_key_verified", True,
        client_id=api_key_record.client_id,
        key_id=api_key_record.key_id
    )
    
    return api_key_record
