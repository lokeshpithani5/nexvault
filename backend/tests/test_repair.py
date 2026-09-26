"""
Step 4 Verification: Heartbeat Degradation Detection & Auto-Repair Engine Tests
"""

import uuid
import hashlib
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bucket import Bucket
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectVersion, ObjectReplica
from backend.app.models.repair import RepairJob
from backend.app.services.data_pipeline import write_object
from backend.app.services.heartbeat import probe_and_update_cluster
from backend.app.services.repair_engine import run_repair_cycle


@pytest.mark.anyio
async def test_heartbeat_detection_and_auto_repair():
    """
    1. Write object with RF=3
    2. Crash one replica node
    3. Run heartbeat probe: node is detected FAILED, replica marked MISSING
    4. Run repair engine: missing replica is reconstituted on a spare node
    5. Verify full durability restored
    """
    test_key = f"financials/ledger_{uuid.uuid4().hex[:8]}.dat"
    test_data = b"CRITICAL_FINANCIAL_TRANSACTION_RECORDS_AUDIT" * 20
    test_sha = hashlib.sha256(test_data).hexdigest()

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # Step 1: Write object (RF=3)
        v = await write_object(session, bucket, test_key, test_data)
        v_id = str(v.id)
        initial_node_ids = {r.node_id for r in v.replicas}
        assert len(initial_node_ids) == 3

        # Pick one node to fail
        victim_node_id = list(initial_node_ids)[0]
        v_node_res = await session.execute(select(StorageNode).where(StorageNode.id == victim_node_id))
        victim_node = v_node_res.scalar_one()
        victim_host = victim_node.host
        victim_port = victim_node.port

        # Step 2: Crash victim node
        httpx.post(f"http://{victim_host}:{victim_port}/chaos/set-state", json={"state": "FAILED"})

        try:
            # Step 3: Run heartbeat monitor (twice to transition HEALTHY -> DEGRADED -> FAILED)
            await probe_and_update_cluster(session)
            await probe_and_update_cluster(session)

            # Verify victim node marked FAILED
            await session.refresh(victim_node)
            assert victim_node.status == "FAILED"

            # Verify victim node's replica marked MISSING
            rep_res = await session.execute(
                select(ObjectReplica).where(
                    ObjectReplica.version_id == v.id,
                    ObjectReplica.node_id == victim_node_id,
                )
            )
            victim_replica = rep_res.scalar_one()
            assert victim_replica.status == "MISSING"
            print(f"✓ Victim node {victim_node_id} successfully marked FAILED, replica marked MISSING")

            # Step 4: Run auto-repair cycle
            repair_stats = await run_repair_cycle(session)
            assert repair_stats["completed_repairs"] >= 1
            assert repair_stats["bytes_recovered"] >= len(test_data)
            print(f"✓ Auto-repair restored {repair_stats['completed_repairs']} replica(s), {repair_stats['bytes_recovered']} bytes!")

            # Step 5: Verify new healthy replica exists on an alternative node
            session.expire_all()
            v_reloaded_res = await session.execute(
                select(ObjectVersion)
                .where(ObjectVersion.id == v_id)
                .options(selectinload(ObjectVersion.replicas))
            )
            v_reloaded = v_reloaded_res.scalar_one()
            healthy_replicas = [r for r in v_reloaded.replicas if r.status == "HEALTHY"]
            assert len(healthy_replicas) == 3

            # Check that a brand new node now hosts the replica
            new_node_ids = {r.node_id for r in healthy_replicas}
            assert victim_node_id not in new_node_ids
            spare_node_id = list(new_node_ids - initial_node_ids)[0]
            print(f"✓ Object restored to full RF=3! New replica successfully created on spare node: {spare_node_id}")

            # Verify repair job logged
            job_res = await session.execute(
                select(RepairJob).where(RepairJob.version_id == v_id)
            )
            jobs = job_res.scalars().all()
            assert any(j.status == "COMPLETED" and j.target_node_id == spare_node_id for j in jobs)

        finally:
            # Restore victim node using cached host and port
            httpx.post(f"http://{victim_host}:{victim_port}/chaos/set-state", json={"state": "HEALTHY"})
            await probe_and_update_cluster(session)
            await probe_and_update_cluster(session)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
