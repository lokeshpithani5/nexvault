from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.repositories.event_repository import EventRepository
from app.schemas.events import EventResponse
from app.models.user import User

router = APIRouter(prefix="/admin/events", tags=["Admin Observability Events"])


@router.get("", response_model=List[EventResponse])
async def list_recent_events(
    limit: int = 100,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = EventRepository(db)
    events = await repo.list_recent(limit=limit)
    return [EventResponse.model_validate(e) for e in events]
