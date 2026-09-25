import io
import uuid
import hashlib
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy import update
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.init_db import init_db
from app.core.database import get_session_factory
from app.models.storage_node import StorageNode
from app.services.node_client import node_client


@pytest_asyncio.fixture(autouse=True)
async def initialize_db():
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            update(StorageNode).values(status="HEALTHY", is_simulated_partitioned=False)
        )
        await session.commit()
    # Ensure physical daemons are online
    for port in range(5001, 5007):
        await node_client.bring_node_online("127.0.0.1", port)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient):
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": settings.INITIAL_ADMIN_EMAIL,
            "password": settings.INITIAL_ADMIN_PASSWORD,
        },
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_headers(client: AsyncClient):
    user_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={"email": user_email, "password": "UserPassword123!", "full_name": "Standard User"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "UserPassword123!"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_chaos_admin_authorization_enforced(client: AsyncClient, user_headers: dict):
    """Verify standard non-admin USER is blocked with 403 Forbidden from all Chaos Lab endpoints."""
    endpoints = [
        ("/api/v1/admin/chaos/node-fail", {"node_id": "dummy", "action": "FAIL"}),
        ("/api/v1/admin/chaos/node-restore", {"node_id": "dummy"}),
        ("/api/v1/admin/chaos/corrupt-replica", {"random": True}),
        ("/api/v1/admin/chaos/network-partition", {"node_ids": ["dummy"], "partitioned": True}),
        ("/api/v1/admin/chaos/scan-integrity", {}),
        ("/api/v1/admin/chaos/rebalance", {}),
    ]

    for path, payload in endpoints:
        res = await client.post(path, json=payload, headers=user_headers)
        assert res.status_code == 403, f"Endpoint {path} must reject non-admin users"
        assert res.json()["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_chaos_node_failure_affects_reachability(client: AsyncClient, admin_headers: dict):
    """Verify that node failure takes the node offline and affects actual storage-node reachability."""
    nodes = (await client.get("/api/v1/nodes", headers=admin_headers)).json()
    target_node = nodes[0]

    try:
        # 1. Trigger node failure via Chaos Lab
        fail_res = await client.post(
            "/api/v1/admin/chaos/node-fail",
            json={"node_id": target_node["id"], "action": "FAIL"},
            headers=admin_headers,
        )
        assert fail_res.status_code == 200
        assert fail_res.json()["success"] is True

        # 2. Confirm node is marked FAILED in control plane
        node_status = (await client.get(f"/api/v1/nodes/{target_node['id']}/health", headers=admin_headers)).json()
        assert node_status["control_plane_status"] == "FAILED"

        # 3. Confirm physical reachability is lost
        daemon_health = await node_client.check_health(target_node["host"], target_node["port"])
        assert daemon_health is None, "Physical storage node must be unreachable after failure injection"

        # 4. Restore node
        restore_res = await client.post(
            "/api/v1/admin/chaos/node-restore",
            json={"node_id": target_node["id"]},
            headers=admin_headers,
        )
        assert restore_res.status_code == 200
        assert restore_res.json()["success"] is True

        # 5. Confirm node is marked HEALTHY and physically reachable
        daemon_health_after = await node_client.check_health(target_node["host"], target_node["port"])
        assert daemon_health_after is not None, "Physical storage node must be reachable after restore"
        assert daemon_health_after["status"] == "HEALTHY"

    finally:
        # Revert
        await client.post(
            "/api/v1/admin/chaos/node-restore",
            json={"node_id": target_node["id"]},
            headers=admin_headers,
        )


@pytest.mark.asyncio
async def test_chaos_replica_corruption_modifies_physical_data(client: AsyncClient, admin_headers: dict):
    """Verify that replica corruption physically modifies stored bytes on disk."""
    # 1. Upload an object
    b_name = f"chaos-corrupt-{uuid.uuid4().hex[:6]}"
    await client.post("/api/v1/buckets", json={"name": b_name}, headers=admin_headers)

    payload = b"ORIGINAL_CLEAN_UNTOUCHED_STORAGE_PAYLOAD_12345"
    up_res = await client.post(
        f"/api/v1/buckets/{b_name}/objects/upload",
        data={"key": "target.bin"},
        files={"file": ("target.bin", io.BytesIO(payload), "application/octet-stream")},
        headers=admin_headers,
    )
    assert up_res.status_code == 201
    replicas = up_res.json()["current_version"]["replicas"]
    first_replica = replicas[0]

    # Verify original file content on disk
    matched_files = list(Path("./storage").glob(f"*/{first_replica['id']}.bin"))
    assert len(matched_files) == 1
    disk_file = matched_files[0]
    with open(disk_file, "rb") as f:
        pre_corruption_bytes = f.read()
    assert pre_corruption_bytes == payload

    # 2. Trigger replica corruption via Chaos Lab
    corrupt_res = await client.post(
        "/api/v1/admin/chaos/corrupt-replica",
        json={"replica_id": first_replica["id"]},
        headers=admin_headers,
    )
    assert corrupt_res.status_code == 200
    assert corrupt_res.json()["success"] is True

    # 3. Confirm physical data on disk was modified (bitrot injected)
    with open(disk_file, "rb") as f:
        post_corruption_bytes = f.read()

    assert post_corruption_bytes != payload, "Physical bytes on disk must be modified by corruption"
    assert hashlib.sha256(post_corruption_bytes).hexdigest() != hashlib.sha256(payload).hexdigest()


@pytest.mark.asyncio
async def test_chaos_network_partition_affects_communication(client: AsyncClient, admin_headers: dict):
    """Verify that network partition isolates selected nodes from coordinator communication."""
    nodes = (await client.get("/api/v1/nodes", headers=admin_headers)).json()
    zone_b_nodes = [n for n in nodes if n["zone"] == "Zone-B"]
    zone_b_ids = [n["id"] for n in zone_b_nodes]

    try:
        # 1. Partition Zone B
        part_res = await client.post(
            "/api/v1/admin/chaos/network-partition",
            json={"node_ids": zone_b_ids, "partitioned": True},
            headers=admin_headers,
        )
        assert part_res.status_code == 200

        # 2. Confirm Zone B nodes are unreachable from coordinator
        for n in zone_b_nodes:
            daemon_check = await node_client.check_health(n["host"], n["port"])
            assert daemon_check is None, f"Node {n['name']} in Zone B must be unreachable during partition"

        # 3. Confirm Zone A nodes remain online and healthy
        zone_a_nodes = [n for n in nodes if n["zone"] == "Zone-A"]
        for n in zone_a_nodes:
            daemon_check = await node_client.check_health(n["host"], n["port"])
            assert daemon_check is not None, f"Node {n['name']} in Zone A must remain reachable"

    finally:
        # Revert partition
        await client.post(
            "/api/v1/admin/chaos/network-partition",
            json={"node_ids": zone_b_ids, "partitioned": False},
            headers=admin_headers,
        )


@pytest.mark.asyncio
async def test_chaos_integrity_scan_and_rebalance(client: AsyncClient, admin_headers: dict):
    """Verify integrity scan and rebalance operations execute and log telemetry."""
    # 1. Integrity Scan
    scan_res = await client.post("/api/v1/admin/chaos/scan-integrity", headers=admin_headers)
    assert scan_res.status_code == 200
    assert scan_res.json()["success"] is True

    # 2. Rebalance
    reb_res = await client.post("/api/v1/admin/chaos/rebalance", headers=admin_headers)
    assert reb_res.status_code == 200
    assert reb_res.json()["success"] is True

    # 3. Verify Events Logged
    events_res = await client.get("/api/v1/admin/events", headers=admin_headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert any(e["category"] == "INTEGRITY" for e in events)
    assert any(e["category"] == "REPAIR" for e in events)
