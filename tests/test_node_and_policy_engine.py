import io
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import update
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.init_db import init_db
from app.core.database import get_session_factory
from app.models.storage_node import StorageNode


@pytest_asyncio.fixture(autouse=True)
async def initialize_db():
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            update(StorageNode).values(status="HEALTHY", is_simulated_partitioned=False)
        )
        await session.commit()


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


@pytest.mark.asyncio
async def test_list_nodes_metadata(client: AsyncClient, admin_headers: dict):
    """Verify all 6 nodes return complete metadata."""
    res = await client.get("/api/v1/nodes", headers=admin_headers)
    assert res.status_code == 200
    nodes = res.json()
    assert len(nodes) == 6

    for n in nodes:
        assert "id" in n
        assert "host" in n
        assert "port" in n
        assert n["zone"] in ["Zone-A", "Zone-B"]
        assert n["status"] in ["HEALTHY", "DEGRADED", "FAILED", "RECOVERING"]
        assert n["total_capacity_bytes"] > 0
        assert "used_capacity_bytes" in n
        assert "last_heartbeat" in n


@pytest.mark.asyncio
async def test_node_and_cluster_health(client: AsyncClient, admin_headers: dict):
    """Verify individual node health check and cluster-wide health matrix."""
    # List nodes to get an ID
    nodes_res = await client.get("/api/v1/nodes", headers=admin_headers)
    node1 = nodes_res.json()[0]

    # Individual node health
    node_h_res = await client.get(f"/api/v1/nodes/{node1['id']}/health", headers=admin_headers)
    assert node_h_res.status_code == 200
    h_data = node_h_res.json()
    assert h_data["name"] == node1["name"]
    assert h_data["is_reachable"] is True
    assert h_data["free_capacity_bytes"] > 0

    # Cluster health
    cluster_res = await client.get("/api/v1/nodes/cluster/health", headers=admin_headers)
    assert cluster_res.status_code == 200
    c_data = cluster_res.json()
    assert c_data["cluster_status"] in ["HEALTHY", "DEGRADED"]
    assert c_data["total_nodes"] == 6
    assert "Zone-A" in c_data["zones"]
    assert "Zone-B" in c_data["zones"]
    assert c_data["zones"]["Zone-A"]["total"] == 3
    assert c_data["zones"]["Zone-B"]["total"] == 3


