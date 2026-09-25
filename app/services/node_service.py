from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.node_repository import NodeRepository
from app.repositories.event_repository import EventRepository
from app.repositories.repair_repository import RepairRepository
from app.models.storage_node import StorageNode
from app.models.object_model import Object
from app.models.object_replica import ObjectReplica
from app.services.node_client import node_client
from app.schemas.node import StorageNodeResponse, ClusterStatsResponse
from app.core.exceptions import ResourceNotFoundError
from app.core.logging_config import logger


class NodeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.node_repo = NodeRepository(session)
        self.event_repo = EventRepository(session)
        self.repair_repo = RepairRepository(session)

    async def list_nodes(self) -> List[StorageNodeResponse]:
        nodes = await self.node_repo.list_all()
        return [StorageNodeResponse.model_validate(n) for n in nodes]

    async def get_node_by_id(self, node_id: str) -> StorageNode:
        node = await self.node_repo.get_by_id(node_id)
        if not node:
            raise ResourceNotFoundError(message=f"Node '{node_id}' not found")
        return node

    async def get_node_health(self, node_id: str) -> Dict[str, Any]:
        node = await self.get_node_by_id(node_id)
        daemon_health = await node_client.check_health(node.host, node.port)
        
        is_reachable = daemon_health is not None
        status = "HEALTHY" if is_reachable and not node.is_simulated_partitioned else "UNREACHABLE"
        if node.is_simulated_partitioned:
            status = "PARTITIONED"

        return {
            "node_id": node.id,
            "name": node.name,
            "host": node.host,
            "port": node.port,
            "zone": node.zone,
            "control_plane_status": node.status,
            "realtime_status": status,
            "is_reachable": is_reachable,
            "is_simulated_partitioned": node.is_simulated_partitioned,
            "total_capacity_bytes": node.total_capacity_bytes,
            "used_capacity_bytes": daemon_health.get("used_bytes", node.used_capacity_bytes) if daemon_health else node.used_capacity_bytes,
            "free_capacity_bytes": daemon_health.get("free_bytes", node.total_capacity_bytes - node.used_capacity_bytes) if daemon_health else 0,
            "chunks_count": daemon_health.get("chunks_count", 0) if daemon_health else 0,
            "last_heartbeat": node.last_heartbeat,
        }

    async def get_cluster_health(self) -> Dict[str, Any]:
        nodes = await self.node_repo.list_all()
        total_nodes = len(nodes)
        healthy = sum(1 for n in nodes if n.status == "HEALTHY" and not n.is_simulated_partitioned)
        degraded = sum(1 for n in nodes if n.status == "DEGRADED" or n.is_simulated_partitioned)
        failed = sum(1 for n in nodes if n.status == "FAILED")

        total_cap = sum(n.total_capacity_bytes for n in nodes)
        used_cap = sum(n.used_capacity_bytes for n in nodes)
        util_pct = (used_cap / total_cap * 100.0) if total_cap > 0 else 0.0

        zone_breakdown = {
            "Zone-A": {
                "nodes": [n.name for n in nodes if n.zone == "Zone-A"],
                "healthy": sum(1 for n in nodes if n.zone == "Zone-A" and n.status == "HEALTHY" and not n.is_simulated_partitioned),
                "total": sum(1 for n in nodes if n.zone == "Zone-A"),
            },
            "Zone-B": {
                "nodes": [n.name for n in nodes if n.zone == "Zone-B"],
                "healthy": sum(1 for n in nodes if n.zone == "Zone-B" and n.status == "HEALTHY" and not n.is_simulated_partitioned),
                "total": sum(1 for n in nodes if n.zone == "Zone-B"),
            },
        }

        cluster_status = "HEALTHY"
        if failed > 0:
            cluster_status = "DEGRADED" if healthy >= 3 else "CRITICAL"

        return {
            "cluster_status": cluster_status,
            "total_nodes": total_nodes,
            "healthy_nodes": healthy,
            "degraded_nodes": degraded,
            "failed_nodes": failed,
            "total_capacity_bytes": total_cap,
            "used_capacity_bytes": used_cap,
            "utilization_percent": round(util_pct, 2),
            "zones": zone_breakdown,
        }

    async def check_and_update_node_heartbeats(self) -> List[Dict[str, Any]]:
        """Active health monitor sweep checking physical node responses and emitting events on state transitions."""
        nodes = await self.node_repo.list_all()
        events_emitted = []

        for node in nodes:
            old_status = node.status
            daemon_health = await node_client.check_health(node.host, node.port)

            if daemon_health is not None and not node.is_simulated_partitioned:
                # Node is responding
                node.last_heartbeat = datetime.now(timezone.utc)
                node.used_capacity_bytes = daemon_health.get("used_bytes", node.used_capacity_bytes)

                if old_status in ["FAILED", "DEGRADED"]:
                    node.status = "HEALTHY"
                    event = await self.event_repo.log_event(
                        severity="INFO",
                        category="NODE",
                        message=f"Node {node.name} (Port {node.port}, {node.zone}) heartbeat restored. Status: {old_status} -> HEALTHY",
                        details_json={"node_id": node.id, "node_name": node.name, "old_status": old_status, "new_status": "HEALTHY"},
                    )
                    events_emitted.append({"node": node.name, "event": "RESTORED", "status": "HEALTHY"})
            else:
                # Node is not responding or is partitioned
                new_status = "DEGRADED" if node.is_simulated_partitioned else "FAILED"
                if old_status != new_status:
                    node.status = new_status
                    severity = "WARNING" if node.is_simulated_partitioned else "CRITICAL"
                    reason = "simulated network partition" if node.is_simulated_partitioned else "connection timeout / process down"
                    event = await self.event_repo.log_event(
                        severity=severity,
                        category="NODE",
                        message=f"Node {node.name} (Port {node.port}, {node.zone}) heartbeat lost ({reason}). Status: {old_status} -> {new_status}",
                        details_json={"node_id": node.id, "node_name": node.name, "old_status": old_status, "new_status": new_status, "reason": reason},
                    )
                    events_emitted.append({"node": node.name, "event": "FAILED", "status": new_status})

        await self.session.flush()
        return events_emitted
