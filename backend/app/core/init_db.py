"""
Database Initialization & Seeding
Ensures tables exist and seeds nodes, admin/user accounts, and default buckets.
"""

import sys
import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from backend.app.core.database import engine, Base, AsyncSessionLocal
from backend.app.core.config import settings
from backend.app.core.security import get_password_hash
from backend.app.models.user import User
from backend.app.models.node import StorageNode
from backend.app.models.bucket import Bucket
from backend.app.models.event import SystemEvent


async def init_database():
    print("📦 Creating Control Plane database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # 1. Seed Storage Nodes
        for spec in settings.DEFAULT_STORAGE_NODES:
            stmt = select(StorageNode).where(StorageNode.id == spec["id"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                node = StorageNode(
                    id=spec["id"],
                    name=spec["name"],
                    host=spec["host"],
                    port=spec["port"],
                    zone=spec["zone"],
                    status="HEALTHY",
                    is_simulated_partitioned=False,
                    capacity_bytes=10 * 1024 * 1024 * 1024,
                    used_bytes=0,
                    replica_count=0,
                    last_heartbeat_at=datetime.now(timezone.utc),
                )
                session.add(node)
                print(f"  ✓ Registered {spec['id']} ({spec['zone']}, Port {spec['port']})")

        # 2. Seed Admin User
        admin_stmt = select(User).where(User.email == "admin@nexvault.io")
        admin_user = (await session.execute(admin_stmt)).scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                email="admin@nexvault.io",
                hashed_password=get_password_hash("admin123"),
                full_name="Cluster Administrator",
                role="ADMIN",
                is_active=True,
            )
            session.add(admin_user)
            await session.flush()
            print("  ✓ Created Admin user: admin@nexvault.io (password: admin123)")

        # 3. Seed Demo User
        demo_stmt = select(User).where(User.email == "demo@nexvault.io")
        demo_user = (await session.execute(demo_stmt)).scalar_one_or_none()
        if not demo_user:
            demo_user = User(
                email="demo@nexvault.io",
                hashed_password=get_password_hash("demo123"),
                full_name="Enterprise Operator",
                role="USER",
                is_active=True,
            )
            session.add(demo_user)
            await session.flush()
            print("  ✓ Created Demo user: demo@nexvault.io (password: demo123)")

        # 4. Seed Initial Buckets
        for b_name, rf, policy, owner in [
            ("production-data", 3, "REPLICATION_3X", admin_user),
            ("analytics-logs", 2, "REPLICATION_2X", demo_user),
        ]:
            b_stmt = select(Bucket).where(Bucket.name == b_name)
            existing_b = (await session.execute(b_stmt)).scalar_one_or_none()
            if not existing_b:
                bucket = Bucket(
                    name=b_name,
                    owner_id=owner.id,
                    replication_factor=rf,
                    durability_policy=policy,
                )
                session.add(bucket)
                print(f"  ✓ Created Bucket: {b_name} (RF={rf}, {policy})")

        # 5. Seed Initial System Event
        evt_stmt = select(SystemEvent)
        existing_evt = (await session.execute(evt_stmt)).scalars().first()
        if not existing_evt:
            init_event = SystemEvent(
                event_type="CLUSTER_INITIALIZED",
                severity="INFO",
                message="NEXVAULT Control Plane initialized with 6 autonomous storage nodes across 2 zones.",
                metadata_json={"zones": ["ZONE_A", "ZONE_B"], "node_count": 6},
            )
            session.add(init_event)

        await session.commit()
    print("✅ Control Plane database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(init_database())
