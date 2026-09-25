from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.repositories.node_repository import NodeRepository
from app.repositories.repair_repository import RepairRepository
from app.models.object_model import Object
from app.models.object_replica import ObjectReplica
from app.schemas.node import StorageNodeResponse, ClusterStatsResponse


class NodeService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.node_repo = NodeRepository(session)
        self.repair_repo = RepairRepository(session)

    async def list_nodes(self) -> List[StorageNodeResponse]:
        nodes = await self.node_repo.list_all()
        return [StorageNodeResponse.model_validate(n) for n in nodes]

    async def get_cluster_stats(self) -> ClusterStatsResponse:
        nodes = await self.node_repo.list_all()
        total_nodes = len(nodes)
        healthy_nodes = sum(1 for n in nodes if n.status == "HEALTHY" and not n.is_simulated_partitioned)
        degraded_nodes = sum(1 for n in nodes if n.status == "DEGRADED" or n.is_simulated_partitioned)
        failed_nodes = sum(1 for n in nodes if n.status == "FAILED")
        
        total_cap = sum(n.total_capacity_bytes for n in nodes)
        used_cap = sum(n.used_capacity_bytes for n in nodes)
        util_pct = (used_cap / total_cap * 100.0) if total_cap > 0 else 0.0

        # Object count
        obj_count_res = await self.session.execute(select(func.count(Object.id)).where(Object.is_deleted == False))
        total_objects = obj_count_res.scalar() or 0

        # Replica count
        rep_count_res = await self.session.execute(select(func.count(ObjectReplica.id)))
        total_replicas = rep_count_res.scalar() or 0

        active_repairs = await self.repair_repo.count_active()

        return ClusterStatsResponse(
            total_nodes=total_nodes,
            healthy_nodes=healthy_nodes,
            degraded_nodes=degraded_nodes,
            failed_nodes=failed_nodes,
            total_capacity_bytes=total_cap,
            used_capacity_bytes=used_cap,
            utilization_percent=round(util_pct, 2),
            total_objects=total_objects,
            total_replicas=total_replicas,
            active_repair_jobs=active_repairs,
        )
