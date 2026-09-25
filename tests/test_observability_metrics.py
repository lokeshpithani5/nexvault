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
        json={"email": user_email, "password": "UserPassword123!", "full_name": "Observability User"},
    )
    token = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": user_email, "password": "UserPassword123!"},
        )
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_events_authorization_and_standardized_format(client: AsyncClient, admin_headers: dict, user_headers: dict):
    """Verify admin can read events, standard USER is blocked with 403, and response is standardized."""
    # 1. Non-admin user gets 403 Forbidden
    user_res = await client.get("/api/v1/admin/events", headers=user_headers)
    assert user_res.status_code == 403

    # 2. Admin can read events
    admin_res = await client.get("/api/v1/admin/events", headers=admin_headers)
    assert admin_res.status_code == 200
    events = admin_res.json()
    assert isinstance(events, list)

    if events:
        first = events[0]
        # Verify standardized fields
        assert "timestamp" in first
        assert "event_type" in first
        assert "severity" in first
        assert "message" in first
        assert "node_id" in first
        assert "object_key" in first
        assert "details" in first


@pytest.mark.asyncio
async def test_admin_events_filtering(client: AsyncClient, admin_headers: dict):
    """Verify event filtering by event_type, severity, limit, and ordering."""
    # Trigger a known event
    nodes_res = await client.get("/api/v1/nodes", headers=admin_headers)
    nodes = nodes_res.json()
    assert len(nodes) >= 1
    target_node = nodes[0]

    # Node failure event
    await client.post(
        "/api/v1/admin/chaos/node-fail",
        json={"node_id": target_node["id"], "action": "FAIL"},
        headers=admin_headers,
    )

    # Filter by event_type=NODE_FAILED
    events_res = await client.get(
        "/api/v1/admin/events",
        params={"event_type": "NODE_FAILED", "limit": 10},
        headers=admin_headers,
    )
    assert events_res.status_code == 200
    failed_events = events_res.json()
    assert len(failed_events) >= 1
    for ev in failed_events:
        assert ev["event_type"] == "NODE_FAILED"
        assert ev["severity"] == "CRITICAL"

    # Restore node
    await client.post(
        "/api/v1/admin/chaos/node-restore",
        json={"node_id": target_node["id"]},
        headers=admin_headers,
    )

    # Filter by event_type=NODE_RESTORED
    restore_res = await client.get(
        "/api/v1/admin/events",
        params={"event_type": "NODE_RESTORED", "limit": 10},
        headers=admin_headers,
    )
    assert restore_res.status_code == 200
    restored_events = restore_res.json()
    assert len(restored_events) >= 1
    assert restored_events[0]["event_type"] == "NODE_RESTORED"

    # Verify chronological ordering (newest first)
    all_events_res = await client.get("/api/v1/admin/events?limit=20", headers=admin_headers)
    all_events = all_events_res.json()
    if len(all_events) >= 2:
        for i in range(len(all_events) - 1):
            assert all_events[i]["timestamp"] >= all_events[i + 1]["timestamp"]


@pytest.mark.asyncio
async def test_metrics_authorization_and_real_values(client: AsyncClient, admin_headers: dict, user_headers: dict):
    """Verify metrics authorization and that real non-fabricated values are returned."""
    # 1. Non-admin is blocked
    m_user = await client.get("/api/v1/admin/metrics", headers=user_headers)
    assert m_user.status_code == 403

    c_user = await client.get("/api/v1/admin/metrics/cluster", headers=user_headers)
    assert c_user.status_code == 403

    # 2. Admin retrieves real system metrics
    m_admin = await client.get("/api/v1/admin/metrics", headers=admin_headers)
    assert m_admin.status_code == 200
    metrics = m_admin.json()

    # Verify core required real metric keys
    assert "total_nodes" in metrics
    assert "healthy_nodes" in metrics
    assert "degraded_nodes" in metrics
    assert "failed_nodes" in metrics
    assert "recovering_nodes" in metrics
    assert "total_objects" in metrics
    assert "healthy_objects" in metrics
    assert "degraded_objects" in metrics
    assert "total_replicas" in metrics
    assert "healthy_replicas" in metrics
    assert "corrupted_replicas" in metrics
    assert "repair_jobs_pending" in metrics
    assert "repair_jobs_running" in metrics
    assert "repair_jobs_completed" in metrics
    assert "repair_jobs_failed" in metrics
    assert "replicas_repaired" in metrics
    assert "bytes_recovered" in metrics
    assert "total_logical_storage" in metrics
    assert "total_physical_storage" in metrics
    assert "storage_overhead" in metrics
    assert "cluster_utilization_percentage" in metrics
    assert "recovery_metrics" in metrics

    # Verify recovery_metrics structure
    rec = metrics["recovery_metrics"]
    assert "average_recovery_time_seconds" in rec
    assert "fastest_recovery_seconds" in rec
    assert "slowest_recovery_seconds" in rec
    assert "total_repairs" in rec
    assert "successful_repairs" in rec
    assert "failed_repairs" in rec


