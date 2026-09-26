"""
Integrity Verification Scrubber & Bit-Rot Self-Healing Service
Deep-scrubs chunks across all storage nodes.
Compares calculated_checksum with stored_checksum.
Flags silent bit-rot and triggers automated reconstruction from healthy replicas.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
import hashlib
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectReplica, ObjectVersion
from backend.app.services.repair_engine import run_repair_cycle
from backend.app.services.event_logger import log_event


async def verify_replica_on_node(
    client: httpx.AsyncClient,
    replica: ObjectReplica,
    node: StorageNode,
) -> Dict[str, Any]:
    """
    Queries node HEAD or GET to retrieve on-disk SHA-256 and compares against stored_checksum.
    """
    url = f"http://{node.host}:{node.port}/chunks/{replica.blob_id}"
    try:
        # Request HEAD which calculates on-disk sha256
        resp = await client.head(url, timeout=3.0)
        if resp.status_code == 200:
            on_disk_sha = resp.headers.get("x-content-sha256")
            if on_disk_sha == replica.stored_checksum:
                return {"healthy": True, "calculated_sha": on_disk_sha}
            else:
                return {
                    "healthy": False,
                    "reason": f"Bit-Rot detected: on-disk {on_disk_sha} != stored {replica.stored_checksum}",
                    "calculated_sha": on_disk_sha,
                }
        elif resp.status_code == 404:
            return {"healthy": False, "reason": "Blob missing on disk"}
        else:
            return {"healthy": False, "reason": f"HTTP status {resp.status_code}"}
    except Exception as e:
        return {"healthy": False, "reason": f"Node communication error: {str(e)}"}


async def run_cluster_integrity_scan(db: AsyncSession) -> Dict[str, Any]:
    """
    Audits all replicas across the cluster.
    If corruption is detected:
      1. Marks replica CORRUPTED
      2. Logs CRITICAL event
      3. Automatically invokes repair engine to heal the degraded object
    """
    # 1. Fetch nodes dictionary
    nodes_res = await db.execute(select(StorageNode))
    nodes_dict = {n.id: n for n in nodes_res.scalars().all()}

    # 2. Fetch all active replicas with their version
    stmt = (
        select(ObjectReplica)
        .options(selectinload(ObjectReplica.version))
    )
    rep_res = await db.execute(stmt)
    replicas = rep_res.scalars().all()

    replicas_checked = 0
    corrupted_count = 0
    missing_count = 0
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient() as client:
        for replica in replicas:
            node = nodes_dict.get(replica.node_id)
            if not node or node.status == "FAILED" or node.is_simulated_partitioned:
                continue

            replicas_checked += 1
            check_res = await verify_replica_on_node(client, replica, node)

            if check_res["healthy"]:
                if replica.status != "HEALTHY":
                    replica.status = "HEALTHY"
                    replica.error_detail = None
                replica.last_verified_at = now
            else:
                reason = check_res.get("reason", "Verification failed")
                if "Bit-Rot" in reason:
                    replica.status = "CORRUPTED"
                    replica.error_detail = reason
                    corrupted_count += 1
                    await log_event(
                        db,
                        event_type="REPLICA_CORRUPTED",
                        severity="CRITICAL",
                        message=f"Integrity Scrubber detected Bit-Rot on {node.id} for chunk '{replica.blob_id}': {reason}",
                        node_id=node.id,
                        object_id=replica.version.object_id if replica.version else None,
                        metadata_json={
                            "blob_id": replica.blob_id,
                            "stored_sha": replica.stored_checksum,
                            "calculated_sha": check_res.get("calculated_sha"),
                        },
                    )
                else:
                    replica.status = "MISSING"
                    replica.error_detail = reason
                    missing_count += 1

    await db.commit()

    # 3. Trigger Auto-Heal if any corruptions or missing replicas were identified
    repaired_count = 0
    bytes_restored = 0
    if corrupted_count > 0 or missing_count > 0:
        repair_res = await run_repair_cycle(db)
        repaired_count = repair_res.get("completed_repairs", 0)
        bytes_restored = repair_res.get("bytes_recovered", 0)

    summary = {
        "replicas_checked": replicas_checked,
        "corrupted_count": corrupted_count,
        "missing_count": missing_count,
        "repaired_count": repaired_count,
        "bytes_restored": bytes_restored,
        "timestamp": now.isoformat(),
    }

    await log_event(
        db,
        event_type="INTEGRITY_SCAN_COMPLETED",
        severity="INFO" if corrupted_count == 0 else "WARNING",
        message=f"Integrity scrubber scanned {replicas_checked} replicas. Found {corrupted_count} corrupted, {missing_count} missing. Repaired {repaired_count} replicas.",
        metadata_json=summary,
    )
    await db.commit()
    return summary
