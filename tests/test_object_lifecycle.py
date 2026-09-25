import io
import uuid
import hashlib
from pathlib import Path
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.init_db import init_db


@pytest_asyncio.fixture(autouse=True)
async def initialize_db():
    await init_db()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_complete_object_lifecycle(client: AsyncClient):
    """Tests upload, physical node replication, download, versioning, and tombstone delete."""
    # 1. Signup and login
    user_email = f"object_tester_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={"email": user_email, "password": "TestPassword123!", "full_name": "Storage Tester"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": user_email, "password": "TestPassword123!"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Bucket
    bucket_name = f"lifecycle-bucket-{uuid.uuid4().hex[:8]}"
    b_res = await client.post(
        "/api/v1/buckets",
        json={"name": bucket_name},
        headers=headers,
    )
    assert b_res.status_code == 201

    # 3. Upload Object (v1)
    file_bytes_v1 = b"NEXVAULT: Resilient distributed storage payload version 1.0"
    v1_sha256 = hashlib.sha256(file_bytes_v1).hexdigest()
    object_key = "documents/specification.txt"

    upload_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        data={"key": object_key},
        files={"file": ("specification.txt", io.BytesIO(file_bytes_v1), "text/plain")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    obj_data = upload_res.json()
    assert obj_data["key"] == object_key
    assert obj_data["current_version"]["version_num"] == 1
    assert obj_data["current_version"]["sha256_checksum"] == v1_sha256
    assert obj_data["current_version"]["size_bytes"] == len(file_bytes_v1)

    replicas = obj_data["current_version"]["replicas"]
    # RF=3: 3 replicas should be placed
    assert len(replicas) == 3

    # Check zone distribution: at least one in Zone-A and one in Zone-B
    zones = [r["node_zone"] for r in replicas]
    assert "Zone-A" in zones
    assert "Zone-B" in zones

    # Check that actual physical files exist on disk in the storage directory
    for rep in replicas:
        rep_id = rep["id"]
        # Look for file in storage/nodeX/
        found_bin = list(Path("./storage").glob(f"*/{rep_id}.bin"))
        assert len(found_bin) == 1, f"Physical chunk file for replica {rep_id} must exist on disk"
        with open(found_bin[0], "rb") as f:
            disk_content = f.read()
        assert disk_content == file_bytes_v1

    # 4. Download Object (v1)
    download_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}",
        headers=headers,
    )
    assert download_res.status_code == 200
    assert download_res.content == file_bytes_v1
    assert download_res.headers.get("x-nexvault-checksum-sha256") == v1_sha256

    # 5. Concurrent / Consecutive Update: Upload Version 2 (Do not overwrite v1)
    file_bytes_v2 = b"NEXVAULT: Updated specification version 2.0 with enhanced redundancy"
    v2_sha256 = hashlib.sha256(file_bytes_v2).hexdigest()

    upload_v2_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        data={"key": object_key},
        files={"file": ("specification.txt", io.BytesIO(file_bytes_v2), "text/plain")},
        headers=headers,
    )
    assert upload_v2_res.status_code == 201
    v2_data = upload_v2_res.json()
    assert v2_data["current_version"]["version_num"] == 2
    assert v2_data["current_version"]["sha256_checksum"] == v2_sha256

    # 6. Verify object versions endpoint returns both versions
    versions_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}/versions",
        headers=headers,
    )
    assert versions_res.status_code == 200
    versions_list = versions_res.json()
    assert len(versions_list) == 2
    assert any(v["version_num"] == 1 and v["sha256_checksum"] == v1_sha256 for v in versions_list)
    assert any(v["version_num"] == 2 and v["sha256_checksum"] == v2_sha256 for v in versions_list)

    # 7. Download specific historical version (v1)
    dl_v1_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}?version=1",
        headers=headers,
    )
    assert dl_v1_res.status_code == 200
    assert dl_v1_res.content == file_bytes_v1

    # 8. Download latest version (v2 by default)
    dl_latest_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}",
        headers=headers,
    )
    assert dl_latest_res.status_code == 200
    assert dl_latest_res.content == file_bytes_v2

    # 9. Get detailed object breakdown (with replicas and zones)
    details_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}/details",
        headers=headers,
    )
    assert details_res.status_code == 200
    details = details_res.json()
    assert details["bucket_name"] == bucket_name
    assert details["key"] == object_key
    assert len(details["versions"]) == 2

    # 10. Delete Object (Creates Tombstone version)
    delete_res = await client.delete(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}",
        headers=headers,
    )
    assert delete_res.status_code == 200
    assert delete_res.json()["deleted"] is True
    assert delete_res.json()["tombstone_version"] == 3

    # 11. Read after delete should return 404 Not Found
    get_deleted_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}",
        headers=headers,
    )
    assert get_deleted_res.status_code == 404

    # 12. List objects should not list deleted objects
    list_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects",
        headers=headers,
    )
    assert list_res.status_code == 200
    assert not any(obj["key"] == object_key for obj in list_res.json())

    # 13. Historical version 1 can still be retrieved explicitly even after object deletion
    historical_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{object_key}?version=1",
        headers=headers,
    )
    assert historical_res.status_code == 200
    assert historical_res.content == file_bytes_v1


@pytest.mark.asyncio
async def test_read_transparent_failover_on_corrupt_replica(client: AsyncClient):
    """Verify that if one physical replica has bitrot, read transparently fails over to healthy replica."""
    user_email = f"failover_tester_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={"email": user_email, "password": "TestPassword123!", "full_name": "Failover Tester"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "TestPassword123!"},
        )
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    bucket_name = f"failover-bucket-{uuid.uuid4().hex[:8]}"
    await client.post("/api/v1/buckets", json={"name": bucket_name}, headers=headers)

    payload = b"CRITICAL_DATA_THAT_MUST_SURVIVE_REPLICA_CORRUPTION"
    obj_key = "critical.dat"

    upload_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        data={"key": obj_key},
        files={"file": ("critical.dat", io.BytesIO(payload), "application/octet-stream")},
        headers=headers,
    )
    assert upload_res.status_code == 201
    replicas = upload_res.json()["current_version"]["replicas"]
    first_replica = replicas[0]

    # Deliberately corrupt the first replica's physical file on disk
    corrupted_file = list(Path("./storage").glob(f"*/{first_replica['id']}.bin"))[0]
    with open(corrupted_file, "r+b") as f:
        data = bytearray(f.read())
        data[0] ^= 0xFF  # Flip bits
        f.seek(0)
        f.write(data)

    # Perform download: should detect corruption on replica 1 and transparently succeed from replica 2 or 3!
    download_res = await client.get(
        f"/api/v1/buckets/{bucket_name}/objects/{obj_key}",
        headers=headers,
    )
    assert download_res.status_code == 200
    assert download_res.content == payload
