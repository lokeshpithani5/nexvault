"""
Concurrent Multi-Zone Data Pipeline
Handles parallel fan-out writes with quorum validation,
failover reads across healthy replicas, on-the-fly checksum verification,
and version-aware tombstone deletion.
"""

import uuid
import hashlib
import asyncio
from datetime import datetime, timezone
from typing import Tuple, Optional, List

import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from backend.app.models.bucket import Bucket
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectEntity, ObjectVersion, ObjectReplica
from backend.app.services.placement import select_replica_nodes
from backend.app.services.event_logger import log_event


async def upload_chunk_to_node(
    client: httpx.AsyncClient,
    node: StorageNode,
    blob_id: str,
    data: bytes,
    expected_hash: str,
) -> Tuple[bool, StorageNode, str]:
    """Uploads chunk to a single node and verifies returned hash."""
    url = f"http://{node.host}:{node.port}/chunks/{blob_id}"
    try:
        resp = await client.put(
            url,
            content=data,
            headers={"Content-Type": "application/octet-stream"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            res_json = resp.json()
            if res_json.get("sha256") == expected_hash:
                return True, node, ""
            return False, node, f"Hash mismatch: got {res_json.get('sha256')}, expected {expected_hash}"
        return False, node, f"HTTP status {resp.status_code}: {resp.text}"
    except Exception as e:
        return False, node, f"Connection failed: {str(e)}"


async def write_object(
    db: AsyncSession,
    bucket: Bucket,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> ObjectVersion:
    """
    Concurrent fan-out upload across failure domains with quorum validation.
    """
    # 1. Compute Cryptographic Checksums
    size_bytes = len(data)
    checksum_sha256 = hashlib.sha256(data).hexdigest()

    # 2. Get or Create Logical ObjectEntity
    stmt = (
        select(ObjectEntity)
        .where(ObjectEntity.bucket_id == bucket.id, ObjectEntity.key == key)
        .options(selectinload(ObjectEntity.versions))
    )
    res = await db.execute(stmt)
    obj_entity = res.scalar_one_or_none()

    if not obj_entity:
        obj_entity = ObjectEntity(
            bucket_id=bucket.id,
            key=key,
            is_deleted=False,
        )
        db.add(obj_entity)
        await db.flush()
        next_version_num = 1
    else:
        obj_entity.is_deleted = False
        # Calculate next version
        max_v = max([v.version_num for v in obj_entity.versions], default=0)
        next_version_num = max_v + 1

    # 3. Select Zone-Aware Replica Nodes
    rf = bucket.replication_factor
    target_nodes = await select_replica_nodes(db, replication_factor=rf)
    if not target_nodes:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No healthy storage nodes available in cluster",
        )

    # 4. Generate unique blob ID
    safe_key = key.replace("/", "_").replace("\\", "_")
    blob_id = f"{bucket.name}_{safe_key}_v{next_version_num}_{uuid.uuid4().hex[:8]}"

    # 5. Parallel Fan-Out Upload to all selected nodes
    async with httpx.AsyncClient() as client:
        upload_tasks = [
            upload_chunk_to_node(client, node, blob_id, data, checksum_sha256)
            for node in target_nodes
        ]
        results = await asyncio.gather(*upload_tasks)

    successful_nodes: List[StorageNode] = []
    failures = []
    for success, node, err in results:
        if success:
            successful_nodes.append(node)
        else:
            failures.append(f"{node.id}: {err}")

    # 6. Quorum Check (at least majority of RF, or min 1 if RF=1)
    min_quorum = max(1, (rf // 2) + 1)
    if len(successful_nodes) < min_quorum:
        # Cleanup any partial writes
        async with httpx.AsyncClient() as client:
            cleanup_tasks = [
                client.delete(f"http://{node.host}:{node.port}/chunks/{blob_id}", timeout=2.0)
                for node in successful_nodes
            ]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        err_msg = f"Write quorum failed. Succeeded on {len(successful_nodes)}/{rf} nodes. Errors: {'; '.join(failures)}"
        await log_event(
            db,
            event_type="WRITE_QUORUM_FAILED",
            severity="ERROR",
            message=err_msg,
            object_id=obj_entity.id,
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=err_msg)

    # 7. Persist Version and Replica Metadata in Control Plane
    new_version = ObjectVersion(
        object_id=obj_entity.id,
        version_num=next_version_num,
        size_bytes=size_bytes,
        content_type=content_type,
        checksum_sha256=checksum_sha256,
        is_tombstone=False,
        storage_policy=bucket.durability_policy,
    )
    db.add(new_version)
    await db.flush()

    for node in successful_nodes:
        replica = ObjectReplica(
            version_id=new_version.id,
            node_id=node.id,
            shard_index=0,
            blob_id=blob_id,
            status="HEALTHY",
            stored_checksum=checksum_sha256,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(replica)
        node.used_bytes += size_bytes
        node.replica_count += 1

    # Durability State
    durability_state = "HEALTHY" if len(successful_nodes) >= rf else "DEGRADED"

    # Structured Audit Event
    zone_distribution = [f"{n.id}({n.zone})" for n in successful_nodes]
    await log_event(
        db,
        event_type="OBJECT_UPLOADED" if durability_state == "HEALTHY" else "OBJECT_UPLOADED_DEGRADED",
        severity="INFO" if durability_state == "HEALTHY" else "WARNING",
        message=f"Object '{bucket.name}/{key}' (v{next_version_num}, {size_bytes} bytes) stored [{durability_state}] with {len(successful_nodes)}/{rf} replicas across {', '.join(zone_distribution)}",
        object_id=obj_entity.id,
        metadata_json={
            "bucket": bucket.name,
            "key": key,
            "version": next_version_num,
            "size": size_bytes,
            "sha256": checksum_sha256,
            "desired_replicas": rf,
            "successful_replicas": len(successful_nodes),
            "failed_replicas": len(failures),
            "durability_state": durability_state,
            "nodes": [n.id for n in successful_nodes],
            "zones": [n.zone for n in successful_nodes],
        },
    )

    await db.commit()

    # Eagerly load replicas before returning to prevent MissingGreenlet lazy-load error
    stmt = (
        select(ObjectVersion)
        .where(ObjectVersion.id == new_version.id)
        .options(selectinload(ObjectVersion.replicas))
    )
    reloaded_res = await db.execute(stmt)
    return reloaded_res.scalar_one()


async def read_object(
    db: AsyncSession,
    bucket_name: str,
    key: str,
    version_num: Optional[int] = None,
) -> Tuple[bytes, ObjectVersion]:
    """
    Resilient failover read pipeline.
    Tries healthy replicas first; falls back seamlessly on node drop or corruption.
    Verifies SHA-256 on the fly.
    """
    # 1. Fetch Bucket & Object
    b_stmt = select(Bucket).where(Bucket.name == bucket_name)
    b_res = await db.execute(b_stmt)
    bucket = b_res.scalar_one_or_none()
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")

    o_stmt = (
        select(ObjectEntity)
        .where(ObjectEntity.bucket_id == bucket.id, ObjectEntity.key == key)
        .options(selectinload(ObjectEntity.versions).selectinload(ObjectVersion.replicas))
    )
    o_res = await db.execute(o_stmt)
    obj_entity = o_res.scalar_one_or_none()

    if not obj_entity or not obj_entity.versions:
        raise HTTPException(status_code=404, detail=f"Object '{key}' not found in bucket '{bucket_name}'")

    # 2. Identify Target Version
    if version_num is not None:
        target_version = next((v for v in obj_entity.versions if v.version_num == version_num), None)
        if not target_version:
            raise HTTPException(status_code=404, detail=f"Version {version_num} of '{key}' not found")
    else:
        # Latest version
        target_version = sorted(obj_entity.versions, key=lambda v: v.version_num, reverse=True)[0]

    # 3. Check for Deletion Tombstone
    if target_version.is_tombstone:
        raise HTTPException(status_code=404, detail=f"Object '{key}' has been deleted (Tombstone)")

    replicas = target_version.replicas
    if not replicas:
        raise HTTPException(status_code=500, detail="Metadata error: No replicas registered for version")

    # 4. Fetch all nodes to prioritize healthy/unpartitioned nodes and allow spare node selection on repair
    nodes_res = await db.execute(select(StorageNode))
    nodes_dict = {n.id: n for n in nodes_res.scalars().all()}

    # Sort replicas: HEALTHY status and node status HEALTHY first
    def replica_priority(rep: ObjectReplica):
        node = nodes_dict.get(rep.node_id)
        is_node_up = node and node.status in ("HEALTHY", "RECOVERING") and not node.is_simulated_partitioned
        is_rep_healthy = rep.status == "HEALTHY"
        return (1 if is_node_up and is_rep_healthy else 0, 1 if is_rep_healthy else 0)

    sorted_replicas = sorted(replicas, key=replica_priority, reverse=True)

    errors = []
    # 5. Resilient Failover Loop
    async with httpx.AsyncClient() as client:
        for replica in sorted_replicas:
            node = nodes_dict.get(replica.node_id)
            if not node:
                continue

            url = f"http://{node.host}:{node.port}/chunks/{replica.blob_id}"
            try:
                resp = await client.get(url, timeout=3.0)
                if resp.status_code == 200:
                    data = resp.content
                    # Verify on-the-fly integrity
                    calc_sha = hashlib.sha256(data).hexdigest()
                    if calc_sha == target_version.checksum_sha256:
                        # Success!
                        # If a prior replica was corrupted, trigger immediate self-healing repair
                        if any("bit-rot" in e or "corrupted" in e for e in errors):
                            try:
                                from backend.app.services.repair_engine import repair_single_version
                                await repair_single_version(db, target_version, bucket, nodes_dict)
                                await db.commit()
                            except Exception:
                                pass
                        return data, target_version
                    else:
                        # BIT-ROT DETECTED ON FETCH!
                        replica.status = "CORRUPTED"
                        replica.error_detail = f"On-the-fly bit-rot detected. Got {calc_sha}, expected {target_version.checksum_sha256}"
                        await log_event(
                            db,
                            event_type="REPLICA_CORRUPTED",
                            severity="CRITICAL",
                            message=f"Bit-rot detected during read on {node.id} for object '{key}' (v{target_version.version_num})",
                            node_id=node.id,
                            object_id=obj_entity.id,
                            metadata_json={"calculated_sha": calc_sha, "expected_sha": target_version.checksum_sha256},
                        )

                        # Emit OBJECT_DEGRADED if healthy replicas drop below RF
                        healthy_reps_now = sum(1 for r in replicas if r.status == "HEALTHY" and r.id != replica.id)
                        if healthy_reps_now < bucket.replication_factor:
                            await log_event(
                                db,
                                event_type="OBJECT_DEGRADED",
                                severity="WARNING",
                                message=f"Object '{bucket.name}/{key}' marked DEGRADED ({healthy_reps_now}/{bucket.replication_factor} replicas healthy)",
                                node_id=node.id,
                                object_id=obj_entity.id,
                                metadata_json={"version_id": str(target_version.id), "healthy_replicas": healthy_reps_now, "desired_replicas": bucket.replication_factor},
                            )
                        await db.commit()
                        errors.append(f"{node.id}: bit-rot corrupted data")
                        continue
                else:
                    errors.append(f"{node.id}: HTTP {resp.status_code}")
            except Exception as e:
                errors.append(f"{node.id}: {str(e)}")

    # If all replicas failed
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Unable to read object from any replica. Errors: {'; '.join(errors)}",
    )


async def delete_object_tombstone(
    db: AsyncSession,
    bucket_name: str,
    key: str,
) -> ObjectVersion:
    """
    Creates a deletion tombstone version. Preserves historical versions.
    """
    b_stmt = select(Bucket).where(Bucket.name == bucket_name)
    b_res = await db.execute(b_stmt)
    bucket = b_res.scalar_one_or_none()
    if not bucket:
        raise HTTPException(status_code=404, detail="Bucket not found")

    o_stmt = (
        select(ObjectEntity)
        .where(ObjectEntity.bucket_id == bucket.id, ObjectEntity.key == key)
        .options(selectinload(ObjectEntity.versions))
    )
    o_res = await db.execute(o_stmt)
    obj_entity = o_res.scalar_one_or_none()

    if not obj_entity or obj_entity.is_deleted:
        raise HTTPException(status_code=404, detail="Object not found or already deleted")

    max_v = max([v.version_num for v in obj_entity.versions], default=0)
    tombstone_version = ObjectVersion(
        object_id=obj_entity.id,
        version_num=max_v + 1,
        size_bytes=0,
        content_type="application/octet-stream",
        checksum_sha256="TOMBSTONE_DELETED",
        is_tombstone=True,
        storage_policy=bucket.durability_policy,
    )
    db.add(tombstone_version)
    obj_entity.is_deleted = True

    await log_event(
        db,
        event_type="OBJECT_DELETED",
        severity="WARNING",
        message=f"Object '{bucket.name}/{key}' tombstoned as v{tombstone_version.version_num}",
        object_id=obj_entity.id,
    )

    await db.commit()
    return tombstone_version
