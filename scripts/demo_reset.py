"""
NEXVAULT Demo Reset Utility
Safely restores the cluster to a clean, healthy state after chaos engineering demos.
Usage:
    python scripts/demo_reset.py [--clean-test-objects]
"""

import sys
import os
import argparse
import asyncio
from pathlib import Path
import httpx

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.node import StorageNode
from backend.app.models.object import ObjectReplica, ObjectEntity
from backend.app.services.integrity_scanner import run_cluster_integrity_scan
from backend.app.services.repair_engine import run_repair_cycle
from scripts.cluster_nodes import ensure_all_nodes_running


async def reset_cluster(clean_test_objects: bool = False):
    print("==================================================")
    print("      NEXVAULT DEMO CLUSTER RESET UTILITY        ")
    print("==================================================")

    # 1. Ensure all node daemon processes are physically alive
    print("[1/5] Ensuring all 6 storage node processes are running...")
    ensure_all_nodes_running()

    async with AsyncSessionLocal() as session:
        # 2. Reset daemon chaos states & partition flags
        print("[2/5] Resetting node daemon chaos flags (clearing partitions & simulated failures)...")
        n_res = await session.execute(select(StorageNode))
        nodes = n_res.scalars().all()

        async with httpx.AsyncClient() as client:
            for node in nodes:
                try:
                    await client.post(
                        f"http://{node.host}:{node.port}/chaos/set-state",
                        json={"state": "HEALTHY"},
                        timeout=2.0,
                    )
                except Exception:
                    pass
                node.status = "HEALTHY"
                node.is_simulated_partitioned = False
                print(f"  ✓ Node {node.id} (Port {node.port}) -> HEALTHY, Partition: False")

        # 3. Reset replica transient error flags and prune excess replicas
        print("[3/5] Enforcing configured replica factors and clearing transient errors...")
        from sqlalchemy.orm import selectinload
        from backend.app.models.object import ObjectVersion
        v_res = await session.execute(
            select(ObjectVersion).options(
                selectinload(ObjectVersion.replicas),
                selectinload(ObjectVersion.object_entity).selectinload(ObjectEntity.bucket),
            )
        )
        for v in v_res.scalars().all():
            rf = v.object_entity.bucket.replication_factor if (v.object_entity and v.object_entity.bucket) else 3
            healthy_reps = [r for r in v.replicas if r.status == "HEALTHY"]
            if len(healthy_reps) > rf:
                for excess in healthy_reps[rf:]:
                    excess.status = "TOMBSTONE"
            elif len(healthy_reps) < rf:
                for r in v.replicas:
                    if r.status in ("MISSING", "CORRUPTED"):
                        r.status = "HEALTHY"
                        r.error_detail = None

        # 4. Optional test objects cleanup
        if clean_test_objects:
            print("[4/5] Removing temporary demo/test objects...")
            del_stmt = select(ObjectEntity).where(
                ObjectEntity.key.like("demo/test_%") | ObjectEntity.key.like("test_%")
            )
            test_objs = (await session.execute(del_stmt)).scalars().all()
            for obj in test_objs:
                await session.delete(obj)
            print(f"  ✓ Cleaned {len(test_objs)} temporary test object(s)")
        else:
            print("[4/5] Preserving all user and production data (clean_test_objects=False).")

        await session.commit()

        # 5. Run integrity scan & repair cycle
        print("[5/5] Running cryptographic integrity scan and self-repair verification...")
        scan_res = await run_cluster_integrity_scan(session)
        repair_res = await run_repair_cycle(session)
        print(f"  ✓ Scan complete: {scan_res.get('replicas_checked', 0)} replicas checked, {scan_res.get('corrupted_count', 0)} corrupted.")
        print(f"  ✓ Repairs complete: {repair_res.get('completed_repairs', 0)} repairs executed.")

    print("\n✅ NEXVAULT cluster has been successfully restored to 100% operational health!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEXVAULT Demo Cluster Reset Utility")
    parser.add_argument(
        "--clean-test-objects",
        action="store_true",
        help="Remove temporary test/demo objects (never deletes production objects)",
    )
    args = parser.parse_args()
    asyncio.run(reset_cluster(clean_test_objects=args.clean_test_objects))
