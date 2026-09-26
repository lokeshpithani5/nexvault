"""
Chaos Engineering Lab API (Admin Only)
Triggers controlled distributed faults:
- Node crash & recovery simulation
- Network partition simulation
- Bit-rot data corruption injection
- On-demand cluster integrity scrubs
- Immediate storage rebalancing
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import httpx

from backend.app.core.database import get_db
from backend.app.core.security import get_current_user, get_current_admin
from backend.app.models.user import User
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectReplica, ObjectVersion, ObjectEntity
from backend.app.services.heartbeat import probe_and_update_cluster
from backend.app.services.repair_engine import run_repair_cycle
from backend.app.services.integrity_scanner import run_cluster_integrity_scan
from backend.app.services.rebalance_engine import run_rebalance_cycle
from backend.app.services.event_logger import log_event

router = APIRouter(prefix="/chaos", tags=["Chaos Lab"])


class NodeStateRequest(BaseModel):
    state: str  # "HEALTHY", "FAILED", "PARTITIONED"


@router.post("/nodes/{node_id}/toggle-status")
async def toggle_node_status(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Toggles node status between HEALTHY and FAILED (Simulates Node Crash/Restore)."""
    n_res = await db.execute(select(StorageNode).where(StorageNode.id == node_id))
    node = n_res.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    target_state = "FAILED" if node.status == "HEALTHY" else "HEALTHY"

    # Send command to physical node daemon
    async with httpx.AsyncClient() as client:
        try:
            await client.post(
                f"http://{node.host}:{node.port}/chaos/set-state",
                json={"state": target_state},
                timeout=3.0,
            )
        except Exception:
            pass

    # Update coordinator state
    node.status = target_state
    if target_state == "FAILED":
        # Mark node's active replicas as MISSING
        rep_stmt = select(ObjectReplica).where(ObjectReplica.node_id == node.id)
        reps = (await db.execute(rep_stmt)).scalars().all()
        for r in reps:
            r.status = "MISSING"

    await log_event(
        db,
        event_type="CHAOS_NODE_TOGGLED",
        severity="WARNING" if target_state == "FAILED" else "INFO",
        message=f"Chaos Lab: Node {node.id} transitioned to {target_state} by {current_user.email}",
        node_id=node.id,
    )
    await db.commit()

    return {"node_id": node.id, "new_status": target_state}


@router.post("/nodes/{node_id}/partition")
async def toggle_network_partition(
    node_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Toggles simulated network partition for a node."""
    n_res = await db.execute(select(StorageNode).where(StorageNode.id == node_id))
    node = n_res.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    node.is_simulated_partitioned = not node.is_simulated_partitioned
    new_partition_state = node.is_simulated_partitioned

    # Inform daemon to reject non-chaos traffic
    async with httpx.AsyncClient() as client:
        try:
            target_daemon_state = "PARTITIONED" if new_partition_state else "HEALTHY"
            await client.post(
                f"http://{node.host}:{node.port}/chaos/set-state",
                json={"state": target_daemon_state},
                timeout=3.0,
            )
        except Exception:
            pass

    await log_event(
        db,
        event_type="CHAOS_PARTITION_TOGGLED",
        severity="WARNING" if new_partition_state else "INFO",
        message=f"Chaos Lab: Network Partition for {node.id} set to {new_partition_state}",
        node_id=node.id,
    )
    await db.commit()

    return {"node_id": node.id, "is_simulated_partitioned": new_partition_state}


@router.post("/replicas/{replica_id}/corrupt")
async def inject_replica_corruption(
    replica_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Simulates Bit-Rot / Media Corruption on a specific replica blob.
    Directly flips bytes in the node's disk file without updating metadata.
    """
    stmt = (
        select(ObjectReplica)
        .where(ObjectReplica.id == replica_id)
        .options(selectinload(ObjectReplica.node))
    )
    res = await db.execute(stmt)
    replica = res.scalar_one_or_none()
    if not replica:
        raise HTTPException(status_code=404, detail="Replica not found")

    node = replica.node
    url = f"http://{node.host}:{node.port}/chaos/corrupt/{replica.blob_id}"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, timeout=5.0)
            if resp.status_code != 200:
                raise Exception(resp.text)
            data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to corrupt chunk on {node.id}: {str(e)}")

    await log_event(
        db,
        event_type="CHAOS_BIT_ROT_INJECTED",
        severity="CRITICAL",
        message=f"Chaos Lab: Injected silent bit-rot into replica {replica.blob_id} on {node.id}",
        node_id=node.id,
        metadata_json=data,
    )
    await db.commit()

    return {
        "status": "CORRUPTED",
        "replica_id": replica.id,
        "blob_id": replica.blob_id,
        "node_id": node.id,
        "corrupted_sha256": data.get("new_corrupted_sha256"),
        "message": "Bit-rot injected. Run an Integrity Scan or download the object to observe self-healing.",
    }


