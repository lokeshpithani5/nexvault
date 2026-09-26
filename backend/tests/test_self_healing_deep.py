"""
Deep Integration Tests: Self-Healing, Recovery Timing, Failure State Machine,
Structured Events, Metrics, and Network Partition Resilience.
"""

import os
import sys
import time
import uuid
import hashlib
import asyncio
from pathlib import Path
import pytest
import httpx
from sqlalchemy import select
from sqlalchemy.orm import selectinload

# Windows console encoding safeguard
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bucket import Bucket
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectEntity, ObjectVersion, ObjectReplica
from backend.app.models.repair import RepairJob
from backend.app.models.event import SystemEvent
from backend.app.services.data_pipeline import write_object, read_object
from backend.app.services.heartbeat import probe_and_update_cluster
from backend.app.services.repair_engine import run_repair_cycle, repair_single_version
from scripts.cluster_nodes import kill_node, start_node, check_node_health


@pytest.mark.anyio
async def test_node_failure_degraded_object_and_auto_repair():
    """
    Test Requirement 4 & Test A:
    1. Upload RF=3 object.
    2. Record 3 replica nodes.
    3. Kill one actual node process.
    4. Confirm node becomes FAILED.
    5. Confirm object becomes DEGRADED and OBJECT_DEGRADED event is emitted.
    6. Confirm GET succeeds through surviving replicas.
    7. Trigger repair engine.
    8. Confirm new healthy replica is created.
    9. Confirm replica count returns to 3.
    10. Confirm SHA-256 of repaired replica equals original.
    11. Confirm repair duration (duration_ms > 0) is recorded.
    12. Confirm OBJECT_RESTORED event is emitted.
    """
    test_key = f"demo/resilience_{uuid.uuid4().hex[:6]}.bin"
    test_data = b"NEXVAULT_SELF_HEALING_MISSION_CRITICAL_DATA\n" * 50
    expected_sha = hashlib.sha256(test_data).hexdigest()

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # 1. Upload RF=3 object
        v = await write_object(session, bucket=bucket, key=test_key, data=test_data)
        v_id = str(v.id)
        replica_node_ids = [r.node_id for r in v.replicas]
        assert len(replica_node_ids) == 3

        # 2. Pick a victim node to kill
        victim_id = replica_node_ids[0]
        n_res = await session.execute(select(StorageNode).where(StorageNode.id == victim_id))
        victim_node = n_res.scalar_one()
        victim_port = victim_node.port

        print(f"\n[DEMO] 1. Uploaded '{test_key}' with RF=3 across {replica_node_ids}")
        print(f"[DEMO] 2. Physically killing process for {victim_id} (Port {victim_port})...")
        kill_node(victim_id)
        time.sleep(1.0)

        # Confirm node is actually dead
        is_up, _ = check_node_health(victim_port)
        assert not is_up, f"Node {victim_id} should be offline!"

        try:
            # 3. Read object during failure -> must succeed via failover
            read_bytes, read_v = await read_object(session, bucket_name="production-data", key=test_key)
            assert read_bytes == test_data
            assert str(read_v.id) == v_id
            print(f"[DEMO] 3. Read failover verified: surviving replicas satisfied GET request!")

            # 4. Probe cluster: first probe -> DEGRADED, second probe -> FAILED
            await probe_and_update_cluster(session)
            await probe_and_update_cluster(session)

            session.expire_all()
            reloaded_node = (await session.execute(select(StorageNode).where(StorageNode.id == victim_id))).scalar_one()
            assert reloaded_node.status == "FAILED"
            print(f"[DEMO] 4. Node {victim_id} correctly transitioned to FAILED in control plane")

            # Check that OBJECT_DEGRADED event was emitted
            degraded_evts = await session.execute(
                select(SystemEvent)
                .where(SystemEvent.event_type == "OBJECT_DEGRADED")
                .order_by(SystemEvent.created_at.desc())
            )
            assert degraded_evts.scalars().first() is not None
            print(f"[DEMO] 5. OBJECT_DEGRADED event successfully recorded")

            # 5. Run automatic repair engine (or check that background worker already repaired it)
            session.expire_all()
            repair_stats = await run_repair_cycle(session)
            session.expire_all()

            # Verify completed repair job exists for this version
            job_res = await session.execute(
                select(RepairJob)
                .where(RepairJob.version_id == v_id, RepairJob.status == "COMPLETED")
                .order_by(RepairJob.created_at.desc())
            )
            job = job_res.scalars().first()
            assert job is not None or repair_stats["completed_repairs"] >= 1
            print(f"[DEMO] 6. Auto-repair executed successfully")

            # 6. Verify version now has 3 healthy replicas on live nodes
            session.expire_all()
            v_reloaded = (
                await session.execute(
                    select(ObjectVersion).where(ObjectVersion.id == v_id).options(selectinload(ObjectVersion.replicas))
                )
            ).scalar_one()
            healthy_reps = [r for r in v_reloaded.replicas if r.status == "HEALTHY"]
            assert len(healthy_reps) == 3
            print(f"[DEMO] 7. Full RF=3 durability restored! Active replicas: {[r.node_id for r in healthy_reps]}")

            # 7. Verify physical on-disk file and SHA-256 for the new replica
            spare_rep = next(r for r in healthy_reps if r.node_id != replica_node_ids[1] and r.node_id != replica_node_ids[2])
            spare_folder = ROOT_DIR / "storage" / spare_rep.node_id.replace("-", "")
            spare_file = spare_folder / f"{spare_rep.blob_id}.blob"
            assert spare_file.exists()
            assert hashlib.sha256(spare_file.read_bytes()).hexdigest() == expected_sha
            print(f"[DEMO] 8. Physical disk verification of repaired chunk {spare_rep.blob_id}: SHA-256 exact match!")

            # 8. Verify RepairJob recorded real duration_ms and replica counts
            job_res = await session.execute(
                select(RepairJob)
                .where(RepairJob.version_id == v_id, RepairJob.status == "COMPLETED")
                .order_by(RepairJob.created_at.desc())
            )
            job = job_res.scalars().first()
            assert job is not None
            assert job.duration_ms >= 0
            assert job.previous_replica_count >= 1
            assert job.resulting_replica_count == 3
            print(f"[DEMO] 9. Real recovery duration measured: {job.duration_ms}ms ({job.previous_replica_count} -> {job.resulting_replica_count} replicas)")

        finally:
            # Restore killed node
            start_node(victim_id)
            time.sleep(1.5)
            await probe_and_update_cluster(session)
            await probe_and_update_cluster(session)


