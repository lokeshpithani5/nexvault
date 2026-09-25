from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from app.models.storage_node import StorageNode
from app.models.object_model import Object, ObjectVersion
from app.models.object_replica import ObjectReplica
from app.models.repair_job import RepairJob
from app.models.event import Event
from app.models.bucket import Bucket
from app.core.logging_config import logger


class MetricsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_system_metrics(self) -> Dict[str, Any]:
        """Calculates real cluster, object, replica, storage, and recovery metrics directly from persistent state."""
        # 1. Node Metrics
        nodes_res = await self.session.execute(select(StorageNode))
        nodes = list(nodes_res.scalars().all())

        total_nodes = len(nodes)
        healthy_nodes = sum(1 for n in nodes if n.status == "HEALTHY" and not n.is_simulated_partitioned)
        degraded_nodes = sum(1 for n in nodes if n.status == "DEGRADED" or (n.status == "HEALTHY" and n.is_simulated_partitioned))
        failed_nodes = sum(1 for n in nodes if n.status == "FAILED")
        recovering_nodes = sum(1 for n in nodes if n.status == "RECOVERING")

        total_cap = sum(n.total_capacity_bytes for n in nodes)
        total_physical_storage = sum(n.used_capacity_bytes for n in nodes)
        utilization_pct = round((total_physical_storage / total_cap * 100.0), 2) if total_cap > 0 else 0.0

        # 2. Object & Logical Storage Metrics
        # Eager load versions, replicas, and bucket policies to avoid greenlet/lazyload issues
        objects_stmt = (
            select(Object)
            .where(Object.is_deleted == False)
            .options(
                selectinload(Object.versions).selectinload(ObjectVersion.replicas),
                selectinload(Object.bucket).selectinload(Bucket.policy),
            )
        )
        objects_res = await self.session.execute(objects_stmt)
        objects = list(objects_res.scalars().all())

        total_objects = len(objects)
        healthy_objects = 0
        degraded_objects = 0
        total_logical_storage = 0

        for obj in objects:
            active_versions = [v for v in obj.versions if not v.is_tombstone]
            if not active_versions:
                continue

            latest_v = active_versions[0]
            total_logical_storage += latest_v.size_bytes

            # Check healthy replicas count vs policy RF
            required_rf = 3
            if obj.bucket and obj.bucket.policy:
                required_rf = obj.bucket.policy.replication_factor

            healthy_reps_count = sum(1 for r in latest_v.replicas if r.status == "HEALTHY")
            if healthy_reps_count >= required_rf:
                healthy_objects += 1
            else:
                degraded_objects += 1

        # 3. Replica Metrics
        reps_res = await self.session.execute(select(ObjectReplica))
        all_replicas = list(reps_res.scalars().all())
        total_replicas = len(all_replicas)
        healthy_replicas = sum(1 for r in all_replicas if r.status == "HEALTHY")
        corrupted_replicas = sum(1 for r in all_replicas if r.status == "CORRUPTED")

        # 4. Storage Overhead
        storage_overhead = None
        if total_logical_storage > 0:
            storage_overhead = round(total_physical_storage / total_logical_storage, 2)

        # 5. Repair Job & Recovery Metrics
        repairs_res = await self.session.execute(select(RepairJob))
        all_repairs = list(repairs_res.scalars().all())

        pending_repairs = sum(1 for r in all_repairs if r.status == "PENDING")
        running_repairs = sum(1 for r in all_repairs if r.status == "IN_PROGRESS")
        completed_repairs = [r for r in all_repairs if r.status == "COMPLETED"]
        failed_repairs = [r for r in all_repairs if r.status == "FAILED"]

        replicas_repaired = len(completed_repairs)
        bytes_recovered = sum(r.bytes_repaired for r in completed_repairs)

        recovery_durations = [
            (r.completed_at - r.started_at).total_seconds()
            for r in completed_repairs
            if r.completed_at and r.started_at and r.completed_at >= r.started_at
        ]

        avg_recovery = round(sum(recovery_durations) / len(recovery_durations), 2) if recovery_durations else None
        fastest_recovery = round(min(recovery_durations), 2) if recovery_durations else None
        slowest_recovery = round(max(recovery_durations), 2) if recovery_durations else None

        # 6. Latest Integrity Scan
        scan_event_stmt = (
            select(Event)
            .where(
                or_(
                    Event.category == "INTEGRITY",
                    Event.event_type.in_(["INTEGRITY_SCAN_COMPLETED", "INTEGRITY_SCAN_STARTED"]),
                )
            )
            .order_by(Event.timestamp.desc())
            .limit(1)
        )
        scan_event_res = await self.session.execute(scan_event_stmt)
        scan_event = scan_event_res.scalars().first()
        latest_integrity_scan = None
        if scan_event:
            latest_integrity_scan = {
                "timestamp": scan_event.timestamp.isoformat(),
                "event_type": scan_event.event_type,
                "message": scan_event.message,
                "details": scan_event.details_json,
            }

        # 7. Latest Rebalance
        reb_event_stmt = (
            select(Event)
            .where(
                or_(
                    Event.event_type.in_(["REBALANCE_COMPLETED", "REBALANCE_STARTED"]),
                    Event.message.ilike("%rebalance%"),
                )
            )
            .order_by(Event.timestamp.desc())
            .limit(1)
        )
        reb_event_res = await self.session.execute(reb_event_stmt)
        reb_event = reb_event_res.scalars().first()
        latest_rebalance = None
        if reb_event:
            latest_rebalance = {
                "timestamp": reb_event.timestamp.isoformat(),
                "event_type": reb_event.event_type,
                "message": reb_event.message,
                "details": reb_event.details_json,
            }

        return {
            "total_nodes": total_nodes,
            "healthy_nodes": healthy_nodes,
            "degraded_nodes": degraded_nodes,
            "failed_nodes": failed_nodes,
            "recovering_nodes": recovering_nodes,
            "total_objects": total_objects,
            "healthy_objects": healthy_objects,
            "degraded_objects": degraded_objects,
            "total_replicas": total_replicas,
            "healthy_replicas": healthy_replicas,
            "corrupted_replicas": corrupted_replicas,
            "repair_jobs_pending": pending_repairs,
            "repair_jobs_running": running_repairs,
            "repair_jobs_completed": len(completed_repairs),
            "repair_jobs_failed": len(failed_repairs),
            "replicas_repaired": replicas_repaired,
            "bytes_recovered": bytes_recovered,
            "total_logical_storage": total_logical_storage,
            "total_physical_storage": total_physical_storage,
            "storage_overhead": storage_overhead,
            "cluster_utilization_percentage": utilization_pct,
            "latest_integrity_scan_result": latest_integrity_scan,
            "latest_rebalance_result": latest_rebalance,
            "recovery_metrics": {
                "average_recovery_time_seconds": avg_recovery,
                "fastest_recovery_seconds": fastest_recovery,
                "slowest_recovery_seconds": slowest_recovery,
                "total_repairs": len(all_repairs),
                "successful_repairs": len(completed_repairs),
                "failed_repairs": len(failed_repairs),
                "replicas_repaired": replicas_repaired,
                "bytes_recovered": bytes_recovered,
            },
        }

    async def get_cluster_summary(self) -> Dict[str, Any]:
        """Provides a concise, dashboard-friendly summary for the admin cluster overview."""
        metrics = await self.get_system_metrics()

        cluster_status = "HEALTHY"
        if metrics["failed_nodes"] > 0 or metrics["degraded_nodes"] > 2:
            cluster_status = "CRITICAL" if metrics["healthy_nodes"] < 3 else "DEGRADED"
        elif metrics["degraded_nodes"] > 0 or metrics["corrupted_replicas"] > 0 or metrics["degraded_objects"] > 0:
            cluster_status = "DEGRADED"

        return {
            "cluster_status": cluster_status,
            "node_counts": {
                "total": metrics["total_nodes"],
                "healthy": metrics["healthy_nodes"],
                "degraded": metrics["degraded_nodes"],
                "failed": metrics["failed_nodes"],
                "recovering": metrics["recovering_nodes"],
            },
            "object_health": {
                "total": metrics["total_objects"],
                "healthy": metrics["healthy_objects"],
                "degraded": metrics["degraded_objects"],
            },
            "replica_health": {
                "total": metrics["total_replicas"],
                "healthy": metrics["healthy_replicas"],
                "corrupted": metrics["corrupted_replicas"],
            },
            "active_repair_count": metrics["repair_jobs_pending"] + metrics["repair_jobs_running"],
            "storage_utilization": {
                "total_capacity_bytes": sum(n.total_capacity_bytes for n in (await self.session.execute(select(StorageNode))).scalars().all()),
                "used_capacity_bytes": metrics["total_physical_storage"],
                "utilization_percent": metrics["cluster_utilization_percentage"],
                "logical_storage_bytes": metrics["total_logical_storage"],
                "overhead_ratio": metrics["storage_overhead"],
            },
            "durability_state": {
                "degraded_objects_count": metrics["degraded_objects"],
                "under_replicated": metrics["degraded_objects"] > 0,
                "corrupted_replicas_count": metrics["corrupted_replicas"],
            },
        }
