"""
Heartbeat & Node State Transition Monitor
Continuously probes storage nodes on ports 5001-5006.
Transitions nodes between HEALTHY, DEGRADED, FAILED, and RECOVERING.
Marks impacted replicas and triggers repair triggers.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from backend.app.models.node import StorageNode
from backend.app.models.bucket import Bucket
from backend.app.models.object import ObjectEntity, ObjectVersion, ObjectReplica
from backend.app.services.event_logger import log_event


async def probe_single_node(node: StorageNode, timeout: float = 2.0) -> Dict[str, Any]:
    url = f"http://{node.host}:{node.port}/health"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                reported_state = data.get("status", "HEALTHY")
                if reported_state == "FAILED":
                    return {"reachable": False, "reason": "Node self-reported FAILED state", "data": data}
                elif reported_state == "PARTITIONED":
                    return {"reachable": False, "reason": "Node partitioned", "data": data}
                return {"reachable": True, "data": data}
            return {"reachable": False, "reason": f"HTTP status {resp.status_code}"}
    except Exception as e:
        return {"reachable": False, "reason": str(e)}


async def probe_and_update_cluster(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Executes a health check cycle across all storage nodes.
    Updates DB states and emits structured failure/recovery events.
    """
    stmt = select(StorageNode)
    res = await db.execute(stmt)
    nodes = res.scalars().all()

    probe_results = []
    now = datetime.now(timezone.utc)

    for node in nodes:
        # If node is administratively simulated partitioned, coordinator considers it unreachable
        if node.is_simulated_partitioned:
            probe_res = {"reachable": False, "reason": "Simulated Network Partition active"}
        else:
            probe_res = await probe_single_node(node)

        prev_status = node.status
        is_up = probe_res["reachable"]

        if is_up:
            data = probe_res.get("data", {})
            node.last_heartbeat_at = now
            node.used_bytes = data.get("used_bytes", node.used_bytes)
            node.capacity_bytes = data.get("capacity_bytes", node.capacity_bytes)

            if prev_status == "FAILED":
                node.status = "RECOVERING"
                await log_event(
                    db,
                    event_type="NODE_RECOVERING",
                    severity="INFO",
                    message=f"Storage node {node.id} is back online, transitioning to RECOVERING.",
                    node_id=node.id,
                )
            elif prev_status == "RECOVERING":
                node.status = "HEALTHY"
                await log_event(
                    db,
                    event_type="NODE_HEALTHY",
                    severity="INFO",
                    message=f"Storage node {node.id} fully recovered and HEALTHY.",
                    node_id=node.id,
                )
                await log_event(
                    db,
                    event_type="NODE_RECOVERED",
                    severity="INFO",
                    message=f"Storage node {node.id} fully recovered and HEALTHY.",
                    node_id=node.id,
                )
            else:
                node.status = "HEALTHY"

        else:
            # Node is unreachable or failed
            reason = probe_res.get("reason", "Unknown error")
            if prev_status == "HEALTHY":
                node.status = "DEGRADED"
                await log_event(
                    db,
                    event_type="NODE_HEARTBEAT_LOST",
                    severity="WARNING",
                    message=f"Heartbeat lost for storage node {node.id} ({node.zone}, Port {node.port}): {reason}",
                    node_id=node.id,
                )
            elif prev_status in ("DEGRADED", "RECOVERING"):
                node.status = "FAILED"
                await log_event(
                    db,
                    event_type="NODE_FAILED",
                    severity="ERROR",
                    message=f"Storage node {node.id} marked FAILED after missing consecutive heartbeats.",
                    node_id=node.id,
                )

                # Mark active replicas on this failed node as MISSING
                rep_stmt = (
                    update(ObjectReplica)
                    .where(ObjectReplica.node_id == node.id, ObjectReplica.status == "HEALTHY")
                    .values(status="MISSING", error_detail=f"Node {node.id} failed")
                )
                await db.execute(rep_stmt)

                # Query affected object versions to emit OBJECT_DEGRADED events
                affected_stmt = (
                    select(ObjectVersion)
                    .join(ObjectReplica, ObjectReplica.version_id == ObjectVersion.id)
                    .where(ObjectReplica.node_id == node.id, ObjectVersion.is_tombstone == False)
                    .options(
                        selectinload(ObjectVersion.replicas),
                        selectinload(ObjectVersion.object_entity).selectinload(ObjectEntity.bucket),
                    )
                    .distinct()
                )
                aff_res = await db.execute(affected_stmt)
                for aff_v in aff_res.scalars().all():
                    bucket = aff_v.object_entity.bucket if aff_v.object_entity else None
                    rf = bucket.replication_factor if bucket else 3
                    healthy_count = sum(1 for r in aff_v.replicas if r.node_id != node.id and r.status == "HEALTHY")
                    if healthy_count < rf:
                        obj_name = aff_v.object_entity.key if aff_v.object_entity else str(aff_v.object_id)
                        await log_event(
                            db,
                            event_type="OBJECT_DEGRADED",
                            severity="WARNING",
                            message=f"Object '{bucket.name if bucket else 'default'}/{obj_name}' marked DEGRADED ({healthy_count}/{rf} replicas online)",
                            object_id=aff_v.object_id,
                            node_id=node.id,
                            metadata_json={
                                "version_id": str(aff_v.id),
                                "healthy_replicas": healthy_count,
                                "desired_replicas": rf,
                            },
                        )

        probe_results.append({
            "node_id": node.id,
            "port": node.port,
            "zone": node.zone,
            "status": node.status,
            "reachable": is_up,
        })

    await db.commit()
    return probe_results