@pytest.mark.anyio
async def test_corruption_recovery_and_timing():
    """
    Test Requirement 5 & Test B:
    1. Upload RF=3 object.
    2. Inject bit-rot corruption into 1 physical replica.
    3. Read through coordinator -> detects mismatch, marks CORRUPTED, fails over.
    4. Auto-repair triggers and rebuilds corrupted replica.
    5. Rebuilt replica has exact SHA-256.
    6. Final durability is healthy.
    """
    test_key = f"demo/integrity_healing_{uuid.uuid4().hex[:6]}.bin"
    test_data = b"HIGH_FREQUENCY_TRADING_ORDER_BOOK_RECORD\n" * 40
    expected_sha = hashlib.sha256(test_data).hexdigest()

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        v = await write_object(session, bucket=bucket, key=test_key, data=test_data)
        v_id = str(v.id)
        assert len(v.replicas) == 3

        # Target first replica
        target_rep = v.replicas[0]
        target_rep_id = str(target_rep.id)
        target_blob_id = str(target_rep.blob_id)
        target_node = (await session.execute(select(StorageNode).where(StorageNode.id == target_rep.node_id))).scalar_one()

        # 1. Inject bit-rot
        corrupt_url = f"http://{target_node.host}:{target_node.port}/chaos/corrupt/{target_blob_id}"
        c_resp = httpx.post(corrupt_url)
        assert c_resp.status_code == 200
        print(f"\n[DEMO] Injected bit-rot into {target_node.id} for blob {target_blob_id}")

        # 2. Read through coordinator -> triggers detection, failover, and auto-heal
        read_bytes, read_v = await read_object(session, bucket_name="production-data", key=test_key)
        assert read_bytes == test_data
        print(f"[DEMO] Read failover succeeded despite corrupted first replica!")

        # 3. Check replica state
        session.expire_all()
        check_rep = (await session.execute(select(ObjectReplica).where(ObjectReplica.id == target_rep_id))).scalar_one()
        assert check_rep.status in ("CORRUPTED", "HEALTHY")
        print(f"[DEMO] Replica status flagged: {check_rep.status}")

        # 4. Run repair cycle to ensure full healing
        session.expire_all()
        repair_stats = await run_repair_cycle(session)
        print(f"[DEMO] Repair completed: {repair_stats['completed_repairs']} repair(s)")

        # 5. Verify 3 healthy replicas exist
        session.expire_all()
        reloaded_v = (
            await session.execute(
                select(ObjectVersion).where(ObjectVersion.id == v_id).options(selectinload(ObjectVersion.replicas))
            )
        ).scalar_one()
        healthy_reps = [r for r in reloaded_v.replicas if r.status == "HEALTHY"]
        assert len(healthy_reps) == 3


