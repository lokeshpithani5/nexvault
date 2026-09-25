import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
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
        """Creates a repair job if one is not already active for this version (Idempotent)."""
        # Idempotency check: don't create multiple active jobs for the same version
        active_job = await self.repair_repo.get_active_job_for_version(version_id)
        if active_job:
            logger.info(f"Active repair job {active_job.id} already exists for version {version_id}. Reusing.")
            return active_job

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

    def select_repair_target_node(
        self,
        version: ObjectVersion,
        healthy_nodes: List[StorageNode],
    ) -> Optional[StorageNode]:
        """
        Selects an optimal target node for repair:
        - Avoids nodes that already host a healthy, readable replica for this version.
        - Preserves failure-zone diversity (Zone A vs Zone B).
        - Balances load by selecting candidate with least used capacity.
        - Falls back to in-place repair if a corrupted replica is on an otherwise healthy node.
        """
        # Identify nodes currently hosting a healthy replica
        existing_healthy_node_ids = {
            r.node_id
            for r in version.replicas
            if r.status == "HEALTHY"
            and r.node
            and r.node.status == "HEALTHY"
            and not r.node.is_simulated_partitioned
        }

        # Candidates must be healthy, not partitioned, and not already hosting a healthy replica
        candidates = [n for n in healthy_nodes if n.id not in existing_healthy_node_ids]

        if candidates:
            # Check zone distribution of existing healthy replicas
            existing_zones = [
                r.node.zone
                for r in version.replicas
                if r.status == "HEALTHY"
                and r.node
                and r.node.status == "HEALTHY"
                and not r.node.is_simulated_partitioned
            ]
            count_a = sum(1 for z in existing_zones if z == "Zone-A")
            count_b = sum(1 for z in existing_zones if z == "Zone-B")

            preferred_zone = "Zone-A" if count_a < count_b else "Zone-B"
            zone_candidates = [n for n in candidates if n.zone == preferred_zone]
            eligible = zone_candidates if zone_candidates else candidates

            # Sort by least used capacity
            eligible.sort(key=lambda n: n.used_capacity_bytes)
            return eligible[0]

        # If all healthy nodes already host a replica, check for in-place repair on a corrupted replica
        corrupt_reps = [
            r for r in version.replicas
            if r.status == "CORRUPTED"
            and r.node
            and r.node.status == "HEALTHY"
            and not r.node.is_simulated_partitioned
        ]
        if corrupt_reps:
            return corrupt_reps[0].node

        return None

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

        # Idempotency check: if already completed, return immediately
        if job.status == "COMPLETED":
            return {
                "job_id": job.id,
                "status": "COMPLETED",
                "bytes_repaired": job.bytes_repaired,
                "message": "Job already completed",
            }

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

        # 1. Identify healthy source replica to copy from (never copy from corrupted replica)
        source_replica = None
        for r in version.replicas:
            if (
                r.status == "HEALTHY"
                and r.node
                and r.node.status == "HEALTHY"
                and not r.node.is_simulated_partitioned
            ):
                source_replica = r
                break

        if not source_replica:
            job.status = "FAILED"
            job.error_message = "No healthy, reachable source replica available for reconstruction"
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

        # 3. Verify SHA-256 checksum against metadata
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
        if not target_node or target_node.status != "HEALTHY" or target_node.is_simulated_partitioned:
            job.status = "FAILED"
            job.error_message = "Target storage node is offline or partitioned"
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

        # 8. Check if object has restored full durability
        required_rf = 3
        if version.object and version.object.bucket and version.object.bucket.policy:
            required_rf = version.object.bucket.policy.replication_factor

        healthy_reps = sum(
            1 for r in version.replicas
            if r.status == "HEALTHY"
            and r.node
            and r.node.status == "HEALTHY"
            and not r.node.is_simulated_partitioned
        )
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

    async def reconcile_version(
        self,
        version_id: str,
        trigger_reason: str = "DURABILITY_VIOLATION",
    ) -> Optional[Dict[str, Any]]:
        """Evaluates version durability and creates/executes automatic repair if under-replicated."""
        v_stmt = (
            select(ObjectVersion)
            .where(ObjectVersion.id == version_id)
            .options(
                selectinload(ObjectVersion.replicas).selectinload(ObjectReplica.node),
                selectinload(ObjectVersion.object).selectinload(Object.bucket).selectinload(Bucket.policy),
            )
        )
        v_res = await self.session.execute(v_stmt)
        version = v_res.scalars().first()
        if not version or version.is_tombstone:
            return None

        required_rf = 3
        if version.object and version.object.bucket and version.object.bucket.policy:
            required_rf = version.object.bucket.policy.replication_factor

        healthy_readable_reps = [
            r for r in version.replicas
            if r.status == "HEALTHY"
            and r.node
            and r.node.status == "HEALTHY"
            and not r.node.is_simulated_partitioned
        ]

        if len(healthy_readable_reps) < required_rf:
            # Check idempotency: is an active repair job already pending/running?
            active_job = await self.repair_repo.get_active_job_for_version(version.id)
            if active_job:
                if active_job.status == "PENDING":
                    return await self.execute_repair(active_job.id)
                return {"job_id": active_job.id, "status": active_job.status, "message": "Repair already active"}

            if not healthy_readable_reps:
                logger.error(f"Cannot repair version {version.id}: 0 healthy replicas available")
                return None

            # Find healthy nodes in cluster
            nodes_stmt = select(StorageNode).where(
                StorageNode.status == "HEALTHY",
                StorageNode.is_simulated_partitioned == False,
            )
            nodes_res = await self.session.execute(nodes_stmt)
            healthy_nodes = list(nodes_res.scalars().all())

            target_node = self.select_repair_target_node(version, healthy_nodes)
            if not target_node:
                logger.warning(f"No eligible target node found to repair version {version.id}")
                return None

            source_rep = healthy_readable_reps[0]
            job = await self.create_repair_job(
                version_id=version.id,
                target_node_id=target_node.id,
                source_node_id=source_rep.node_id,
                trigger_reason=trigger_reason,
            )
            return await self.execute_repair(job.id)

        return None

    async def run_cluster_reconciliation(self) -> Dict[str, Any]:
        """
        Periodically discovers and repairs all degraded objects across the cluster.
        Safe, idempotent, and non-blocking.
        """
        objects_stmt = (
            select(Object)
            .where(Object.is_deleted == False)
            .options(
                selectinload(Object.versions).selectinload(ObjectVersion.replicas).selectinload(ObjectReplica.node),
                selectinload(Object.bucket).selectinload(Bucket.policy),
            )
        )
        objects_res = await self.session.execute(objects_stmt)
        objects = list(objects_res.scalars().all())

        repaired_jobs = []
        for obj in objects:
            active_versions = [v for v in obj.versions if not v.is_tombstone]
            if not active_versions:
                continue

            latest_v = active_versions[0]
            rep_result = await self.reconcile_version(latest_v.id)
            if rep_result and rep_result.get("status") == "COMPLETED":
                repaired_jobs.append(rep_result)

        return {
            "scanned_objects": len(objects),
            "repairs_executed": len(repaired_jobs),
            "repair_results": repaired_jobs,
        }

    async def reconcile_node_restoration(self, node_id: str) -> Dict[str, Any]:
        """
        Reconciles a node returning from failure:
        1. Marks RECOVERING
        2. Checks physical daemon health
        3. Inspects physical replicas on disk against metadata
        4. Reconciles corrupt/missing chunks
        5. Returns node to HEALTHY only when verified
        """
        node = await self.node_repo.get_by_id(node_id)
        if not node:
            raise ResourceNotFoundError(message=f"Node '{node_id}' not found")

        # 1. Mark RECOVERING
        node.status = "RECOVERING"
        await self.session.flush()
        await self.event_repo.log_event(
            event_type="NODE_RECOVERING",
            severity="WARNING",
            category="NODE",
            message=f"Node {node.name} marked RECOVERING during restoration reconciliation",
            details_json={"node_id": node.id, "node_name": node.name, "status": "RECOVERING"},
        )

        # 2. Check physical daemon response
        daemon_health = await node_client.check_health(node.host, node.port)
        if daemon_health is None:
            node.status = "FAILED"
            await self.session.flush()
            return {"node_id": node.id, "status": "FAILED", "error": "Daemon unreachable"}

        # 3. Inspect existing replicas on this node
        reps_stmt = (
            select(ObjectReplica)
            .where(ObjectReplica.node_id == node.id)
            .options(selectinload(ObjectReplica.version))
        )
        reps_res = await self.session.execute(reps_stmt)
        replicas = list(reps_res.scalars().all())

        verified_count = 0
        corrupted_count = 0

        async def verify_one(rep):
            nonlocal verified_count, corrupted_count
            try:
                data, sha = await node_client.get_chunk(node.host, node.port, rep.id)
                comp_sha = hashlib.sha256(data).hexdigest()
                if comp_sha != rep.stored_checksum:
                    rep.status = "CORRUPTED"
                    corrupted_count += 1
                    await self.event_repo.log_event(
                        event_type="REPLICA_CORRUPTED",
                        severity="ERROR",
                        category="REPLICA",
                        message=f"Replica {rep.id} on restored node {node.name} failed checksum verification",
                        details_json={"replica_id": rep.id, "node_id": node.id, "expected": rep.stored_checksum, "actual": comp_sha},
                    )
                else:
                    rep.status = "HEALTHY"
                    verified_count += 1
            except Exception:
                rep.status = "CORRUPTED"
                corrupted_count += 1

        batch_size = 20
        for i in range(0, len(replicas), batch_size):
            await asyncio.gather(*(verify_one(r) for r in replicas[i:i + batch_size]))

        await self.session.flush()


        # 4. Repair any corrupted replicas
        if corrupted_count > 0:
            for r in replicas:
                if r.status == "CORRUPTED" and r.version:
                    await self.reconcile_version(r.version_id, trigger_reason="RESTORED_NODE_CORRUPTION")

        # 5. Return node to HEALTHY
        node.status = "HEALTHY"
        node.is_simulated_partitioned = False
        node.last_heartbeat = datetime.now(timezone.utc)
        await self.session.flush()

        await self.event_repo.log_event(
            event_type="NODE_RESTORED",
            severity="INFO",
            category="NODE",
            message=f"Node {node.name} restored and fully reconciled to HEALTHY",
            details_json={
                "node_id": node.id,
                "node_name": node.name,
                "status": "HEALTHY",
                "verified_replicas": verified_count,
                "corrupted_replicas": corrupted_count,
            },
        )

        return {
            "node_id": node.id,
            "status": "HEALTHY",
            "verified_replicas": verified_count,
            "corrupted_replicas": corrupted_count,
        }
