"""
Structured Event Logging & Real-time SSE Dispatcher
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.event import SystemEvent

# In-memory pub/sub queues for live SSE stream subscribers
_subscribers: List[asyncio.Queue] = []


def register_subscriber() -> asyncio.Queue:
    queue = asyncio.Queue(maxsize=100)
    _subscribers.append(queue)
    return queue


def unregister_subscriber(queue: asyncio.Queue):
    if queue in _subscribers:
        _subscribers.remove(queue)


async def broadcast_event(event_dict: dict):
    """Pushes new events to all active SSE subscribers."""
    for queue in list(_subscribers):
        try:
            queue.put_nowait(event_dict)
        except asyncio.QueueFull:
            pass


async def log_event(
    db: AsyncSession,
    event_type: str,
    severity: str,
    message: str,
    node_id: Optional[str] = None,
    object_id: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> SystemEvent:
    """
    Persists structured event in database and broadcasts to UI subscribers.
    """
    event = SystemEvent(
        event_type=event_type,
        severity=severity,
        node_id=node_id,
        object_id=object_id,
        message=message,
        metadata_json=metadata_json or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()

    event_payload = {
        "id": event.id,
        "event_type": event.event_type,
        "severity": event.severity,
        "node_id": event.node_id,
        "object_id": event.object_id,
        "message": event.message,
        "metadata_json": event.metadata_json,
        "created_at": event.created_at.isoformat(),
    }

    # Dispatch to live SSE streams
    asyncio.create_task(broadcast_event(event_payload))

    return event