@pytest.mark.asyncio
async def test_policy_retrieval_and_safe_update(client: AsyncClient, admin_headers: dict):
    """Verify policy retrieval, safe update, and rejection of unsafe policy configurations."""
    # 1. Retrieve all policies
    res = await client.get("/api/v1/policies", headers=admin_headers)
    assert res.status_code == 200
    policies = res.json()
    names = [p["name"] for p in policies]
    assert "standard-rf3" in names
    assert "available-rf3" in names
    assert "light-rf2" in names
    assert "ec-4-2" in names

    std_policy = next(p for p in policies if p["name"] == "standard-rf3")
    assert std_policy["availability_mode"] == "DURABILITY_FIRST"

    avail_policy = next(p for p in policies if p["name"] == "available-rf3")
    assert avail_policy["availability_mode"] == "AVAILABILITY_FIRST"

    # 2. Safe Update
    update_res = await client.put(
        f"/api/v1/policies/{std_policy['id']}",
        json={"description": "Updated enterprise durability policy description"},
        headers=admin_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["description"] == "Updated enterprise durability policy description"

    # 3. Unsafe Update Rejection: min_write_quorum (5) > replication_factor (3) -> 409 Conflict
    unsafe_res = await client.put(
        f"/api/v1/policies/{std_policy['id']}",
        json={"min_write_quorum": 5, "replication_factor": 3},
        headers=admin_headers,
    )
    assert unsafe_res.status_code == 409
    assert "cannot exceed replication factor" in unsafe_res.json()["message"]


@pytest.mark.asyncio
async def test_availability_first_vs_durability_first(client: AsyncClient, admin_headers: dict):
    """Verify that DURABILITY_FIRST blocks writes when quorum cannot be met, while AVAILABILITY_FIRST succeeds degraded."""
    # 1. Find the policies
    policies_res = await client.get("/api/v1/policies", headers=admin_headers)
    policies = policies_res.json()
    durability_pol = next(p for p in policies if p["name"] == "standard-rf3")
    avail_pol = next(p for p in policies if p["name"] == "available-rf3")

    # Create buckets with the two distinct policies
    d_bucket = f"durability-bkt-{uuid.uuid4().hex[:6]}"
    a_bucket = f"avail-bkt-{uuid.uuid4().hex[:6]}"

    await client.post(
        "/api/v1/buckets",
        json={"name": d_bucket, "policy_id": durability_pol["id"]},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/buckets",
        json={"name": a_bucket, "policy_id": avail_pol["id"]},
        headers=admin_headers,
    )

    # 2. Get all nodes and isolate 5 of the 6 nodes using network partition simulation
    nodes = (await client.get("/api/v1/nodes", headers=admin_headers)).json()
    isolated_node_ids = [n["id"] for n in nodes[1:]]  # Leave only 1 node available (node 0)

    partition_res = await client.post(
        "/api/v1/admin/chaos/network-partition",
        json={"node_ids": isolated_node_ids, "partitioned": True},
        headers=admin_headers,
    )
    assert partition_res.status_code == 200

    try:
        payload = b"CRITICAL_OBJECT_QUORUM_TEST"

        # 3. DURABILITY_FIRST attempt: with only 1 healthy node and W=2 required -> MUST FAIL WITH 503
        d_res = await client.post(
            f"/api/v1/buckets/{d_bucket}/objects/upload",
            data={"key": "test_quorum.txt"},
            files={"file": ("test.txt", io.BytesIO(payload), "text/plain")},
            headers=admin_headers,
        )
        assert d_res.status_code == 503
        assert d_res.json()["code"] == "QUORUM_NOT_REACHED"

        # 4. AVAILABILITY_FIRST attempt: with only 1 healthy node -> MUST SUCCEED (degraded write mode)
        a_res = await client.post(
            f"/api/v1/buckets/{a_bucket}/objects/upload",
            data={"key": "test_avail.txt"},
            files={"file": ("test.txt", io.BytesIO(payload), "text/plain")},
            headers=admin_headers,
        )
        assert a_res.status_code == 201
        assert a_res.json()["current_version"]["size_bytes"] == len(payload)
        assert len(a_res.json()["current_version"]["replicas"]) == 1

    finally:
        # Revert network partition so cluster is back to healthy
        await client.post(
            "/api/v1/admin/chaos/network-partition",
            json={"node_ids": isolated_node_ids, "partitioned": False},
            headers=admin_headers,
        )


@pytest.mark.asyncio
async def test_heartbeat_sweep_and_events(client: AsyncClient, admin_headers: dict):
    """Verify heartbeat sweep records node responses and logs events on state transitions."""
    nodes = (await client.get("/api/v1/nodes", headers=admin_headers)).json()
    first_node = nodes[0]

    # Partition first node
    await client.post(
        "/api/v1/admin/chaos/network-partition",
        json={"node_ids": [first_node["id"]], "partitioned": True},
        headers=admin_headers,
    )

    # Run heartbeat sweep -> node status transitions to DEGRADED
    sweep_res = await client.post("/api/v1/nodes/sweep", headers=admin_headers)
    assert sweep_res.status_code == 200

    # Verify event logged
    events_res = await client.get("/api/v1/admin/events", headers=admin_headers)
    assert events_res.status_code == 200
    events = events_res.json()
    assert any(e["category"] == "NODE" and first_node["name"] in e["message"] for e in events)

    # Revert partition
    await client.post(
        "/api/v1/admin/chaos/network-partition",
        json={"node_ids": [first_node["id"]], "partitioned": False},
        headers=admin_headers,
    )
    # Sweep again -> restored to HEALTHY
    await client.post("/api/v1/nodes/sweep", headers=admin_headers)
