from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, String
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
        event_type: Optional[str] = None,
    ) -> Event:
        details = details_json or {}
        # Infer event_type if omitted
        inferred_type = event_type or details.get("event_type") or category
        if "event_type" not in details and inferred_type:
            details["event_type"] = inferred_type

        event = Event(
            severity=severity,
            category=category,
            event_type=inferred_type,
            message=message,
            details_json=details,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_recent(self, limit: int = 100) -> List[Event]:
        stmt = select(Event).order_by(Event.timestamp.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_filtered(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        node: Optional[str] = None,
        object_key: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Event]:
        stmt = select(Event)
        conditions = []

        if event_type:
            conditions.append(Event.event_type == event_type)
        if severity:
            conditions.append(Event.severity == severity.upper())
        if category:
            conditions.append(Event.category == category.upper())
        if since:
            conditions.append(Event.timestamp >= since)
        if node:
            conditions.append(
                or_(
                    Event.message.ilike(f"%{node}%"),
                    Event.details_json.cast(String).ilike(f"%{node}%"),
                )
            )
        if object_key:
            conditions.append(
                or_(
                    Event.message.ilike(f"%{object_key}%"),
                    Event.details_json.cast(String).ilike(f"%{object_key}%"),
                )
            )

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(Event.timestamp.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
