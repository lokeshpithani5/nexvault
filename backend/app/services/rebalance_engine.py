"""
Cluster Storage Skew Detector & Background Rebalancing Engine
Identifies imbalanced utilization across storage nodes.
Migrates replicas from overloaded donor nodes to underloaded receiver nodes
without impacting availability.
"""

import time
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.core.config import settings
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectReplica, ObjectVersion
from backend.app.models.repair import RebalanceTask
from backend.app.services.event_logger import log_event


async def evaluate_cluster_skew(db: AsyncSession) -> Dict[str, Any]:
    """
    Evaluates whether storage distribution across healthy nodes exceeds the imbalance threshold.
    """
    stmt = select(StorageNode).where(
        StorageNode.status.in_(["HEALTHY", "RECOVERING"]),
        StorageNode.is_simulated_partitioned == False,
    )
    res = await db.execute(stmt)
    nodes = res.scalars().all()

    if len(nodes) < 2:
        return {"imbalanced": False, "reason": "Insufficient healthy nodes"}

    counts = [n.replica_count for n in nodes]
    avg_count = sum(counts) / len(counts)
    max_node = max(nodes, key=lambda n: n.replica_count)
    min_node = min(nodes, key=lambda n: n.replica_count)

    diff = max_node.replica_count - min_node.replica_count
    # Imbalanced if difference is at least 2 and skew exceeds threshold
    threshold = settings.REBALANCE_IMBALANCE_THRESHOLD
    imbalanced = diff >= 2 and (max_node.replica_count > avg_count * (1 + threshold))

    return {
        "imbalanced": imbalanced,
        "avg_replicas": round(avg_count, 1),
        "max_node": {"id": max_node.id, "count": max_node.replica_count, "used_bytes": max_node.used_bytes},
        "min_node": {"id": min_node.id, "count": min_node.replica_count, "used_bytes": min_node.used_bytes},
        "difference": diff,
    }


async def run_rebalance_cycle(db: AsyncSession, force: bool = False) -> Dict[str, Any]:
    """
    Runs rebalancing migration if cluster skew is detected or force=True.
    """
    skew_eval = await evaluate_cluster_skew(db)
    if not skew_eval.get("imbalanced") and not force:
        return {
            "rebalanced": False,
            "message": "Cluster storage is balanced within threshold limits.",
            "skew_eval": skew_eval,
        }

    stmt = select(StorageNode).where(
        StorageNode.status.in_(["HEALTHY", "RECOVERING"]),
        StorageNode.is_simulated_partitioned == False,
    )
    res = await db.execute(stmt)
    nodes = res.scalars().all()

    if len(nodes) < 2:
        return {"rebalanced": False, "message": "Not enough nodes to rebalance"}

    # Sort nodes by replica count descending
    nodes.sort(key=lambda n: (n.replica_count, n.used_bytes), reverse=True)
    donor_node = nodes[0]
    receiver_node = nodes[-1]

    if donor_node.replica_count <= receiver_node.replica_count:
        return {"rebalanced": False, "message": "Cluster balanced"}

    # Find a candidate replica on donor_node whose ObjectVersion is NOT on receiver_node
    cand_stmt = (
        select(ObjectReplica)
        .where(ObjectReplica.node_id == donor_node.id, ObjectReplica.status == "HEALTHY")
        .options(selectinload(ObjectReplica.version).selectinload(ObjectVersion.replicas))
    )
    cand_res = await db.execute(cand_stmt)
    candidates = cand_res.scalars().all()

    movable_replica: Optional[ObjectReplica] = None
    for cand in candidates:
        version_node_ids = {r.node_id for r in cand.version.replicas}
        if receiver_node.id not in version_node_ids:
            movable_replica = cand
            break

    if not movable_replica:
        return {"rebalanced": False, "message": "No eligible replicas to migrate without violating uniqueness"}

    version = movable_replica.version
    new_blob_id = f"rebalanced_{uuid.uuid4().hex[:8]}_{movable_replica.blob_id}"
    bytes_moved = version.size_bytes

    await log_event(
        db,
        event_type="REBALANCE_TRIGGERED",
        severity="INFO",
        message=f"Rebalance migration started: moving replica of version {version.id} ({bytes_moved} bytes) from {donor_node.id} to {receiver_node.id}",
        node_id=receiver_node.id,
        object_id=version.object_id,
    )

    try:
        async with httpx.AsyncClient() as client:
            # 1. Fetch from donor
            src_url = f"http://{donor_node.host}:{donor_node.port}/chunks/{movable_replica.blob_id}"
            src_resp = await client.get(src_url, timeout=10.0)
            if src_resp.status_code != 200:
                raise Exception(f"Failed to fetch from donor {donor_node.id}")
            data = src_resp.content

            # 2. Upload to receiver
            dst_url = f"http://{receiver_node.host}:{receiver_node.port}/chunks/{new_blob_id}"
            dst_resp = await client.put(
                dst_url,
                content=data,
                headers={"Content-Type": "application/octet-stream"},
                timeout=10.0,
            )
            if dst_resp.status_code != 200:
                raise Exception(f"Failed to write to receiver {receiver_node.id}")

            # 3. Delete from donor
            await client.delete(src_url, timeout=5.0)

        # 4. Update replica metadata to receiver node
        movable_replica.node_id = receiver_node.id
        movable_replica.blob_id = new_blob_id
        movable_replica.last_verified_at = datetime.now(timezone.utc)

        donor_node.replica_count = max(0, donor_node.replica_count - 1)
        donor_node.used_bytes = max(0, donor_node.used_bytes - bytes_moved)
        receiver_node.replica_count += 1
        receiver_node.used_bytes += bytes_moved

        # Record task
        task = RebalanceTask(
            source_node_id=donor_node.id,
            target_node_id=receiver_node.id,
            replica_id=movable_replica.id,
            bytes_moved=bytes_moved,
            status="COMPLETED",
        )
        db.add(task)

        await log_event(
            db,
            event_type="REBALANCE_COMPLETED",
            severity="INFO",
            message=f"Rebalance completed: chunk migrated successfully to {receiver_node.id}. Skew reduced.",
            node_id=receiver_node.id,
            object_id=version.object_id,
            metadata_json={"source": donor_node.id, "target": receiver_node.id, "bytes": bytes_moved},
        )
        await db.commit()

        return {
            "rebalanced": True,
            "source_node": donor_node.id,
            "target_node": receiver_node.id,
            "bytes_moved": bytes_moved,
            "replica_id": movable_replica.id,
        }

    except Exception as e:
        await log_event(
            db,
            event_type="REBALANCE_FAILED",
            severity="ERROR",
            message=f"Rebalancing migration failed: {str(e)}",
            node_id=receiver_node.id,
        )
        await db.commit()
        return {"rebalanced": False, "error": str(e)}
