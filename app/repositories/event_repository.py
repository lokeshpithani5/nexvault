from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.event import Event


class EventRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(
        self,
        severity: str,
        category: str,
        message: str,
        details_json: Dict[str, Any] = None,
    ) -> Event:
        event = Event(
            severity=severity,
            category=category,
            message=message,
            details_json=details_json or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_recent(self, limit: int = 100) -> List[Event]:
        stmt = select(Event).order_by(Event.timestamp.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
