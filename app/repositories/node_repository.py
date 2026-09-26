from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.storage_node import StorageNode


class NodeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> List[StorageNode]:
        stmt = select(StorageNode).order_by(StorageNode.port.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, node_id: str) -> Optional[StorageNode]:
        stmt = select(StorageNode).where(StorageNode.id == node_id)
        result = await self.session.execute(stmt)
        node = result.scalars().first()
        if node:
            return node
        if str(node_id).isdigit():
            idx = int(node_id)
            port = 5000 + idx if idx < 100 else idx
            node = await self.get_by_port(port)
            if node:
                return node
        stmt = select(StorageNode).where(StorageNode.name == str(node_id))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_port(self, port: int) -> Optional[StorageNode]:
        stmt = select(StorageNode).where(StorageNode.port == port)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def register_or_update(
        self,
        name: str,
        port: int,
        zone: str,
        host: str = "127.0.0.1",
        total_capacity_bytes: int = 10737418240,
    ) -> StorageNode:
        existing = await self.get_by_port(port)
        if existing:
            existing.name = name
            existing.zone = zone
            existing.host = host
            existing.total_capacity_bytes = total_capacity_bytes
            existing.last_heartbeat = datetime.now(timezone.utc)
            await self.session.flush()
            return existing

        node = StorageNode(
            name=name,
            port=port,
            zone=zone,
            host=host,
            total_capacity_bytes=total_capacity_bytes,
            status="HEALTHY",
            is_simulated_partitioned=False,
            last_heartbeat=datetime.now(timezone.utc),
        )
        self.session.add(node)
        await self.session.flush()
        return node

    async def update_status(self, node_id: str, status: str) -> Optional[StorageNode]:
        node = await self.get_by_id(node_id)
        if node:
            node.status = status
            node.last_heartbeat = datetime.now(timezone.utc)
            await self.session.flush()
        return node

    async def set_partition_state(self, node_ids: List[str], partitioned: bool):
        stmt = (
            update(StorageNode)
            .where(StorageNode.id.in_(node_ids))
            .values(is_simulated_partitioned=partitioned)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def get_healthy_available_nodes(self) -> List[StorageNode]:
        stmt = (
            select(StorageNode)
            .where(
                StorageNode.status == "HEALTHY",
                StorageNode.is_simulated_partitioned == False,
            )
            .order_by(StorageNode.used_capacity_bytes.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
