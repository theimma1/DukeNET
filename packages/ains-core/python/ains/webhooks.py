"""Webhook event notifications"""
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid
import json
import hmac
import hashlib
import httpx
from sqlalchemy.orm import Session

from .db import Webhook, WebhookDelivery, Task


# Event types
EVENT_TASK_CREATED = "task.created"
EVENT_TASK_ASSIGNED = "task.assigned"
EVENT_TASK_STARTED = "task.started"
EVENT_TASK_COMPLETED = "task.completed"
EVENT_TASK_FAILED = "task.failed"
EVENT_TASK_CANCELLED = "task.cancelled"


def register_webhook(
    db: Session,
    agent_id: str,
    url: str,
    events: List[str],
    secret: str = None
) -> Webhook:
    """
    Register a webhook for an agent.
    
    Args:
        db: Database session
        agent_id: Agent ID
        url: Webhook URL to call
        events: List of event types to subscribe to
        secret: Optional secret for HMAC signing
    
    Returns:
        Created webhook
    """
    webhook_id = f"webhook_{uuid.uuid4().hex[:16]}"
    
    webhook = Webhook(
        webhook_id=webhook_id,
        agent_id=agent_id,
        url=url,
        events=json.dumps(events),
        secret=secret,
        active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return webhook


def trigger_webhook_event(
    db: Session,
    event_type: str,
    task: Task
) -> int:
    """
    Trigger webhook event for a task.
    
    Finds all active webhooks subscribed to this event type
    and creates delivery records.
    
    Args:
        db: Database session
        event_type: Type of event (e.g., "task.completed")
        task: Task that triggered the event
    
    Returns:
        Number of webhooks triggered
    """
    # Find webhooks for this agent and event type
    webhooks = db.query(Webhook).filter(
        Webhook.agent_id == task.client_id,
        Webhook.active == True
    ).all()
    
    triggered = 0
    
    for webhook in webhooks:
        # Check if webhook is subscribed to this event
        subscribed_events = json.loads(webhook.events)
        if event_type not in subscribed_events:
            continue
        
        # Create payload
        payload = {
            "event": event_type,
            "task_id": task.task_id,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result_data": task.result_data,
            "error_message": task.error_message
        }
        
        # Create delivery record
        delivery_id = f"delivery_{uuid.uuid4().hex[:16]}"
        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            webhook_id=webhook.webhook_id,
            event_type=event_type,
            payload=json.dumps(payload),
            status="pending",
            attempt_count=0,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(delivery)
        triggered += 1
    
    if triggered > 0:
        db.commit()
    
    return triggered


async def deliver_webhook(db: Session, delivery: WebhookDelivery) -> bool:
    """
    Deliver a webhook notification.
    
    Args:
        db: Database session
        delivery: Webhook delivery record
    
    Returns:
        bool: True if delivered successfully
    """
    webhook = db.query(Webhook).filter(
        Webhook.webhook_id == delivery.webhook_id
    ).first()
    
    if not webhook or not webhook.active:
        delivery.status = "failed"
        delivery.response_body = "Webhook not found or inactive"
        db.commit()
        return False
    
    # Prepare payload
    payload = json.loads(delivery.payload)
    
    # Add signature if secret is configured
    headers = {"Content-Type": "application/json"}
    if webhook.secret:
        signature = hmac.new(
            webhook.secret.encode(),
            delivery.payload.encode(),
            hashlib.sha256
        ).hexdigest()
        headers["X-Webhook-Signature"] = f"sha256={signature}"
    
    # Deliver webhook
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers
            )
        
        delivery.attempt_count += 1
        delivery.response_code = response.status_code
        delivery.response_body = response.text[:1000]  # Truncate
        
        if 200 <= response.status_code < 300:
            delivery.status = "success"
            delivery.delivered_at = datetime.now(timezone.utc)
            db.commit()
            return True
        else:
            delivery.status = "failed"
            db.commit()
            return False
            
    except Exception as e:
        delivery.attempt_count += 1
        delivery.status = "failed"
        delivery.response_body = str(e)[:1000]
        db.commit()
        return False


def get_webhook_deliveries(
    db: Session,
    webhook_id: str,
    limit: int = 50
) -> List[WebhookDelivery]:
    """Get recent deliveries for a webhook"""
    return db.query(WebhookDelivery).filter(
        WebhookDelivery.webhook_id == webhook_id
    ).order_by(
        WebhookDelivery.created_at.desc()
    ).limit(limit).all()
