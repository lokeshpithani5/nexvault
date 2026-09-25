from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.repositories.repair_repository import RepairRepository
from app.services.repair_service import RepairService
from app.models.user import User

router = APIRouter(prefix="/admin/repairs", tags=["Admin Repairs"])


class CreateRepairJobRequest(BaseModel):
    version_id: str
    target_node_id: str
    source_node_id: Optional[str] = None
    trigger_reason: str = "ADMIN_TRIGGERED"


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


@router.post("")
async def create_repair_job(
    req: CreateRepairJobRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = RepairService(db)
    job = await service.create_repair_job(
        version_id=req.version_id,
        target_node_id=req.target_node_id,
        source_node_id=req.source_node_id,
        trigger_reason=req.trigger_reason,
    )
    await db.commit()
    return {"id": job.id, "status": job.status, "version_id": job.version_id}


@router.post("/{job_id}/execute")
async def execute_repair_job(
    job_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = RepairService(db)
    result = await service.execute_repair(job_id)
    await db.commit()
    return result


@router.post("/reconcile")
async def trigger_cluster_reconciliation(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only: Triggers an immediate cluster-wide durability scan & automatic repair cycle."""
    service = RepairService(db)
    result = await service.run_cluster_reconciliation()
    await db.commit()
    return result

