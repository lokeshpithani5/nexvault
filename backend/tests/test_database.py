"""
Step 2 Verification: Database Models, Security, and Seeding Tests
"""

import pytest
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.core.security import verify_password, get_password_hash, create_access_token
from backend.app.models.user import User
from backend.app.models.node import StorageNode
from backend.app.models.bucket import Bucket


@pytest.mark.anyio
async def test_password_hashing():
    raw_pwd = "SuperSecretPassword123!"
    hashed = get_password_hash(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


@pytest.mark.anyio
async def test_storage_nodes_seeded():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(StorageNode))
        nodes = result.scalars().all()
        assert len(nodes) == 6
        zones = {n.zone for n in nodes}
        assert zones == {"ZONE_A", "ZONE_B"}
        zone_a = [n for n in nodes if n.zone == "ZONE_A"]
        zone_b = [n for n in nodes if n.zone == "ZONE_B"]
        assert len(zone_a) == 3
        assert len(zone_b) == 3


@pytest.mark.anyio
async def test_users_and_buckets_seeded():
    async with AsyncSessionLocal() as session:
        # Check admin user
        admin_res = await session.execute(select(User).where(User.email == "admin@nexvault.io"))
        admin = admin_res.scalar_one_or_none()
        assert admin is not None
        assert admin.role == "ADMIN"
        assert verify_password("admin123", admin.hashed_password) is True

        # Check buckets
        b_res = await session.execute(select(Bucket))
        buckets = b_res.scalars().all()
        assert len(buckets) >= 2
        b_names = {b.name for b in buckets}
        assert "production-data" in b_names
        assert "analytics-logs" in b_names


if __name__ == "__main__":
    pytest.main(["-v", __file__])
