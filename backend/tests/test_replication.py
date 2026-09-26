"""
Step 3 Verification: Replication, Failover Reads, and Tombstone Deletion Tests
"""

import uuid
import hashlib
import httpx
import pytest
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bucket import Bucket
from backend.app.models.node import StorageNode
from backend.app.services.placement import select_replica_nodes
from backend.app.services.data_pipeline import write_object, read_object, delete_object_tombstone


@pytest.mark.anyio
async def test_zone_aware_placement():
    """Verify RF=3 placement selects nodes from both ZONE_A and ZONE_B."""
    async with AsyncSessionLocal() as session:
        nodes = await select_replica_nodes(session, replication_factor=3)
        assert len(nodes) == 3
        zones = {n.zone for n in nodes}
        assert "ZONE_A" in zones
        assert "ZONE_B" in zones
        print(f"✓ Placement selected: {[n.id + '(' + n.zone + ')' for n in nodes]}")


@pytest.mark.anyio
async def test_concurrent_fanout_write_and_read():
    """Upload an object with RF=3 and read it back."""
    test_key = f"reports/q3_resilience_audit_{uuid.uuid4().hex[:8]}.pdf"
    test_bytes = b"%PDF-1.4 Resilience and Durability in Distributed Storage - NEXVAULT" * 50
    expected_sha = hashlib.sha256(test_bytes).hexdigest()

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # 1. Write Object
        version = await write_object(
            session,
            bucket=bucket,
            key=test_key,
            data=test_bytes,
            content_type="application/pdf",
        )
        assert version.version_num == 1
        assert version.checksum_sha256 == expected_sha
        assert len(version.replicas) == 3

        # 2. Read Object back
        read_bytes, fetched_version = await read_object(session, bucket_name="production-data", key=test_key)
        assert read_bytes == test_bytes
        assert fetched_version.version_num == 1


@pytest.mark.anyio
async def test_resilient_failover_when_replica_fails():
    """Simulate failure of one replica node; confirm read succeeds from remaining replicas."""
    test_key = f"configs/mission_critical_{uuid.uuid4().hex[:8]}.yaml"
    test_data = b"cluster_name: NEXVAULT\nreplication_factor: 3\nstatus: active"

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # Write
        v = await write_object(session, bucket=bucket, key=test_key, data=test_data)
        assert len(v.replicas) == 3

        # Simulate failure of the first replica's node
        primary_replica = v.replicas[0]
        node_res = await session.execute(select(StorageNode).where(StorageNode.id == primary_replica.node_id))
        failed_node = node_res.scalar_one()

        # Set node to FAILED via its chaos endpoint
        httpx.post(f"http://{failed_node.host}:{failed_node.port}/chaos/set-state", json={"state": "FAILED"})

        try:
            # Resilient read must succeed from other healthy nodes!
            read_bytes, read_v = await read_object(session, bucket_name="production-data", key=test_key)
            assert read_bytes == test_data
            assert read_v.version_num == v.version_num
            print(f"✓ Resilient read succeeded seamlessly even when {failed_node.id} was offline!")
        finally:
            # Restore node to healthy
            httpx.post(f"http://{failed_node.host}:{failed_node.port}/chaos/set-state", json={"state": "HEALTHY"})


@pytest.mark.anyio
async def test_tombstone_deletion_and_version_preservation():
    """Verify tombstone soft-deletion and historical version retrieval."""
    test_key = f"secrets/keys_{uuid.uuid4().hex[:8]}.txt"
    v1_data = b"INITIAL_SECRET_V1"
    v2_data = b"UPDATED_SECRET_V2"

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # Write v1
        await write_object(session, bucket, test_key, v1_data)
        # Write v2
        await write_object(session, bucket, test_key, v2_data)

        # Delete (creates tombstone)
        tombstone = await delete_object_tombstone(session, "production-data", test_key)
        assert tombstone.is_tombstone is True
        assert tombstone.version_num == 3

        # Latest read should fail with 404
        with pytest.raises(Exception):
            await read_object(session, "production-data", test_key)

        # But reading specific historical version v1 or v2 must STILL SUCCEED!
        read_v1, _ = await read_object(session, "production-data", test_key, version_num=1)
        assert read_v1 == v1_data
        read_v2, _ = await read_object(session, "production-data", test_key, version_num=2)
        assert read_v2 == v2_data
        print("✓ Historical versions preserved and retrievable after tombstone deletion!")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
