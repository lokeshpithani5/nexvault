from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.bucket_repository import BucketRepository
from app.repositories.object_repository import ObjectRepository
from app.repositories.event_repository import EventRepository
from app.schemas.storage import (
    BucketCreateRequest,
    BucketResponse,
    PolicyResponse,
    ObjectResponse,
    ObjectDetailResponse,
    ObjectVersionResponse,
    ReplicaResponse,
)
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError, ConflictError


class StorageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bucket_repo = BucketRepository(session)
        self.object_repo = ObjectRepository(session)
        self.event_repo = EventRepository(session)

    async def list_policies(self) -> List[PolicyResponse]:
        policies = await self.bucket_repo.list_policies()
        return [PolicyResponse.model_validate(p) for p in policies]

    async def create_bucket(self, current_user: User, bucket_in: BucketCreateRequest) -> BucketResponse:
        existing = await self.bucket_repo.get_by_name(bucket_in.name)
        if existing:
            raise ConflictError(message=f"Bucket with name '{bucket_in.name}' already exists")

        policy_id = bucket_in.policy_id
        if not policy_id:
            default_pol = await self.bucket_repo.get_default_policy()
            if not default_pol:
                raise ResourceNotFoundError(message="No default durability policy configured")
            policy_id = default_pol.id
        else:
            pol = await self.bucket_repo.get_policy_by_id(policy_id)
            if not pol:
                raise ResourceNotFoundError(message=f"Policy with id '{policy_id}' not found")

        bucket = await self.bucket_repo.create(
            name=bucket_in.name,
            owner_id=current_user.id,
            policy_id=policy_id,
        )
        await self.event_repo.log_event(
            severity="INFO",
            category="OBJECT",
            message=f"Bucket '{bucket.name}' created by {current_user.email}",
            details_json={"bucket_id": bucket.id, "owner_id": current_user.id, "policy_id": policy_id},
        )
        return BucketResponse(
            id=bucket.id,
            name=bucket.name,
            owner_id=bucket.owner_id,
            policy_id=bucket.policy_id,
            created_at=bucket.created_at,
            policy=PolicyResponse.model_validate(bucket.policy) if bucket.policy else None,
            object_count=0,
            total_size_bytes=0,
        )

    async def list_user_buckets(self, current_user: User) -> List[BucketResponse]:
        if current_user.role == "ADMIN":
            buckets = await self.bucket_repo.list_all()
        else:
            buckets = await self.bucket_repo.list_by_owner(current_user.id)

        responses = []
        for b in buckets:
            obj_count = len(b.objects) if b.objects else 0
            responses.append(
                BucketResponse(
                    id=b.id,
                    name=b.name,
                    owner_id=b.owner_id,
                    policy_id=b.policy_id,
                    created_at=b.created_at,
                    policy=PolicyResponse.model_validate(b.policy) if b.policy else None,
                    object_count=obj_count,
                    total_size_bytes=0,
                )
            )
        return responses

    async def verify_bucket_access(self, current_user: User, bucket_name: str):
        bucket = await self.bucket_repo.get_by_name(bucket_name)
        if not bucket:
            raise ResourceNotFoundError(message=f"Bucket '{bucket_name}' not found")
        if current_user.role != "ADMIN" and bucket.owner_id != current_user.id:
            raise PermissionDeniedError(message="You do not have permission to access objects in this bucket")
        return bucket

    async def list_objects(self, current_user: User, bucket_name: str) -> List[ObjectResponse]:
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        objects = await self.object_repo.list_by_bucket(bucket.id, include_deleted=False)
        result = []
        for obj in objects:
            current_v = None
            if obj.versions:
                # pick highest version that is not a tombstone
                active_v = [v for v in obj.versions if not v.is_tombstone]
                if active_v:
                    top = active_v[0]
                    replicas_dto = [
                        ReplicaResponse(
                            id=r.id,
                            version_id=r.version_id,
                            node_id=r.node_id,
                            node_name=r.node.name if r.node else None,
                            node_port=r.node.port if r.node else None,
                            node_zone=r.node.zone if r.node else None,
                            chunk_index=r.chunk_index,
                            status=r.status,
                            stored_checksum=r.stored_checksum,
                            last_verified_at=r.last_verified_at,
                        )
                        for r in top.replicas
                    ]
                    current_v = ObjectVersionResponse(
                        id=top.id,
                        version_num=top.version_num,
                        size_bytes=top.size_bytes,
                        sha256_checksum=top.sha256_checksum,
                        content_type=top.content_type,
                        is_tombstone=top.is_tombstone,
                        created_at=top.created_at,
                        replicas=replicas_dto,
                    )
            result.append(
                ObjectResponse(
                    id=obj.id,
                    bucket_id=obj.bucket_id,
                    key=obj.key,
                    is_deleted=obj.is_deleted,
                    created_at=obj.created_at,
                    updated_at=obj.updated_at,
                    current_version=current_v,
                )
            )
        return result

    async def get_object_details(self, current_user: User, bucket_name: str, key: str) -> ObjectDetailResponse:
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        obj = await self.object_repo.get_by_key(bucket.id, key)
        if not obj or obj.is_deleted:
            raise ResourceNotFoundError(message=f"Object '{key}' not found in bucket '{bucket_name}'")

        version_dtos = []
        for v in obj.versions:
            replicas_dto = [
                ReplicaResponse(
                    id=r.id,
                    version_id=r.version_id,
                    node_id=r.node_id,
                    node_name=r.node.name if r.node else None,
                    node_port=r.node.port if r.node else None,
                    node_zone=r.node.zone if r.node else None,
                    chunk_index=r.chunk_index,
                    status=r.status,
                    stored_checksum=r.stored_checksum,
                    last_verified_at=r.last_verified_at,
                )
                for r in v.replicas
            ]
            version_dtos.append(
                ObjectVersionResponse(
                    id=v.id,
                    version_num=v.version_num,
                    size_bytes=v.size_bytes,
                    sha256_checksum=v.sha256_checksum,
                    content_type=v.content_type,
                    is_tombstone=v.is_tombstone,
                    created_at=v.created_at,
                    replicas=replicas_dto,
                )
            )

        current_v = version_dtos[0] if version_dtos else None
        return ObjectDetailResponse(
            id=obj.id,
            bucket_id=bucket.id,
            bucket_name=bucket.name,
            key=obj.key,
            is_deleted=obj.is_deleted,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            policy=PolicyResponse.model_validate(bucket.policy),
            current_version=current_v,
            versions=version_dtos,
        )
