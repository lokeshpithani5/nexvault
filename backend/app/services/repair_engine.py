"""
Automatic Background Replica Repair Engine
Detects under-replicated or corrupted objects.
Identifies healthy source replicas and reconstructs missing copies on available nodes.
Measures recovery duration and bytes restored.
"""

import time
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.models.node import StorageNode
from backend.app.models.bucket import Bucket
from backend.app.models.object import ObjectEntity, ObjectVersion, ObjectReplica
from backend.app.models.repair import RepairJob
from backend.app.services.placement import select_replica_nodes
from backend.app.services.event_logger import log_event


async def repair_single_version(
    db: AsyncSession,
    version: ObjectVersion,
    bucket: Bucket,
    all_nodes_dict: Dict[str, StorageNode],
) -> Optional[RepairJob]:
    """
    Evaluates and repairs a single ObjectVersion if under-replicated.
    """
    if version.is_tombstone:
        return None

    # Prevent duplicate concurrent repair jobs for the same version
    active_job_stmt = select(RepairJob).where(
        RepairJob.version_id == version.id,
        RepairJob.status.in_(["QUEUED", "RUNNING", "PENDING"]),
    )
    active_job = (await db.execute(active_job_stmt)).scalars().first()
    if active_job:
        return None

    required_rf = bucket.replication_factor

    # Identify healthy replicas on healthy nodes
    healthy_replicas: List[ObjectReplica] = []
    for r in version.replicas:
        node = all_nodes_dict.get(r.node_id)
        if r.status == "HEALTHY" and node and node.status in ("HEALTHY", "RECOVERING") and not node.is_simulated_partitioned:
            healthy_replicas.append(r)

    if len(healthy_replicas) >= required_rf:
        # Policy is met, no repair needed
        return None

    if len(healthy_replicas) == 0:
        await log_event(
            db,
            event_type="UNRECOVERABLE_DATA_RISK",
            severity="CRITICAL",
            message=f"Zero healthy replicas found for version {version.id} of object {version.object_id}. Cannot auto-repair!",
            object_id=version.object_id,
        )
        return None

    # We need to restore replicas: choose a healthy source replica
    source_replica = healthy_replicas[0]
    source_node = all_nodes_dict.get(source_replica.node_id)
    if not source_node:
        return None

    # Identify target nodes not already holding ANY replica of this version
    existing_node_ids = {r.node_id for r in version.replicas if r.status != "MISSING"}
    eligible_target_nodes = await select_replica_nodes(
        db,
        replication_factor=1,
        exclude_node_ids=list(existing_node_ids),
    )

    if not eligible_target_nodes:
        # Fallback to any healthy node not in healthy_replicas
        current_healthy_node_ids = {r.node_id for r in healthy_replicas}
        eligible_target_nodes = await select_replica_nodes(
            db,
            replication_factor=1,
            exclude_node_ids=list(current_healthy_node_ids),
        )

    if not eligible_target_nodes:
        await log_event(
            db,
            event_type="REPAIR_STALLED_NO_NODES",
            severity="WARNING",
            message=f"Auto-repair could not find a spare healthy node to reconstruct replica for version {version.id}",
            object_id=version.object_id,
        )
        return None

    target_node = eligible_target_nodes[0]
    previous_replica_count = len(healthy_replicas)
    start_time = time.time()
    now = datetime.now(timezone.utc)

    # 1. Create RepairJob in QUEUED state
    repair_job = RepairJob(
        version_id=version.id,
        source_node_id=source_node.id,
        target_node_id=target_node.id,
        status="QUEUED",
        trigger_reason="UNDER_REPLICATED_AUTO_HEAL",
        bytes_recovered=0,
        previous_replica_count=previous_replica_count,
        started_at=now,
    )
    db.add(repair_job)
    await db.flush()

    obj_key = version.object_entity.key if version.object_entity else str(version.object_id)
    await log_event(
        db,
        event_type="REPAIR_CREATED",
        severity="INFO",
        message=f"Repair job created: rebuilding replica for '{bucket.name}/{obj_key}' (v{version.version_num}) on {target_node.id}",
        node_id=target_node.id,
        object_id=version.object_id,
        metadata_json={
            "job_id": str(repair_job.id),
            "version_id": str(version.id),
            "source_node": source_node.id,
            "target_node": target_node.id,
            "previous_replicas": previous_replica_count,
            "desired_replicas": required_rf,
        },
    )

    # 2. Transition RepairJob to RUNNING
    repair_job.status = "RUNNING"
    await db.flush()

    await log_event(
        db,
        event_type="REPAIR_STARTED",
        severity="INFO",
        message=f"Repair job {repair_job.id[:8]} started: copying {version.size_bytes} bytes from {source_node.id} to {target_node.id}",
        node_id=target_node.id,
        object_id=version.object_id,
        metadata_json={
            "job_id": str(repair_job.id),
            "source_node": source_node.id,
            "target_node": target_node.id,
            "size_bytes": version.size_bytes,
        },
    )

    # 3. Transfer chunk from source node to target node
    new_blob_id = f"repaired_{uuid.uuid4().hex[:8]}_{source_replica.blob_id}"
    try:
        async with httpx.AsyncClient() as client:
            # Fetch from source
            source_url = f"http://{source_node.host}:{source_node.port}/chunks/{source_replica.blob_id}"
            src_resp = await client.get(source_url, timeout=10.0)
            if src_resp.status_code != 200:
                raise Exception(f"Failed to fetch chunk from source node {source_node.id}: HTTP {src_resp.status_code}")

            raw_bytes = src_resp.content

            # Verify integrity before replicating
            fetched_sha = hashlib.sha256(raw_bytes).hexdigest()
            if fetched_sha != version.checksum_sha256:
                raise Exception(f"Source replica on {source_node.id} is corrupt! SHA mismatch: {fetched_sha} != {version.checksum_sha256}")

            # Upload to target
            target_url = f"http://{target_node.host}:{target_node.port}/chunks/{new_blob_id}"
            tgt_resp = await client.put(
                target_url,
                content=raw_bytes,
                headers={"Content-Type": "application/octet-stream"},
                timeout=10.0,
            )
            if tgt_resp.status_code != 200:
                raise Exception(f"Failed to upload reconstructed chunk to {target_node.id}: HTTP {tgt_resp.status_code}")

            tgt_data = tgt_resp.json()
            reported_sha = tgt_data.get("sha256")
            if reported_sha != version.checksum_sha256:
                raise Exception(f"Target node {target_node.id} reported corrupted write checksum: {reported_sha}")

        # Emit REPLICA_COPIED
        await log_event(
            db,
            event_type="REPLICA_COPIED",
            severity="INFO",
            message=f"Replica copied successfully to {target_node.id} ({len(raw_bytes)} bytes)",
            node_id=target_node.id,
            object_id=version.object_id,
            metadata_json={
                "job_id": str(repair_job.id),
                "source_node": source_node.id,
                "target_node": target_node.id,
                "bytes": len(raw_bytes),
                "blob_id": new_blob_id,
            },
        )

        # Emit CHECKSUM_VERIFIED
        await log_event(
            db,
            event_type="CHECKSUM_VERIFIED",
            severity="INFO",
            message=f"Checksum verified for rebuilt replica on {target_node.id} (SHA-256: {version.checksum_sha256[:16]}...)",
            node_id=target_node.id,
            object_id=version.object_id,
            metadata_json={
                "job_id": str(repair_job.id),
                "sha256": version.checksum_sha256,
                "target_node": target_node.id,
            },
        )

        # 4. Success: Register new healthy replica
        existing_target_rep = next((r for r in version.replicas if r.node_id == target_node.id), None)
        if existing_target_rep:
            existing_target_rep.status = "HEALTHY"
            existing_target_rep.blob_id = new_blob_id
            existing_target_rep.stored_checksum = version.checksum_sha256
            existing_target_rep.last_verified_at = datetime.now(timezone.utc)
            existing_target_rep.error_detail = None
        else:
            new_rep = ObjectReplica(
                version_id=version.id,
                node_id=target_node.id,
                shard_index=0,
                blob_id=new_blob_id,
                status="HEALTHY",
                stored_checksum=version.checksum_sha256,
                last_verified_at=datetime.now(timezone.utc),
            )
            new_rep.version = version
            if new_rep not in version.replicas:
                version.replicas.append(new_rep)
            db.add(new_rep)

        target_node.used_bytes += len(raw_bytes)
        target_node.replica_count += 1

        end_time = time.time()
        duration_ms = max(1, int((end_time - start_time) * 1000))
        duration_sec = round(end_time - start_time, 3)

        # Compute resulting healthy replicas
        resulting_replica_count = sum(
            1 for r in version.replicas
            if r.status == "HEALTHY"
            and (all_nodes_dict.get(r.node_id) and all_nodes_dict[r.node_id].status in ("HEALTHY", "RECOVERING") and not all_nodes_dict[r.node_id].is_simulated_partitioned)
        )

        repair_job.status = "COMPLETED"
        repair_job.bytes_recovered = len(raw_bytes)
        repair_job.duration_ms = duration_ms
        repair_job.previous_replica_count = previous_replica_count
        repair_job.resulting_replica_count = resulting_replica_count
        repair_job.finished_at = datetime.now(timezone.utc)

        # Emit REPAIR_COMPLETED and REPAIR_RESTORED
        await log_event(
            db,
            event_type="REPAIR_COMPLETED",
            severity="INFO",
            message=f"Repair job {repair_job.id[:8]} completed in {duration_ms}ms ({len(raw_bytes)} bytes restored). Durability: {previous_replica_count} -> {resulting_replica_count} replicas.",
            node_id=target_node.id,
            object_id=version.object_id,
            metadata_json={
                "job_id": str(repair_job.id),
                "duration_ms": duration_ms,
                "duration_seconds": duration_sec,
                "bytes_recovered": len(raw_bytes),
                "source_node": source_node.id,
                "target_node": target_node.id,
                "previous_replicas": previous_replica_count,
                "resulting_replicas": resulting_replica_count,
            },
        )

        if resulting_replica_count >= required_rf:
            await log_event(
                db,
                event_type="OBJECT_RESTORED",
                severity="INFO",
                message=f"Object '{bucket.name}/{obj_key}' restored to policy ({resulting_replica_count}/{required_rf} replicas).",
                node_id=target_node.id,
                object_id=version.object_id,
                metadata_json={
                    "version_id": str(version.id),
                    "healthy_replicas": resulting_replica_count,
                    "desired_replicas": required_rf,
                    "job_id": str(repair_job.id),
                },
            )

        return repair_job

    except Exception as e:
        end_time = time.time()
        duration_ms = max(1, int((end_time - start_time) * 1000))
        repair_job.status = "FAILED"
        repair_job.duration_ms = duration_ms
        repair_job.error_message = str(e)
        repair_job.finished_at = datetime.now(timezone.utc)
        await log_event(
            db,
            event_type="REPAIR_FAILED",
            severity="ERROR",
            message=f"Repair job failed: {str(e)}",
            node_id=target_node.id,
            object_id=version.object_id,
            metadata_json={"job_id": str(repair_job.id), "error": str(e)},
        )
        return repair_job


