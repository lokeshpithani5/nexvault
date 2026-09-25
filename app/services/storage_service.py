import asyncio
import hashlib
import uuid
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.object_model import Object, ObjectVersion
from app.models.object_replica import ObjectReplica
from app.repositories.bucket_repository import BucketRepository
from app.repositories.object_repository import ObjectRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.event_repository import EventRepository
from app.services.node_client import node_client
from app.services.placement_engine import placement_engine
from app.schemas.storage import (
    BucketCreateRequest,
    BucketResponse,
    PolicyResponse,
    ObjectResponse,
    ObjectDetailResponse,
    ObjectVersionResponse,
    ReplicaResponse,
)
from app.core.exceptions import (
    ResourceNotFoundError,
    PermissionDeniedError,
    ConflictError,
    QuorumNotReachedError,
    DataIntegrityError,
    StorageNodeUnavailableError,
)
from app.core.logging_config import logger


class StorageService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.bucket_repo = BucketRepository(session)
        self.object_repo = ObjectRepository(session)
        self.node_repo = NodeRepository(session)
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
            message=f"Bucket '{bucket.name}' created by {current_user.email} (Policy: {bucket.policy.name if bucket.policy else 'standard'})",
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

    async def upload_object(
        self,
        current_user: User,
        bucket_name: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> ObjectResponse:
        """Upload object with zone-aware placement, physical node writes, checksum validation & versioning."""
        bucket = await self.verify_bucket_access(current_user, bucket_name)

        # 1. Compute SHA-256
        sha256_checksum = hashlib.sha256(data).hexdigest()
        size_bytes = len(data)

        # 2. Find or create logical object
        obj = await self.object_repo.get_by_key(bucket.id, key)
        if not obj:
            obj = await self.object_repo.create_object(bucket.id, key)
        else:
            obj.is_deleted = False

        # 3. Calculate next version number
        version_num = await self.object_repo.get_next_version_num(obj.id)

        # 4. Fetch available nodes and select target placement
        available_nodes = await self.node_repo.get_healthy_available_nodes()
        target_nodes, is_degraded = placement_engine.select_nodes_for_placement(available_nodes, bucket.policy)

        # 5. Concurrently write chunks to target storage nodes
        write_tasks = []
        replica_metadata_list = []

        for node in target_nodes:
            replica_id = str(uuid.uuid4())
            replica_metadata_list.append((node, replica_id))
            write_tasks.append(node_client.put_chunk(node.host, node.port, replica_id, data))

        results = await asyncio.gather(*write_tasks, return_exceptions=True)

        # 6. Verify write quorum
        successful_replicas = []
        for (node, replica_id), res in zip(replica_metadata_list, results):
            if isinstance(res, Exception):
                logger.warning(f"Failed to write replica {replica_id} to node {node.name}: {res}")
            else:
                if res.get("sha256") == sha256_checksum:
                    successful_replicas.append((node, replica_id))
                    node.used_capacity_bytes += size_bytes
                else:
                    logger.error(f"Checksum mismatch reported by node {node.name} for replica {replica_id}")

        avail_mode = getattr(bucket.policy, "availability_mode", "DURABILITY_FIRST")
        min_required = 1 if (avail_mode == "AVAILABILITY_FIRST" and is_degraded) else bucket.policy.min_write_quorum

        if len(successful_replicas) < min_required:
            raise QuorumNotReachedError(
                message=f"Write quorum failed. Required {min_required} (Mode: {avail_mode}), succeeded {len(successful_replicas)}",
                details={"required": min_required, "succeeded": len(successful_replicas), "mode": avail_mode},
            )

        # 7. Record Version & Replicas in Control Plane
        version = await self.object_repo.create_version(
            object_id=obj.id,
            version_num=version_num,
            size_bytes=size_bytes,
            sha256_checksum=sha256_checksum,
            content_type=content_type,
            is_tombstone=False,
        )

        created_replicas = []
        for node, replica_id in successful_replicas:
            rep = ObjectReplica(
                id=replica_id,
                version_id=version.id,
                node_id=node.id,
                chunk_index=0,
                status="HEALTHY",
                stored_checksum=sha256_checksum,
            )
            self.session.add(rep)
            created_replicas.append(rep)

        await self.session.flush()

        # 8. Emit structured event
        node_names = [n.name for n, _ in successful_replicas]
        severity = "WARNING" if is_degraded else "INFO"
        event_type = "WRITE_DEGRADED" if is_degraded else "WRITE_SUCCESS"
        await self.event_repo.log_event(
            event_type=event_type,
            severity=severity,
            category="OBJECT",
            message=f"Object '{key}' v{version_num} written to '{bucket_name}' across {node_names} ({event_type})",
            details_json={
                "bucket": bucket_name,
                "key": key,
                "version": version_num,
                "size": size_bytes,
                "sha256": sha256_checksum,
                "nodes": node_names,
                "is_degraded": is_degraded,
                "availability_mode": avail_mode,
            },
        )
        if is_degraded:
            await self.event_repo.log_event(
                event_type="OBJECT_DEGRADED",
                severity="WARNING",
                category="OBJECT",
                message=f"Object '{key}' in bucket '{bucket_name}' entered DEGRADED state ({len(successful_replicas)}/{bucket.policy.replication_factor} replicas)",
                details_json={"bucket": bucket_name, "key": key, "healthy_replicas": len(successful_replicas), "target_rf": bucket.policy.replication_factor},
            )

        # Build response DTO
        replica_dtos = [
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
            for r in created_replicas
        ]

        version_dto = ObjectVersionResponse(
            id=version.id,
            version_num=version.version_num,
            size_bytes=version.size_bytes,
            sha256_checksum=version.sha256_checksum,
            content_type=version.content_type,
            is_tombstone=version.is_tombstone,
            created_at=version.created_at,
            replicas=replica_dtos,
        )

        return ObjectResponse(
            id=obj.id,
            bucket_id=obj.bucket_id,
            key=obj.key,
            is_deleted=obj.is_deleted,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            current_version=version_dto,
        )

    async def download_object(
        self,
        current_user: User,
        bucket_name: str,
        key: str,
        version_num: Optional[int] = None,
    ) -> Tuple[bytes, str, str, str]:
        """Locates healthy replica, retrieves data from storage node, validates checksum, fails over on error."""
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        obj = await self.object_repo.get_by_key(bucket.id, key)

        if not obj:
            raise ResourceNotFoundError(message=f"Object '{key}' not found in bucket '{bucket_name}'")

        target_version = None
        if version_num is not None:
            for v in obj.versions:
                if v.version_num == version_num:
                    target_version = v
                    break
            if not target_version:
                raise ResourceNotFoundError(message=f"Version {version_num} for object '{key}' not found")
        else:
            if obj.is_deleted:
                raise ResourceNotFoundError(message=f"Object '{key}' has been deleted")
            for v in obj.versions:
                if not v.is_tombstone:
                    target_version = v
                    break
            if not target_version:
                raise ResourceNotFoundError(message=f"No active versions available for '{key}'")

        if target_version.is_tombstone:
            raise ResourceNotFoundError(message=f"Object version {target_version.version_num} is a tombstone")

        eligible_replicas = [
            r for r in target_version.replicas
            if r.status == "HEALTHY" and r.node and r.node.status == "HEALTHY" and not r.node.is_simulated_partitioned
        ]

        if not eligible_replicas:
            eligible_replicas = [r for r in target_version.replicas if r.status != "CORRUPTED" and r.node]

        if not eligible_replicas:
            raise StorageNodeUnavailableError(
                message=f"No healthy replicas reachable for object '{key}'",
                details={"replicas_total": len(target_version.replicas)},
            )

        last_error = None
        for rep in eligible_replicas:
            try:
                data, header_sha256 = await node_client.get_chunk(
                    rep.node.host, rep.node.port, rep.id
                )
                calc_sha256 = hashlib.sha256(data).hexdigest()

                if calc_sha256 != target_version.sha256_checksum:
                    logger.error(
                        f"Bitrot/corruption detected on node {rep.node.name} for replica {rep.id}! "
                        f"Expected {target_version.sha256_checksum}, got {calc_sha256}"
                    )
                    rep.status = "CORRUPTED"
                    await self.session.flush()
                    await self.event_repo.log_event(
                        event_type="READ_FAILOVER",
                        severity="ERROR",
                        category="INTEGRITY",
                        message=f"Data corruption detected during read on replica {rep.id} (node {rep.node.name}) - triggering failover",
                        details_json={"replica_id": rep.id, "node_name": rep.node.name, "expected": target_version.sha256_checksum},
                    )
                    continue

                filename = key.split("/")[-1]
                return data, target_version.content_type, target_version.sha256_checksum, filename

            except Exception as e:
                logger.warning(f"Failed to read from replica {rep.id} on node {rep.node.name}: {e}")
                last_error = e

        raise StorageNodeUnavailableError(
            message=f"All replicas failed to return verified data for '{key}': {last_error}",
            details={"error": str(last_error)},
        )

    async def delete_object(self, current_user: User, bucket_name: str, key: str) -> dict:
        """Tombstone/version-aware deletion preserving complete audit trail."""
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        obj = await self.object_repo.get_by_key(bucket.id, key)

        if not obj or obj.is_deleted:
            raise ResourceNotFoundError(message=f"Object '{key}' not found in bucket '{bucket_name}'")

        next_version_num = await self.object_repo.get_next_version_num(obj.id)

        tombstone = await self.object_repo.create_version(
            object_id=obj.id,
            version_num=next_version_num,
            size_bytes=0,
            sha256_checksum="",
            content_type="",
            is_tombstone=True,
        )

        obj.is_deleted = True
        await self.session.flush()

        await self.event_repo.log_event(
            severity="INFO",
            category="OBJECT",
            message=f"Object '{key}' marked deleted with tombstone v{next_version_num}",
            details_json={"bucket": bucket_name, "key": key, "tombstone_version": next_version_num},
        )

        return {
            "deleted": True,
            "bucket": bucket_name,
            "key": key,
            "tombstone_version": next_version_num,
        }

    async def list_objects(self, current_user: User, bucket_name: str) -> List[ObjectResponse]:
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        objects = await self.object_repo.list_by_bucket(bucket.id, include_deleted=False)
        result = []
        for obj in objects:
            current_v = None
            if obj.versions:
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

    async def get_object_metadata(self, current_user: User, bucket_name: str, key: str) -> ObjectResponse:
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        obj = await self.object_repo.get_by_key(bucket.id, key)
        if not obj or obj.is_deleted:
            raise ResourceNotFoundError(message=f"Object '{key}' not found in bucket '{bucket_name}'")

        active_v = [v for v in obj.versions if not v.is_tombstone]
        if not active_v:
            raise ResourceNotFoundError(message=f"Object '{key}' has been deleted")

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
        version_dto = ObjectVersionResponse(
            id=top.id,
            version_num=top.version_num,
            size_bytes=top.size_bytes,
            sha256_checksum=top.sha256_checksum,
            content_type=top.content_type,
            is_tombstone=top.is_tombstone,
            created_at=top.created_at,
            replicas=replicas_dto,
        )

        return ObjectResponse(
            id=obj.id,
            bucket_id=obj.bucket_id,
            key=obj.key,
            is_deleted=obj.is_deleted,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            current_version=version_dto,
        )

    async def get_object_details(self, current_user: User, bucket_name: str, key: str) -> ObjectDetailResponse:
        bucket = await self.verify_bucket_access(current_user, bucket_name)
        obj = await self.object_repo.get_by_key(bucket.id, key)
        if not obj:
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

        active_versions = [v for v in version_dtos if not v.is_tombstone]
        current_v = active_versions[0] if active_versions else (version_dtos[0] if version_dtos else None)

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

    async def get_object_versions(self, current_user: User, bucket_name: str, key: str) -> List[ObjectVersionResponse]:
        details = await self.get_object_details(current_user, bucket_name, key)
        return details.versions
