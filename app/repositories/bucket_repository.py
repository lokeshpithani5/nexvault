from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.bucket import Bucket
from app.models.policy import Policy


class BucketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, bucket_id: str) -> Optional[Bucket]:
        stmt = (
            select(Bucket)
            .where(Bucket.id == bucket_id, Bucket.is_deleted == False)
            .options(selectinload(Bucket.policy), selectinload(Bucket.objects))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_name(self, name: str) -> Optional[Bucket]:
        stmt = (
            select(Bucket)
            .where(Bucket.name == name, Bucket.is_deleted == False)
            .options(selectinload(Bucket.policy), selectinload(Bucket.objects))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_owner(self, owner_id: str) -> List[Bucket]:
        stmt = (
            select(Bucket)
            .where(Bucket.owner_id == owner_id, Bucket.is_deleted == False)
            .options(selectinload(Bucket.policy), selectinload(Bucket.objects))
            .order_by(Bucket.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> List[Bucket]:
        stmt = (
            select(Bucket)
            .where(Bucket.is_deleted == False)
            .options(selectinload(Bucket.policy), selectinload(Bucket.objects))
            .order_by(Bucket.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, name: str, owner_id: str, policy_id: str) -> Bucket:
        bucket = Bucket(
            name=name,
            owner_id=owner_id,
            policy_id=policy_id,
            is_deleted=False,
        )
        self.session.add(bucket)
        await self.session.flush()
        return bucket

    async def get_default_policy(self) -> Optional[Policy]:
        stmt = select(Policy).where(Policy.name == "standard-rf3")
        result = await self.session.execute(stmt)
        policy = result.scalars().first()
        if not policy:
            stmt = select(Policy).limit(1)
            result = await self.session.execute(stmt)
            policy = result.scalars().first()
        return policy

    async def get_policy_by_id(self, policy_id: str) -> Optional[Policy]:
        stmt = select(Policy).where(Policy.id == policy_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_policies(self) -> List[Policy]:
        stmt = select(Policy)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
