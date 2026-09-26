"""
Step 6 Verification: Cluster Rebalancing and Network Partition Simulation Tests
"""

import uuid
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.core.database import AsyncSessionLocal
from backend.app.models.bucket import Bucket
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectReplica
from backend.app.services.data_pipeline import write_object
from backend.app.services.rebalance_engine import run_rebalance_cycle, evaluate_cluster_skew


@pytest.mark.anyio
async def test_rebalance_migration():
    """Verify that forcing rebalance moves a replica from donor node to receiver node."""
    test_key = f"datasets/skew_test_{uuid.uuid4().hex[:8]}.csv"
    test_bytes = b"id,val\n1,100\n2,200\n3,300\n" * 10

    async with AsyncSessionLocal() as session:
        b_res = await session.execute(select(Bucket).where(Bucket.name == "production-data"))
        bucket = b_res.scalar_one()

        # Write an object
        v = await write_object(session, bucket, test_key, test_bytes)
        v_id = str(v.id)

        # Run rebalance cycle with force=True
        res = await run_rebalance_cycle(session, force=True)
        assert res["rebalanced"] is True
        assert "source_node" in res
        assert "target_node" in res
        assert res["source_node"] != res["target_node"]
        print(f"✓ Rebalanced replica from {res['source_node']} -> {res['target_node']} ({res['bytes_moved']} bytes)")

        # Verify replica in database points to target_node
        rep_res = await session.execute(
            select(ObjectReplica).where(ObjectReplica.id == res["replica_id"])
        )
        moved_rep = rep_res.scalar_one()
        assert moved_rep.node_id == res["target_node"]


@pytest.mark.anyio
async def test_simulated_network_partition():
    """
    Simulate network partition on node-4.
    Coordinator treats node-4 as partitioned and unreachable.
    Local data on node-4 remains intact on disk.
    """
    async with AsyncSessionLocal() as session:
        n_res = await session.execute(select(StorageNode).where(StorageNode.id == "node-4"))
        node4 = n_res.scalar_one()

        # Partition node 4
        node4.is_simulated_partitioned = True
        await session.commit()

        # Check that node 4 cannot be selected for placement
        from backend.app.services.placement import select_replica_nodes
        selected = await select_replica_nodes(session, replication_factor=3)
        selected_ids = {n.id for n in selected}
        assert "node-4" not in selected_ids
        print("✓ Placement engine correctly excluded partitioned node-4")

        # Verify node-4 HTTP process is still actually running and healthy directly
        resp = httpx.get(f"http://{node4.host}:{node4.port}/health")
        assert resp.status_code == 200
        print("✓ Node-4 local data plane daemon is intact and running")

        # Unpartition
        node4.is_simulated_partitioned = False
        await session.commit()

        # Verify node-4 can be selected again
        re_selected = await select_replica_nodes(session, replication_factor=6)
        assert any(n.id == "node-4" for n in re_selected)
        print("✓ Node-4 successfully rejoins the pool after unpartitioning")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