async def run_repair_cycle(db: AsyncSession) -> Dict[str, Any]:
    """
    Scans all objects in the cluster and triggers self-healing repairs for any degraded versions.
    """
    # Load all nodes
    nodes_res = await db.execute(select(StorageNode))
    nodes_dict = {n.id: n for n in nodes_res.scalars().all()}

    # Load all versions with bucket and replicas
    stmt = (
        select(ObjectVersion)
        .where(ObjectVersion.is_tombstone == False)
        .options(
            selectinload(ObjectVersion.replicas),
            selectinload(ObjectVersion.object_entity).selectinload(ObjectEntity.bucket),
        )
    )
    v_res = await db.execute(stmt)
    versions = v_res.scalars().all()

    completed_repairs = 0
    total_bytes_recovered = 0
    failed_repairs = 0

    for version in versions:
        bucket = version.object_entity.bucket
        job = await repair_single_version(db, version, bucket, nodes_dict)
        if job:
            if job.status == "COMPLETED":
                completed_repairs += 1
                total_bytes_recovered += job.bytes_recovered
            elif job.status == "FAILED":
                failed_repairs += 1

    await db.commit()
    return {
        "completed_repairs": completed_repairs,
        "failed_repairs": failed_repairs,
        "bytes_recovered": total_bytes_recovered,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