@pytest.mark.asyncio
async def test_node_failure_and_restore_changes_metrics(client: AsyncClient, admin_headers: dict):
    """Verify that failing and restoring a node changes real metrics dynamically."""
    initial_metrics = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    init_healthy = initial_metrics["healthy_nodes"]
    init_failed = initial_metrics["failed_nodes"]

    nodes_res = await client.get("/api/v1/nodes", headers=admin_headers)
    target_node = nodes_res.json()[0]

    # 1. Fail node
    await client.post(
        "/api/v1/admin/chaos/node-fail",
        json={"node_id": target_node["id"], "action": "FAIL"},
        headers=admin_headers,
    )

    failed_metrics = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert failed_metrics["failed_nodes"] == init_failed + 1
    assert failed_metrics["healthy_nodes"] == init_healthy - 1

    # Cluster summary also reflects change
    cluster_sum = (await client.get("/api/v1/admin/metrics/cluster", headers=admin_headers)).json()
    assert cluster_sum["node_counts"]["failed"] == init_failed + 1
    assert cluster_sum["node_counts"]["healthy"] == init_healthy - 1

    # 2. Restore node
    await client.post(
        "/api/v1/admin/chaos/node-restore",
        json={"node_id": target_node["id"]},
        headers=admin_headers,
    )

    restored_metrics = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert restored_metrics["failed_nodes"] == init_failed
    assert restored_metrics["healthy_nodes"] == init_healthy


@pytest.mark.asyncio
async def test_corruption_scan_and_repair_lifecycle_metrics_and_events(client: AsyncClient, admin_headers: dict):
    """Full lifecycle: upload object -> corrupt replica -> scan integrity -> repair replica -> verify all metrics and events."""
    # 1. Create bucket and upload object
    bucket_name = f"obs-bucket-{uuid.uuid4().hex[:6]}"
    b_res = await client.post("/api/v1/buckets", json={"name": bucket_name}, headers=admin_headers)
    assert b_res.status_code == 201

    payload = b"NEXVAULT Observability Test Data 12345"
    file_tuple = ("obs.txt", io.BytesIO(payload), "text/plain")
    up_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        files={"file": file_tuple},
        headers=admin_headers,
    )
    assert up_res.status_code == 201
    object_info = up_res.json()
    version_id = object_info["current_version"]["id"]

    # 2. Check metrics before corruption
    before_m = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    init_corrupted = before_m["corrupted_replicas"]

    # 3. Corrupt a replica
    corr_res = await client.post(
        "/api/v1/admin/chaos/corrupt-replica",
        json={"random": True},
        headers=admin_headers,
    )
    assert corr_res.status_code == 200
    corrupted_rep_id = corr_res.json()["affected_entities"]["replica_id"]

    # Verify metrics updated to reflect corruption
    after_corr_m = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert after_corr_m["corrupted_replicas"] == init_corrupted + 1

    # Verify REPLICA_CORRUPTED event
    corr_events = (
        await client.get("/api/v1/admin/events", params={"event_type": "REPLICA_CORRUPTED"}, headers=admin_headers)
    ).json()
    assert len(corr_events) >= 1
    assert corr_events[0]["event_type"] == "REPLICA_CORRUPTED"

    # 4. Run Integrity Scan
    scan_res = await client.post("/api/v1/admin/chaos/scan-integrity", headers=admin_headers)
    assert scan_res.status_code == 200

    # Verify scan events and latest integrity scan in metrics
    scan_m = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert scan_m["latest_integrity_scan_result"] is not None
    assert scan_m["latest_integrity_scan_result"]["event_type"] == "INTEGRITY_SCAN_COMPLETED"

    # 5. Create and Execute Repair Job
    # Pick target node
    nodes = (await client.get("/api/v1/nodes", headers=admin_headers)).json()
    target_node_id = nodes[0]["id"]

    repair_create_res = await client.post(
        "/api/v1/admin/repairs",
        json={
            "version_id": version_id,
            "target_node_id": target_node_id,
            "trigger_reason": "OBS_TEST_BITROT",
        },
        headers=admin_headers,
    )
    assert repair_create_res.status_code == 200
    job_id = repair_create_res.json()["id"]

    # Execute repair
    exec_res = await client.post(f"/api/v1/admin/repairs/{job_id}/execute", headers=admin_headers)
    assert exec_res.status_code == 200
    assert exec_res.json()["status"] == "COMPLETED"

    # 6. Verify Repair Metrics and Events
    final_m = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert final_m["repair_jobs_completed"] >= 1
    assert final_m["replicas_repaired"] >= 1
    assert final_m["recovery_metrics"]["successful_repairs"] >= 1
    assert final_m["recovery_metrics"]["average_recovery_time_seconds"] is not None

    # Verify all repair event types were emitted
    for ev_type in ["REPAIR_CREATED", "REPAIR_STARTED", "CHECKSUM_VERIFIED", "REPLICA_REBUILT", "OBJECT_HEALTHY"]:
        ev_list = (await client.get("/api/v1/admin/events", params={"event_type": ev_type}, headers=admin_headers)).json()
        assert len(ev_list) >= 1, f"Event {ev_type} not found in events"



@pytest.mark.asyncio
async def test_cluster_summary_consistency(client: AsyncClient, admin_headers: dict):
    """Verify /api/v1/admin/metrics/cluster is strictly consistent with /api/v1/admin/metrics."""
    metrics = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    cluster = (await client.get("/api/v1/admin/metrics/cluster", headers=admin_headers)).json()

    assert cluster["cluster_status"] in ["HEALTHY", "DEGRADED", "CRITICAL"]
    assert cluster["node_counts"]["total"] == metrics["total_nodes"]
    assert cluster["node_counts"]["healthy"] == metrics["healthy_nodes"]
    assert cluster["node_counts"]["failed"] == metrics["failed_nodes"]
    assert cluster["object_health"]["total"] == metrics["total_objects"]
    assert cluster["object_health"]["healthy"] == metrics["healthy_objects"]
    assert cluster["replica_health"]["total"] == metrics["total_replicas"]
    assert cluster["replica_health"]["corrupted"] == metrics["corrupted_replicas"]
    assert cluster["storage_utilization"]["used_capacity_bytes"] == metrics["total_physical_storage"]
    assert cluster["storage_utilization"]["logical_storage_bytes"] == metrics["total_logical_storage"]
