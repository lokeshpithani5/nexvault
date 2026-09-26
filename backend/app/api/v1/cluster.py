"""
Cluster Telemetry & Health API
Provides real-time topology, repair records, durability metrics, and storage overhead measurements.
"""

from typing import List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.models.node import StorageNode
from backend.app.models.bucket import Bucket
from backend.app.models.object import ObjectEntity, ObjectVersion, ObjectReplica
from backend.app.models.repair import RepairJob, RebalanceTask

router = APIRouter(prefix="/cluster", tags=["Cluster Telemetry"])


@router.get("/overview")
async def get_cluster_overview(db: AsyncSession = Depends(get_db)):
    # Query Nodes
    n_res = await db.execute(select(StorageNode))
    nodes = n_res.scalars().all()
    total_nodes = len(nodes)
    healthy_nodes = sum(1 for n in nodes if n.status == "HEALTHY" and not n.is_simulated_partitioned)
    failed_nodes = sum(1 for n in nodes if n.status == "FAILED")
    degraded_nodes = sum(1 for n in nodes if n.status == "DEGRADED" or n.is_simulated_partitioned)

    total_capacity = sum(n.capacity_bytes for n in nodes)
    total_used = sum(n.used_bytes for n in nodes)

    # Query Objects & Buckets
    b_count_res = await db.execute(select(func.count(Bucket.id)))
    bucket_count = b_count_res.scalar() or 0

    o_count_res = await db.execute(select(func.count(ObjectEntity.id)).where(ObjectEntity.is_deleted == False))
    object_count = o_count_res.scalar() or 0

    # Active repair jobs
    rep_res = await db.execute(
        select(func.count(RepairJob.id)).where(RepairJob.status.in_(["PENDING", "RUNNING"]))
    )
    active_repairs = rep_res.scalar() or 0

    # Health score
    health_score = round((healthy_nodes / total_nodes * 100), 1) if total_nodes > 0 else 0

    return {
        "status": "HEALTHY" if health_score == 100 else ("DEGRADED" if health_score >= 50 else "CRITICAL"),
        "health_score_pct": health_score,
        "nodes": {
            "total": total_nodes,
            "healthy": healthy_nodes,
            "degraded": degraded_nodes,
            "failed": failed_nodes,
        },
        "storage": {
            "total_capacity_bytes": total_capacity,
            "total_used_bytes": total_used,
            "available_bytes": max(0, total_capacity - total_used),
            "utilization_pct": round((total_used / total_capacity * 100), 2) if total_capacity > 0 else 0,
        },
        "inventory": {
            "buckets_count": bucket_count,
            "active_objects_count": object_count,
            "active_repairs_count": active_repairs,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/nodes")
async def get_nodes(db: AsyncSession = Depends(get_db)):
    n_res = await db.execute(select(StorageNode).order_by(StorageNode.port))
    nodes = n_res.scalars().all()
    return [
        {
            "id": n.id,
            "name": n.name,
            "host": n.host,
            "port": n.port,
            "zone": n.zone,
            "status": n.status,
            "is_simulated_partitioned": n.is_simulated_partitioned,
            "capacity_bytes": n.capacity_bytes,
            "used_bytes": n.used_bytes,
            "replica_count": n.replica_count,
            "last_heartbeat_at": n.last_heartbeat_at.isoformat() if n.last_heartbeat_at else None,
        }
        for n in nodes
    ]


@router.get("/repairs")
async def get_repairs(limit: int = 50, db: AsyncSession = Depends(get_db)):
    r_res = await db.execute(
        select(RepairJob)
        .order_by(RepairJob.created_at.desc())
        .limit(limit)
    )
    repairs = r_res.scalars().all()

    reb_res = await db.execute(
        select(RebalanceTask)
        .order_by(RebalanceTask.created_at.desc())
        .limit(limit)
    )
    rebalances = reb_res.scalars().all()

    return {
        "repairs": [
            {
                "id": str(r.id),
                "version_id": str(r.version_id),
                "source_node_id": r.source_node_id,
                "target_node_id": r.target_node_id,
                "status": r.status,
                "trigger_reason": r.trigger_reason,
                "bytes_recovered": r.bytes_recovered,
                "duration_ms": getattr(r, "duration_ms", 0),
                "previous_replica_count": getattr(r, "previous_replica_count", 0),
                "resulting_replica_count": getattr(r, "resulting_replica_count", 0),
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat(),
            }
            for r in repairs
        ],
        "rebalances": [
            {
                "id": str(t.id),
                "source_node_id": t.source_node_id,
                "target_node_id": t.target_node_id,
                "replica_id": str(t.replica_id),
                "bytes_moved": t.bytes_moved,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            }
            for t in rebalances
        ],
    }


@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """
    Real cluster metrics calculated from actual state:
    - healthy node count
    - failed node count
    - degraded object count
    - repair jobs completed
    - repair jobs failed
    - bytes recovered
    - average repair duration
    - last repair duration
    - logical storage
    - physical storage
    - replication overhead
    - cluster utilization
    """
    # 1. Node availability & states
    n_res = await db.execute(select(StorageNode))
    nodes = n_res.scalars().all()
    healthy_nodes = sum(1 for n in nodes if n.status == "HEALTHY" and not n.is_simulated_partitioned)
    failed_nodes = sum(1 for n in nodes if n.status == "FAILED")
    degraded_nodes = sum(1 for n in nodes if n.status == "DEGRADED" or n.is_simulated_partitioned)
    availability_pct = round((healthy_nodes / len(nodes) * 100), 1) if nodes else 0

    total_capacity = sum(n.capacity_bytes for n in nodes)
    total_used = sum(n.used_bytes for n in nodes)
    cluster_utilization_pct = round((total_used / total_capacity * 100), 2) if total_capacity > 0 else 0.0

    # 2. Repair Metrics
    rep_res = await db.execute(select(RepairJob).order_by(RepairJob.created_at.asc()))
    all_repairs = rep_res.scalars().all()
    completed_repairs = [r for r in all_repairs if r.status == "COMPLETED"]
    failed_repairs = [r for r in all_repairs if r.status == "FAILED"]
    total_recovered_bytes = sum(r.bytes_recovered for r in completed_repairs)

    recovery_durations_ms = []
    for r in completed_repairs:
        dur_ms = getattr(r, "duration_ms", 0)
        if dur_ms and dur_ms > 0:
            recovery_durations_ms.append(dur_ms)
        elif r.started_at and r.finished_at:
            ms = int((r.finished_at - r.started_at).total_seconds() * 1000)
            if ms >= 0:
                recovery_durations_ms.append(ms)

    avg_repair_duration_ms = round(sum(recovery_durations_ms) / len(recovery_durations_ms), 1) if recovery_durations_ms else 0.0
    avg_recovery_seconds = round(avg_repair_duration_ms / 1000.0, 3)

    last_repair = completed_repairs[-1] if completed_repairs else None
    last_repair_duration_ms = (
        getattr(last_repair, "duration_ms", 0)
        if last_repair and getattr(last_repair, "duration_ms", 0) > 0
        else (int((last_repair.finished_at - last_repair.started_at).total_seconds() * 1000) if (last_repair and last_repair.started_at and last_repair.finished_at) else 0)
    )

    # 3. Storage & Degraded Object Measurement
    v_res = await db.execute(
        select(ObjectVersion)
        .where(ObjectVersion.is_tombstone == False)
        .options(
            selectinload(ObjectVersion.replicas),
            selectinload(ObjectVersion.object_entity).selectinload(ObjectEntity.bucket),
        )
    )
    versions = v_res.scalars().all()
    logical_bytes = sum(v.size_bytes for v in versions)

    nodes_dict = {n.id: n for n in nodes}
    degraded_objects_count = 0
    for v in versions:
        bucket = v.object_entity.bucket if v.object_entity else None
        required_rf = bucket.replication_factor if bucket else 3
        healthy_count = sum(
            1 for r in v.replicas
            if r.status == "HEALTHY"
            and (nodes_dict.get(r.node_id) and nodes_dict[r.node_id].status in ("HEALTHY", "RECOVERING") and not nodes_dict[r.node_id].is_simulated_partitioned)
        )
        if healthy_count < required_rf:
            degraded_objects_count += 1

    rep_bytes_res = await db.execute(
        select(ObjectReplica)
        .where(ObjectReplica.status == "HEALTHY")
        .options(selectinload(ObjectReplica.version))
    )
    healthy_replicas = rep_bytes_res.scalars().all()
    physical_stored_bytes = sum(r.version.size_bytes for r in healthy_replicas if r.version)

    overhead_ratio = round(physical_stored_bytes / logical_bytes, 2) if logical_bytes > 0 else 3.0

    return {
        # Core requested metrics
        "healthy_node_count": healthy_nodes,
        "failed_node_count": failed_nodes,
        "degraded_node_count": degraded_nodes,
        "degraded_object_count": degraded_objects_count,
        "repair_jobs_completed": len(completed_repairs),
        "repair_jobs_failed": len(failed_repairs),
        "bytes_recovered": total_recovered_bytes,
        "average_repair_duration_ms": avg_repair_duration_ms,
        "last_repair_duration_ms": last_repair_duration_ms,
        "logical_storage": logical_bytes,
        "physical_storage": physical_stored_bytes,
        "replication_overhead": overhead_ratio,
        "cluster_utilization": cluster_utilization_pct,

        # Backwards compatible structure
        "node_availability_pct": availability_pct,
        "active_nodes_count": healthy_nodes,
        "total_nodes_count": len(nodes),
        "repairs": {
            "total_jobs": len(all_repairs),
            "completed": len(completed_repairs),
            "failed": len(failed_repairs),
            "total_bytes_recovered": total_recovered_bytes,
            "avg_recovery_duration_seconds": avg_recovery_seconds,
            "avg_repair_duration_ms": avg_repair_duration_ms,
            "last_repair_duration_ms": last_repair_duration_ms,
        },
        "overhead": {
            "logical_bytes": logical_bytes,
            "physical_stored_bytes": physical_stored_bytes,
            "replication_multiplier": f"{overhead_ratio}x",
            "erasure_coding_equivalent": "1.5x (4+2)",
        },
        "zones": {
            "ZONE_A": {
                "nodes": [n.id for n in nodes if n.zone == "ZONE_A"],
                "used_bytes": sum(n.used_bytes for n in nodes if n.zone == "ZONE_A"),
            },
            "ZONE_B": {
                "nodes": [n.id for n in nodes if n.zone == "ZONE_B"],
                "used_bytes": sum(n.used_bytes for n in nodes if n.zone == "ZONE_B"),
            },
        },
    }