@router.post("/scans/integrity")
async def trigger_manual_integrity_scan(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Triggers an immediate cluster-wide cryptographic SHA-256 integrity verification."""
    result = await run_cluster_integrity_scan(db)
    return result


@router.post("/repair/trigger")
async def trigger_manual_repair(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Triggers an immediate self-healing replica repair cycle."""
    result = await run_repair_cycle(db)
    return result


@router.post("/rebalance/trigger")
async def trigger_manual_rebalance(
    force: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Triggers storage rebalancing migration."""
    result = await run_rebalance_cycle(db, force=force)
    return result


class ResetDemoRequest(BaseModel):
    clean_test_objects: bool = False
    trigger_scrub: bool = True


@router.post("/reset")
async def reset_demo_cluster(
    req: Optional[ResetDemoRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """
    Demo Reset Capability (Admin Only):
    Safely returns the NEXVAULT cluster to a clean, known healthy state:
    1. Un-partitions and restores all physical node daemons.
    2. Resets node statuses to HEALTHY in the control plane DB.
    3. Clears transient replica error states.
    4. Optionally runs an immediate integrity scan & auto-repair cycle.
    5. Optionally cleans test/demo temporary objects if explicitly requested.
    """
    params = req or ResetDemoRequest()
    n_res = await db.execute(select(StorageNode))
    nodes = n_res.scalars().all()

    # 1. Reset physical node daemons
    async with httpx.AsyncClient() as client:
        for node in nodes:
            try:
                await client.post(
                    f"http://{node.host}:{node.port}/chaos/set-state",
                    json={"state": "HEALTHY"},
                    timeout=2.0,
                )
            except Exception:
                pass
            node.status = "HEALTHY"
            node.is_simulated_partitioned = False

    # 2. Reset replica statuses and prune excess copies to preserve configured RF
    v_res = await db.execute(
        select(ObjectVersion).options(
            selectinload(ObjectVersion.replicas),
            selectinload(ObjectVersion.object_entity).selectinload(ObjectEntity.bucket),
        )
    )
    for v in v_res.scalars().all():
        rf = v.object_entity.bucket.replication_factor if (v.object_entity and v.object_entity.bucket) else 3
        healthy_reps = [r for r in v.replicas if r.status == "HEALTHY"]
        if len(healthy_reps) > rf:
            for excess in healthy_reps[rf:]:
                excess.status = "TOMBSTONE"
        elif len(healthy_reps) < rf:
            for r in v.replicas:
                if r.status in ("MISSING", "CORRUPTED"):
                    r.status = "HEALTHY"
                    r.error_detail = None

    # 3. Clean test objects if requested (only temporary demo objects, never user data)
    objects_cleaned = 0
    if params.clean_test_objects:
        del_stmt = select(ObjectEntity).where(
            ObjectEntity.key.like("demo/test_%") | ObjectEntity.key.like("test_%")
        )
        test_objs = (await db.execute(del_stmt)).scalars().all()
        for obj in test_objs:
            await db.delete(obj)
            objects_cleaned += 1

    await db.commit()

    # 4. Optional scrub & auto-repair
    scan_result = None
    repair_result = None
    if params.trigger_scrub:
        scan_result = await run_cluster_integrity_scan(db)
        repair_result = await run_repair_cycle(db)

    await log_event(
        db,
        event_type="DEMO_RESET_EXECUTED",
        severity="INFO",
        message=f"Demo cluster reset executed by {current_user.email}. Nodes reset: {len(nodes)}. Test objects cleaned: {objects_cleaned}.",
        metadata_json={
            "nodes_reset": len(nodes),
            "objects_cleaned": objects_cleaned,
            "scan_result": scan_result,
            "repair_result": repair_result,
        },
    )
    await db.commit()

    return {
        "status": "RESET_COMPLETE",
        "nodes_reset": len(nodes),
        "partitions_cleared": len(nodes),
        "objects_cleaned": objects_cleaned,
        "scan_result": scan_result,
        "repair_result": repair_result,
        "message": "NEXVAULT cluster successfully restored to clean healthy operational state.",
    }
