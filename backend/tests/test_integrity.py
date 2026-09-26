"""
Step 5 Verification: Integrity Verification Scrubber & Bit-Rot Self-Healing Tests
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
from backend.app.services.data_pipeline import write_object
from backend.app.services.integrity_scanner import run_cluster_integrity_scan


@pytest.mark.anyio
async def test_bit_rot_scrubbing_and_self_healing():
    """
    1. Write object with RF=3
    2. Inject bit-rot into one replica on disk
    3. Run integrity scrubber
    4. Confirm bit-rot is detected and replica marked CORRUPTED
    5. Confirm scrubber automatically heals the replica from healthy peer replicas
    """
    test_key = f"manifests/integrity_data_{uuid.uuid4().hex[:8]}.json"
    test_content = b'{"system": "NEXVAULT", "tier": "ultra-durable", "checksum_verified": true}' * 10
    expected_sha = hashlib.sha256(test_content).hexdigest()

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # 1. Write object
        v = await write_object(session, bucket, test_key, test_content)
        v_id = str(v.id)
        assert len(v.replicas) == 3

        # 2. Pick one replica to inject bit-rot
        target_replica = v.replicas[0]
        rep_blob_id = target_replica.blob_id
        rep_node_id = target_replica.node_id

        node_res = await session.execute(select(StorageNode).where(StorageNode.id == rep_node_id))
        target_node = node_res.scalar_one()

        # Call node chaos corrupt endpoint
        corrupt_resp = httpx.post(f"http://{target_node.host}:{target_node.port}/chaos/corrupt/{rep_blob_id}")
        assert corrupt_resp.status_code == 200
        assert corrupt_resp.json()["corrupted"] is True
        print(f"✓ Injected silent bit-rot into {target_node.id} chunk {rep_blob_id}")

        # 3. Run Cluster Integrity Scrubber
        scan_res = await run_cluster_integrity_scan(session)
        assert scan_res["corrupted_count"] >= 1
        assert scan_res["repaired_count"] >= 1
        print(f"✓ Scrubber detected {scan_res['corrupted_count']} corrupted replica(s) and auto-repaired {scan_res['repaired_count']}!")

        # 4. Reload version and verify healthy replica count is back to 3
        session.expire_all()
        reloaded_v_res = await session.execute(
            select(ObjectVersion)
            .where(ObjectVersion.id == v_id)
            .options(selectinload(ObjectVersion.replicas))
        )
        reloaded_v = reloaded_v_res.scalar_one()
        healthy_reps = [r for r in reloaded_v.replicas if r.status == "HEALTHY"]
        assert len(healthy_reps) == 3
        print("✓ Object successfully healed from bit-rot! Full replication factor restored.")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
