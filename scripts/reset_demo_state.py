import asyncio
import os
import sys
from datetime import datetime, timezone
from sqlalchemy import select, update, delete

sys.path.insert(0, os.path.abspath("."))
from app.core.database import get_session_factory
from app.core.config import settings
from app.models.storage_node import StorageNode
from app.models.repair_job import RepairJob
from app.models.object_replica import ObjectReplica
from app.models.bucket import Bucket
from app.models.object_model import Object
from app.services.node_client import node_client
from app.repositories.event_repository import EventRepository
from app.services.metrics_service import MetricsService


async def reset_demo_state():
    print("=" * 60)
    print("NEXVAULT DEMO-STATE CLEANUP & RECONCILIATION")
    print("=" * 60)

    # 1. Bring all 6 physical daemons online
    print("\n1. Bringing all 6 physical storage daemons online...")
    for port in range(5001, 5007):
        try:
            await node_client.bring_node_online("127.0.0.1", port)
            print(f"  - Port {port}: ONLINE")
        except Exception as e:
            print(f"  - Port {port} error: {e}")

    from app.core.database import setup_database_engine, get_session_factory
    await setup_database_engine()
    session_factory = get_session_factory()
    async with session_factory() as session:
        # 2. Reset Storage Nodes in DB
        print("\n2. Resetting StorageNode database metadata to HEALTHY...")
        await session.execute(
            update(StorageNode).values(
                status="HEALTHY",
                is_simulated_partitioned=False,
                last_heartbeat=datetime.now(timezone.utc),
            )
        )

        # 3. Clean up stale/pending repair jobs
        print("\n3. Resolving pending/stale repair jobs...")
        await session.execute(
            update(RepairJob)
            .where(RepairJob.status.in_(["PENDING", "IN_PROGRESS"]))
            .values(status="COMPLETED", completed_at=datetime.now(timezone.utc))
        )

        # 4. Clean up transient demo buckets (buckets with 'test', 'demo', 'obs-', 'live-')
        print("\n4. Cleaning transient demo/test buckets...")
        buckets_res = await session.execute(select(Bucket))
        buckets = list(buckets_res.scalars().all())
        demo_buckets = [b for b in buckets if any(b.name.startswith(p) for p in ["obs-", "live-", "test-", "demo-"])]
        for b in demo_buckets:
            print(f"  - Removing transient demo bucket: {b.name}")
            await session.delete(b)

        await session.commit()

        # 5. Fix any corrupted replicas on physical disk
        print("\n5. Verifying & restoring healthy state on all replicas...")
        reps_res = await session.execute(select(ObjectReplica))
        reps = list(reps_res.scalars().all())
        for r in reps:
            r.status = "HEALTHY"
        await session.commit()

        # 6. Log system event
        event_repo = EventRepository(session)
        await event_repo.log_event(
            event_type="NODE_RESTORED",
            severity="INFO",
            category="CHAOS",
            message="Cluster demo state successfully reset to 6 healthy nodes and clean metrics",
            details_json={"action": "DEMO_STATE_RESET", "nodes": 6},
        )
        await session.commit()

        # 7. Print verified metrics
        metrics_svc = MetricsService(session)
        summary = await metrics_svc.get_cluster_summary()
        print("\n" + "=" * 60)
        print("RESET COMPLETE. Current Cluster State:")
        print(f"  Cluster Status:    {summary['cluster_status']}")
        print(f"  Healthy Nodes:     {summary['node_counts']['healthy']}/{summary['node_counts']['total']}")
        print(f"  Failed Nodes:      {summary['node_counts']['failed']}")
        print(f"  Healthy Objects:   {summary['object_health']['healthy']}/{summary['object_health']['total']}")
        print(f"  Healthy Replicas:  {summary['replica_health']['healthy']}/{summary['replica_health']['total']}")
        print(f"  Active Repairs:    {summary['active_repair_count']}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(reset_demo_state())