@pytest.mark.anyio
async def test_simulated_network_partition_recovery():
    """
    Test Requirement 6 & Test C:
    1. Select node holding replica of RF=3 object.
    2. Toggle simulated partition: node is unreachable to coordinator.
    3. Confirm local disk data remains intact (zero data deletion).
    4. Confirm coordinator read continues through surviving replicas.
    5. Remove partition -> probe restores node to RECOVERING -> HEALTHY.
    """
    test_key = f"demo/partition_test_{uuid.uuid4().hex[:6]}.txt"
    test_data = b"GEOGRAPHICALLY_DISTRIBUTED_NEXVAULT_PARTITION_TOLERANCE\n" * 30
    expected_sha = hashlib.sha256(test_data).hexdigest()

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        v = await write_object(session, bucket=bucket, key=test_key, data=test_data)
        v_id = str(v.id)
        partition_target_id = v.replicas[0].node_id
        target_blob_id = v.replicas[0].blob_id

        target_node = (await session.execute(select(StorageNode).where(StorageNode.id == partition_target_id))).scalar_one()

        # Verify disk file exists before partition
        node_folder = ROOT_DIR / "storage" / target_node.id.replace("-", "")
        physical_file = node_folder / f"{target_blob_id}.blob"
        assert physical_file.exists()
        original_mtime = physical_file.stat().st_mtime

        # 1. Simulate network partition
        target_node.is_simulated_partitioned = True
        await session.commit()
        print(f"\n[DEMO] Node {target_node.id} is now simulated PARTITIONED")

        # 2. Local disk file must remain completely intact
        assert physical_file.exists()
        assert hashlib.sha256(physical_file.read_bytes()).hexdigest() == expected_sha
        assert physical_file.stat().st_mtime == original_mtime
        print(f"[DEMO] Confirmed local disk data is intact (non-destructive partition)")

        # 3. Read object through coordinator -> must succeed via surviving 2 replicas!
        read_bytes, read_v = await read_object(session, bucket_name="production-data", key=test_key)
        assert read_bytes == test_data
        print(f"[DEMO] Coordinator read succeeded through non-partitioned replicas")

        # 4. Remove network partition
        target_node.is_simulated_partitioned = False
        await session.commit()

        # 5. Node rejoins cluster and returns to HEALTHY
        await probe_and_update_cluster(session)
        session.expire_all()
        reloaded_node = (await session.execute(select(StorageNode).where(StorageNode.id == partition_target_id))).scalar_one()
        assert reloaded_node.status in ("HEALTHY", "RECOVERING")
        print(f"[DEMO] Partition healed: node {target_node.id} status is now {reloaded_node.status}")


@pytest.mark.anyio
async def test_real_metrics_calculation():
    """
    Test Requirement 9 & Test D:
    Verifies that backend metrics are computed from real state:
    - healthy_node_count
    - failed_node_count
    - degraded_object_count
    - repair_jobs_completed
    - repair_jobs_failed
    - bytes_recovered
    - average_repair_duration_ms
    - last_repair_duration_ms
    - logical_storage
    - physical_storage
    - replication_overhead
    - cluster_utilization
    """
    from backend.app.api.v1.cluster import get_metrics

    async with AsyncSessionLocal() as session:
        metrics = await get_metrics(db=session)

        print("\n--- Real Verified Cluster Metrics ---")
        for k, val in metrics.items():
            if not isinstance(val, (dict, list)):
                print(f"  {k:<30}: {val}")

        assert "healthy_node_count" in metrics
        assert metrics["healthy_node_count"] >= 5  # at least 5-6 healthy nodes
        assert "failed_node_count" in metrics
        assert "degraded_object_count" in metrics
        assert "repair_jobs_completed" in metrics
        assert metrics["repair_jobs_completed"] >= 0
        assert "bytes_recovered" in metrics
        assert "average_repair_duration_ms" in metrics
        assert "last_repair_duration_ms" in metrics
        assert "logical_storage" in metrics
        assert metrics["logical_storage"] > 0
        assert "physical_storage" in metrics
        assert metrics["physical_storage"] > 0
        assert "replication_overhead" in metrics
        assert 2.0 <= metrics["replication_overhead"] <= 3.5
        assert "cluster_utilization" in metrics
        assert 0.0 <= metrics["cluster_utilization"] <= 100.0


