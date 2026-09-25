from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.repair_job import RepairJob


class RepairRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(
        self,
        version_id: str,
        target_node_id: str,
        source_node_id: Optional[str],
        trigger_reason: str,
    ) -> RepairJob:
        job = RepairJob(
            version_id=version_id,
            target_node_id=target_node_id,
            source_node_id=source_node_id,
            trigger_reason=trigger_reason,
            status="PENDING",
            bytes_repaired=0,
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(job)
        await self.session.flush()
        return job

    async def list_recent(self, limit: int = 50) -> List[RepairJob]:
        stmt = select(RepairJob).order_by(RepairJob.started_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        stmt = select(RepairJob).where(RepairJob.status.in_(["PENDING", "IN_PROGRESS"]))
        result = await self.session.execute(stmt)
        return len(list(result.scalars().all()))
