from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.repositories.event_repository import EventRepository
from app.schemas.events import EventResponse
from app.models.user import User

router = APIRouter(prefix="/admin/events", tags=["Admin Observability Events"])


@router.get("", response_model=List[EventResponse])
async def list_recent_events(
    event_type: Optional[str] = Query(None, description="Filter by exact event type (e.g. NODE_FAILED)"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g. INFO, WARNING, ERROR, CRITICAL)"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. NODE, REPLICA, OBJECT, CHAOS)"),
    node: Optional[str] = Query(None, description="Filter by node ID or name"),
    object: Optional[str] = Query(None, description="Filter by object key"),
    since: Optional[datetime] = Query(None, description="Filter events occurring after ISO timestamp"),
    limit: int = Query(100, ge=1, le=1000, description="Max events to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Retrieve audit & observability event log ordered newest first with optional filters."""
    repo = EventRepository(db)
    events = await repo.list_filtered(
        event_type=event_type,
        severity=severity,
        category=category,
        node=node,
        object_key=object,
        since=since,
        limit=limit,
        offset=offset,
    )
    return [EventResponse.model_validate(e) for e in events]
