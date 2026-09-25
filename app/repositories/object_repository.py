from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.models.object_model import Object, ObjectVersion
from app.models.object_replica import ObjectReplica


class ObjectRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_key(self, bucket_id: str, key: str) -> Optional[Object]:
        stmt = (
            select(Object)
            .where(Object.bucket_id == bucket_id, Object.key == key)
            .options(
                selectinload(Object.versions).selectinload(ObjectVersion.replicas).selectinload(ObjectReplica.node)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_id(self, object_id: str) -> Optional[Object]:
        stmt = (
            select(Object)
            .where(Object.id == object_id)
            .options(
                selectinload(Object.versions).selectinload(ObjectVersion.replicas).selectinload(ObjectReplica.node)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_bucket(self, bucket_id: str, include_deleted: bool = False) -> List[Object]:
        stmt = (
            select(Object)
            .where(Object.bucket_id == bucket_id)
            .options(
                selectinload(Object.versions).selectinload(ObjectVersion.replicas).selectinload(ObjectReplica.node)
            )
        )
        if not include_deleted:
            stmt = stmt.where(Object.is_deleted == False)
        stmt = stmt.order_by(Object.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_object(self, bucket_id: str, key: str) -> Object:
        obj = Object(bucket_id=bucket_id, key=key, is_deleted=False)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def get_next_version_num(self, object_id: str) -> int:
        stmt = select(func.max(ObjectVersion.version_num)).where(ObjectVersion.object_id == object_id)
        result = await self.session.execute(stmt)
        max_num = result.scalar()
        return (max_num or 0) + 1

    async def create_version(
        self,
        object_id: str,
        version_num: int,
        size_bytes: int,
        sha256_checksum: str,
        content_type: str = "application/octet-stream",
        is_tombstone: bool = False,
    ) -> ObjectVersion:
        version = ObjectVersion(
            object_id=object_id,
            version_num=version_num,
            size_bytes=size_bytes,
            sha256_checksum=sha256_checksum,
            content_type=content_type,
            is_tombstone=is_tombstone,
        )
        self.session.add(version)
        await self.session.flush()
        return version

    async def create_replica(
        self,
        version_id: str,
        node_id: str,
        chunk_index: int,
        status: str,
        stored_checksum: str,
    ) -> ObjectReplica:
        replica = ObjectReplica(
            version_id=version_id,
            node_id=node_id,
            chunk_index=chunk_index,
            status=status,
            stored_checksum=stored_checksum,
        )
        self.session.add(replica)
        await self.session.flush()
        return replica

    async def get_replica(self, replica_id: str) -> Optional[ObjectReplica]:
        stmt = select(ObjectReplica).where(ObjectReplica.id == replica_id).options(selectinload(ObjectReplica.node))
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def update_replica_status(self, replica_id: str, status: str):
        replica = await self.get_replica(replica_id)
        if replica:
            replica.status = status
            await self.session.flush()
