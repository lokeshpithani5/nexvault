from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, require_admin
from app.services.chaos_service import ChaosService
from app.schemas.chaos import (
    NodeFailRequest,
    NodeRestoreRequest,
    CorruptReplicaRequest,
    NetworkPartitionRequest,
    ChaosOperationResponse,
)
from app.models.user import User

router = APIRouter(prefix="/admin/chaos", tags=["Chaos Lab"])


@router.post("/node-fail", response_model=ChaosOperationResponse)
async def trigger_node_failure(
    payload: NodeFailRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.fail_node(payload.node_id, payload.action)
    await db.commit()
    return result


@router.post("/node-restore", response_model=ChaosOperationResponse)
async def trigger_node_restore(
    payload: NodeRestoreRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.restore_node(payload.node_id)
    await db.commit()
    return result


@router.post("/corrupt-replica", response_model=ChaosOperationResponse)
async def trigger_corrupt_replica(
    payload: CorruptReplicaRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.corrupt_replica(payload.replica_id, payload.node_id, payload.random)
    await db.commit()
    return result


@router.post("/network-partition", response_model=ChaosOperationResponse)
async def trigger_network_partition(
    payload: NetworkPartitionRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.network_partition(payload.node_ids, payload.partitioned)
    await db.commit()
    return result


@router.post("/scan-integrity", response_model=ChaosOperationResponse)
async def trigger_integrity_scan(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.scan_integrity()
    await db.commit()
    return result


@router.post("/rebalance", response_model=ChaosOperationResponse)
async def trigger_rebalance(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.rebalance()
    await db.commit()
    return result
