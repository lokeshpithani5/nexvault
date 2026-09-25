from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.repositories.repair_repository import RepairRepository
from app.models.user import User

router = APIRouter(prefix="/admin/repairs", tags=["Admin Repairs"])


@router.get("")
async def list_recent_repairs(
    limit: int = 50,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = RepairRepository(db)
    repairs = await repo.list_recent(limit=limit)
    return [
        {
            "id": r.id,
            "version_id": r.version_id,
            "source_node_id": r.source_node_id,
            "target_node_id": r.target_node_id,
            "status": r.status,
            "trigger_reason": r.trigger_reason,
            "bytes_repaired": r.bytes_repaired,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "error_message": r.error_message,
        }
        for r in repairs
    ]