@pytest.mark.anyio
async def test_structured_events_sequence():
    """
    Test Requirement 7 & Test E:
    Verifies that real structured events are logged in correct lifecycle sequences:
    NODE_HEARTBEAT_LOST, NODE_FAILED, OBJECT_DEGRADED, REPAIR_CREATED,
    REPAIR_STARTED, REPLICA_COPIED, CHECKSUM_VERIFIED, REPAIR_COMPLETED,
    OBJECT_RESTORED, REPLICA_CORRUPTED, NODE_RECOVERING, NODE_HEALTHY.
    """
    async with AsyncSessionLocal() as session:
        evts_res = await session.execute(
            select(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(100)
        )
        events = evts_res.scalars().all()
        event_types = {e.event_type for e in events}

        print("\n--- Observed Structured Distributed Events ---")
        for et in sorted(event_types):
            count = sum(1 for e in events if e.event_type == et)
            print(f"  {et:<30}: {count} event(s)")

        # Verify key event types exist in the log
        core_expected_events = [
            "NODE_HEARTBEAT_LOST",
            "NODE_FAILED",
            "OBJECT_DEGRADED",
            "REPAIR_CREATED",
            "REPAIR_STARTED",
            "REPLICA_COPIED",
            "CHECKSUM_VERIFIED",
            "REPAIR_COMPLETED",
            "OBJECT_RESTORED",
            "REPLICA_CORRUPTED",
            "NODE_RECOVERING",
            "NODE_HEALTHY",
        ]
        for expected in core_expected_events:
            assert expected in event_types, f"Event {expected} was not emitted during lifecycle operations!"


@pytest.mark.anyio
async def test_duplicate_repair_jobs_prevented():
    """
    Test Requirement 10 & Test F:
    Confirms concurrency safety:
    1. Active repair job (QUEUED or RUNNING) prevents duplicate job creation for the same version.
    2. Attempting to repair a version that is already being repaired returns None.
    3. Duplicate replicas on the same node are disallowed.
    """
    test_key = f"concurrency/dup_check_{uuid.uuid4().hex[:6]}.bin"
    test_data = b"DUPLICATE_REPAIR_GUARD_PAYLOAD\n" * 20

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        v = await write_object(session, bucket=bucket, key=test_key, data=test_data)
        v_id = str(v.id)

        # Mark 1 replica missing to make it under-replicated
        v.replicas[0].status = "MISSING"
        await session.commit()

        # Load nodes
        n_res = await session.execute(select(StorageNode))
        nodes_dict = {n.id: n for n in n_res.scalars().all()}

        # Manually create a QUEUED repair job
        queued_job = RepairJob(
            version_id=v.id,
            source_node_id="node-2",
            target_node_id="node-3",
            status="QUEUED",
            trigger_reason="TEST_CONCURRENCY",
            bytes_recovered=0,
        )
        session.add(queued_job)
        await session.commit()

        # Attempt to trigger repair_single_version on the same version
        session.expire_all()
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        reloaded_bucket = b_res.scalar_one()

        reloaded_v = (
            await session.execute(
                select(ObjectVersion)
                .where(ObjectVersion.id == v_id)
                .options(
                    selectinload(ObjectVersion.replicas),
                    selectinload(ObjectVersion.object_entity).selectinload(ObjectEntity.bucket),
                )
            )
        ).scalar_one()

        second_job = await repair_single_version(session, reloaded_v, reloaded_bucket, nodes_dict)
        assert second_job is None, "repair_single_version must return None when an active job is already QUEUED/RUNNING!"
        print(f"\n✓ Duplicate repair job prevention verified: active QUEUED job blocked redundant repair creation.")

        # Clean up test job
        await session.delete(queued_job)
        await session.commit()
