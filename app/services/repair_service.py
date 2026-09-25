from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.repair_job import RepairJob
from app.models.object_replica import ObjectReplica
from app.models.object_model import Object, ObjectVersion
from app.models.storage_node import StorageNode
from app.models.bucket import Bucket
from app.repositories.repair_repository import RepairRepository
from app.repositories.event_repository import EventRepository
from app.repositories.node_repository import NodeRepository
from app.repositories.object_repository import ObjectRepository
from app.services.node_client import node_client
from app.core.exceptions import ResourceNotFoundError, StorageNodeUnavailableError
from app.core.logging_config import logger


class RepairService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repair_repo = RepairRepository(session)
        self.event_repo = EventRepository(session)
        self.node_repo = NodeRepository(session)
        self.object_repo = ObjectRepository(session)

    async def create_repair_job(
        self,
        version_id: str,
        target_node_id: str,
        source_node_id: Optional[str] = None,
        trigger_reason: str = "BITROT_DETECTED",
    ) -> RepairJob:
        """Creates a pending repair job and logs REPAIR_CREATED event."""
        job = await self.repair_repo.create_job(
            version_id=version_id,
            target_node_id=target_node_id,
            source_node_id=source_node_id,
            trigger_reason=trigger_reason,
        )

        await self.event_repo.log_event(
            event_type="REPAIR_CREATED",
            severity="INFO",
            category="REPAIR",
            message=f"Repair job {job.id} created for version {version_id} (Reason: {trigger_reason})",
            details_json={
                "job_id": job.id,
                "version_id": version_id,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "trigger_reason": trigger_reason,
            },
        )
        await self.session.flush()
        return job

    async def execute_repair(self, job_id: str) -> Dict[str, Any]:
        """Executes a repair job: reads healthy source, verifies checksum, rebuilds replica, and restores object health."""
        job_stmt = (
            select(RepairJob)
            .where(RepairJob.id == job_id)
            .options(
                selectinload(RepairJob.version).selectinload(ObjectVersion.replicas).selectinload(ObjectReplica.node),
                selectinload(RepairJob.version).selectinload(ObjectVersion.object).selectinload(Object.bucket).selectinload(Bucket.policy),
                selectinload(RepairJob.source_node),
                selectinload(RepairJob.target_node),
            )
        )
        res = await self.session.execute(job_stmt)
        job = res.scalars().first()
        if not job:
            raise ResourceNotFoundError(message=f"Repair job '{job_id}' not found")

        job.status = "IN_PROGRESS"
        job.started_at = datetime.now(timezone.utc)
        await self.session.flush()

        await self.event_repo.log_event(
            event_type="REPAIR_STARTED",
            severity="INFO",
            category="REPAIR",
            message=f"Repair job {job.id} started execution for version {job.version_id}",
            details_json={"job_id": job.id, "version_id": job.version_id, "target_node_id": job.target_node_id},
        )

        version = job.version
        if not version:
            job.status = "FAILED"
            job.error_message = "ObjectVersion not found"
            job.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            return {"job_id": job.id, "status": "FAILED", "error": job.error_message}

        # 1. Identify healthy source replica to copy from
        source_replica = None
        for r in version.replicas:
            if r.status == "HEALTHY" and r.node and r.node.status == "HEALTHY" and not r.node.is_simulated_partitioned:
                source_replica = r
                break

        if not source_replica:
            job.status = "FAILED"
            job.error_message = "No healthy source replica available for reconstruction"
            job.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            return {"job_id": job.id, "status": "FAILED", "error": job.error_message}

        # 2. Read data from source node
        try:
            chunk_data, _ = await node_client.get_chunk(
                source_replica.node.host,
                source_replica.node.port,
                source_replica.id,
            )
        except Exception as e:
            job.status = "FAILED"
            job.error_message = f"Failed to read from source replica {source_replica.id}: {e}"
            job.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            return {"job_id": job.id, "status": "FAILED", "error": job.error_message}

        # 3. Verify SHA-256 checksum
        computed_sha = hashlib.sha256(chunk_data).hexdigest()
        if computed_sha != version.sha256_checksum:
            job.status = "FAILED"
            job.error_message = f"Checksum mismatch during repair: {computed_sha} != {version.sha256_checksum}"
            job.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            return {"job_id": job.id, "status": "FAILED", "error": job.error_message}

        await self.event_repo.log_event(
            event_type="CHECKSUM_VERIFIED",
            severity="INFO",
            category="INTEGRITY",
            message=f"SHA-256 checksum verified for version {version.id} ({computed_sha[:12]}...)",
            details_json={"version_id": version.id, "checksum": computed_sha, "bytes": len(chunk_data)},
        )

        # 4. Target node
        target_node = job.target_node or await self.node_repo.get_by_id(job.target_node_id)
        if not target_node:
            job.status = "FAILED"
            job.error_message = "Target storage node not found"
            job.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            return {"job_id": job.id, "status": "FAILED", "error": job.error_message}

        # 5. Find or create replica record for target node
        target_replica = next((r for r in version.replicas if r.node_id == target_node.id), None)
        if not target_replica:
            target_replica = ObjectReplica(
                version_id=version.id,
                node_id=target_node.id,
                chunk_index=len(version.replicas),
                status="HEALTHY",
                stored_checksum=computed_sha,
            )
            self.session.add(target_replica)
            await self.session.flush()
        else:
            target_replica.status = "HEALTHY"
            target_replica.stored_checksum = computed_sha

        # 6. Write chunk to target node daemon
        await node_client.put_chunk(
            target_node.host,
            target_node.port,
            target_replica.id,
            chunk_data,
        )

        # 7. Complete job record
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        job.bytes_repaired = len(chunk_data)
        job.source_node_id = source_replica.node_id
        await self.session.flush()

        await self.event_repo.log_event(
            event_type="REPLICA_REBUILT",
            severity="INFO",
            category="REPAIR",
            message=f"Replica {target_replica.id} successfully rebuilt on node {target_node.name} ({len(chunk_data)} bytes)",
            details_json={
                "job_id": job.id,
                "replica_id": target_replica.id,
                "node_id": target_node.id,
                "node_name": target_node.name,
                "bytes": len(chunk_data),
            },
        )

        # 8. Check if object is now fully healthy
        required_rf = 3
        if version.object and version.object.bucket and version.object.bucket.policy:
            required_rf = version.object.bucket.policy.replication_factor

        healthy_reps = sum(1 for r in version.replicas if r.status == "HEALTHY")
        if healthy_reps >= required_rf:
            obj_key = version.object.key if version.object else version.id
            await self.event_repo.log_event(
                event_type="OBJECT_HEALTHY",
                severity="INFO",
                category="OBJECT",
                message=f"Object '{obj_key}' restored to HEALTHY state ({healthy_reps}/{required_rf} replicas)",
                details_json={
                    "object_id": version.object_id,
                    "key": obj_key,
                    "healthy_replicas": healthy_reps,
                    "required_rf": required_rf,
                },
            )

        return {
            "job_id": job.id,
            "status": "COMPLETED",
            "bytes_repaired": job.bytes_repaired,
            "replica_id": target_replica.id,
            "target_node": target_node.name,
        }
