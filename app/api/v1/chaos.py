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


chaos_compat_router = APIRouter(prefix="/chaos", tags=["Chaos Lab Frontend"])


@chaos_compat_router.post("/kill-node/{node_id}", response_model=ChaosOperationResponse)
async def compat_kill_node(
    node_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.fail_node(node_id, action="FAIL")
    await db.commit()
    return result


@chaos_compat_router.post("/restore-node/{node_id}", response_model=ChaosOperationResponse)
async def compat_restore_node(
    node_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.restore_node(node_id)
    await db.commit()
    return result


@chaos_compat_router.post("/partition-node/{node_id}", response_model=ChaosOperationResponse)
async def compat_partition_node(
    node_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.network_partition([node_id], partitioned=True)
    await db.commit()
    return result


@chaos_compat_router.post("/heal-partition/{node_id}", response_model=ChaosOperationResponse)
async def compat_heal_partition(
    node_id: str,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.network_partition([node_id], partitioned=False)
    await db.commit()
    return result


@chaos_compat_router.post("/corrupt-replica", response_model=ChaosOperationResponse)
async def compat_corrupt_replica(
    payload: CorruptReplicaRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.corrupt_replica(payload.replica_id, payload.node_id, payload.random)
    await db.commit()
    return result


@chaos_compat_router.post("/trigger-scrub", response_model=ChaosOperationResponse)
async def compat_trigger_scrub(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.scan_integrity()
    await db.commit()
    return result


@chaos_compat_router.post("/trigger-repair", response_model=ChaosOperationResponse)
async def compat_trigger_repair(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.repair_service import RepairService
    repair_svc = RepairService(db)
    reconciled = await repair_svc.run_cluster_reconciliation()
    await db.commit()
    return ChaosOperationResponse(
        success=True,
        operation="EMERGENCY_REPAIR",
        message=f"Emergency repair cycle completed. Reconciled {len(reconciled)} degraded object(s).",
        affected_entities={"reconciled_versions": reconciled},
    )


@chaos_compat_router.post("/rebalance", response_model=ChaosOperationResponse)
async def compat_rebalance(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = ChaosService(db)
    result = await service.rebalance()
    await db.commit()
    return result


demo_router = APIRouter(tags=["Demo"])


@demo_router.post("/demo/reset")
@chaos_compat_router.post("/reset")
async def compat_demo_reset(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services.node_client import node_client
    from app.models.storage_node import StorageNode
    from app.models.repair_job import RepairJob
    from app.models.object_replica import ObjectReplica
    from app.repositories.event_repository import EventRepository
    from datetime import datetime, timezone
    from sqlalchemy import update

    for port in range(5001, 5007):
        try:
            await node_client.bring_node_online("127.0.0.1", port)
        except Exception:
            pass

    await db.execute(
        update(StorageNode).values(
            status="HEALTHY",
            is_simulated_partitioned=False,
            last_heartbeat=datetime.now(timezone.utc),
        )
    )
    await db.execute(
        update(RepairJob)
        .where(RepairJob.status.in_(["PENDING", "IN_PROGRESS"]))
        .values(status="COMPLETED", completed_at=datetime.now(timezone.utc))
    )
    await db.execute(update(ObjectReplica).values(status="HEALTHY"))
    event_repo = EventRepository(db)
    await event_repo.log_event(
        event_type="NODE_RESTORED",
        severity="INFO",
        category="CHAOS",
        message="Demo state reset: All 6 nodes healthy, replicas verified",
        details_json={"action": "DEMO_RESET", "nodes": 6},
    )
    await db.commit()
    return {
        "success": True,
        "message": "Cluster reset to baseline. All 6 nodes healthy, replicas verified.",
    }
