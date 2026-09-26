"""
System Events & Live SSE Streaming API
"""

import json
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.core.database import get_db
from backend.app.models.event import SystemEvent
from backend.app.services.event_logger import register_subscriber, unregister_subscriber

router = APIRouter(prefix="/events", tags=["Observability & Events"])


@router.get("")
async def get_events(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(limit)
    if severity:
        stmt = stmt.where(SystemEvent.severity == severity.upper())

    res = await db.execute(stmt)
    events = res.scalars().all()

    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "severity": e.severity,
            "node_id": e.node_id,
            "object_id": str(e.object_id) if e.object_id else None,
            "message": e.message,
            "metadata_json": e.metadata_json,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


@router.get("/stream")
async def stream_live_events(request: Request):
    """
    Server-Sent Events (SSE) stream broadcasting events to React UI live.
    """
    queue = register_subscriber()

    async def event_generator():
        try:
            # Yield initial keep-alive / connection event
            yield f"data: {json.dumps({'event_type': 'CONNECTED', 'severity': 'INFO', 'message': 'Connected to NEXVAULT Live Event Stream'})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event_data)}\n\n"
                except asyncio.TimeoutError:
                    # Heartbeat comment to keep SSE connection alive
                    yield ": ping\n\n"
        finally:
            unregister_subscriber(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
