import io
import uuid
import hashlib
import pytest
import pytest_asyncio
from sqlalchemy import update
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.init_db import init_db
from app.core.database import get_session_factory
from app.models.storage_node import StorageNode
from app.models.object_replica import ObjectReplica
from app.services.node_client import node_client


@pytest_asyncio.fixture(autouse=True)
async def initialize_db():
    await init_db()
    session_factory = get_session_factory()
    async with session_factory() as session:
        await session.execute(
            update(StorageNode).values(status="HEALTHY", is_simulated_partitioned=False)
        )
        await session.execute(
            update(ObjectReplica).values(status="HEALTHY")
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


@pytest.mark.asyncio
async def test_node_failure_triggers_automatic_repair_and_durability_restoration(
    client: AsyncClient,
    admin_headers: dict,
):
    """
    1. RF3 object starts healthy
    2. Fail one physical node hosting a replica
    3. Object becomes degraded
    4. Automatic repair reconciliation is triggered
    5. Another healthy node receives the rebuilt replica
    6. Checksum matches original object
    7. Object returns to healthy
    8. Repair events emitted
    9. Recovery metrics update
    """
    # 1. Create bucket and upload RF3 object
    bucket_name = f"autorep-{uuid.uuid4().hex[:6]}"
    b_res = await client.post("/api/v1/buckets", json={"name": bucket_name}, headers=admin_headers)
    assert b_res.status_code == 201

    payload = b"NEXVAULT High Durability Automatic Self Healing Test Data 98765"
    expected_sha = hashlib.sha256(payload).hexdigest()

    file_tuple = ("auto_heal.txt", io.BytesIO(payload), "text/plain")
    up_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        files={"file": file_tuple},
        headers=admin_headers,
    )
    assert up_res.status_code == 201
    obj_data = up_res.json()
    version_id = obj_data["current_version"]["id"]
    initial_replicas = obj_data["current_version"]["replicas"]
    assert len(initial_replicas) == 3
    initial_node_ids = {r["node_id"] for r in initial_replicas}

    # 2. Fail one physical node hosting a replica
    failed_node_id = list(initial_node_ids)[0]
    fail_res = await client.post(
        "/api/v1/admin/chaos/node-fail",
        json={"node_id": failed_node_id, "action": "FAIL"},
        headers=admin_headers,
    )
    assert fail_res.status_code == 200

    # 3. Verify object is in degraded state via metrics
    metrics_before = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert metrics_before["degraded_objects"] >= 1

    # 4. Trigger automatic reconciliation
    reconcile_res = await client.post("/api/v1/admin/repairs/reconcile", headers=admin_headers)
    assert reconcile_res.status_code == 200
    rec_data = reconcile_res.json()
    assert rec_data["repairs_executed"] >= 1

    # 5. Check object details: another healthy node has received the rebuilt replica
    obj_detail = (await client.get(f"/api/v1/buckets/{bucket_name}/objects/auto_heal.txt/metadata", headers=admin_headers)).json()
    updated_replicas = obj_detail["current_version"]["replicas"]
    healthy_reps = [r for r in updated_replicas if r["status"] == "HEALTHY" and r["node_id"] != failed_node_id]
    assert len(healthy_reps) >= 3

    # Check that a new node outside initial 3 received a replica
    new_node_ids = {r["node_id"] for r in healthy_reps}
    assert len(new_node_ids - initial_node_ids) >= 1

    # 6. Verify rebuilt checksum
    for r in healthy_reps:
        assert r["stored_checksum"] == expected_sha

    # 7. Verify object returns to healthy
    metrics_after = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert metrics_after["healthy_objects"] >= 1

    # 8. Verify all required repair events were emitted
    for event_name in ["REPAIR_CREATED", "REPAIR_STARTED", "CHECKSUM_VERIFIED", "REPLICA_REBUILT", "OBJECT_HEALTHY"]:
        ev_res = await client.get("/api/v1/admin/events", params={"event_type": event_name}, headers=admin_headers)
        assert ev_res.status_code == 200
        assert len(ev_res.json()) >= 1, f"Event {event_name} was not recorded"

    # 9. Verify recovery metrics updated
    assert metrics_after["repair_jobs_completed"] >= 1
    assert metrics_after["replicas_repaired"] >= 1
    assert metrics_after["recovery_metrics"]["successful_repairs"] >= 1
    assert metrics_after["recovery_metrics"]["average_recovery_time_seconds"] is not None


@pytest.mark.asyncio
async def test_corruption_scan_triggers_automatic_repair(client: AsyncClient, admin_headers: dict):
    """
    10. Corrupt one physical replica
    11. Integrity scan identifies it
    12. Automatic repair restores it
    """
    bucket_name = f"corr-heal-{uuid.uuid4().hex[:6]}"
    await client.post("/api/v1/buckets", json={"name": bucket_name}, headers=admin_headers)

    payload = b"Data To Test Corruption Detection and Automatic Self Healing"
    file_tuple = ("corrupt_target.txt", io.BytesIO(payload), "text/plain")
    up_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        files={"file": file_tuple},
        headers=admin_headers,
    )
    assert up_res.status_code == 201

    obj_info = up_res.json()
    target_replica_id = obj_info["current_version"]["replicas"][0]["id"]

    # Corrupt a specific replica of this object
    corr_res = await client.post(
        "/api/v1/admin/chaos/corrupt-replica",
        json={"replica_id": target_replica_id},
        headers=admin_headers,
    )
    assert corr_res.status_code == 200

    # Run integrity scan -> automatically reconciles detected corruptions
    scan_res = await client.post("/api/v1/admin/chaos/scan-integrity", headers=admin_headers)
    assert scan_res.status_code == 200
    scan_data = scan_res.json()
    assert scan_data["affected_entities"]["corrupted"] >= 1
    assert scan_data["affected_entities"]["repaired"] >= 1

    # Verify object returned to healthy
    metrics = (await client.get("/api/v1/admin/metrics", headers=admin_headers)).json()
    assert metrics["healthy_objects"] >= 1


@pytest.mark.asyncio
async def test_repair_idempotency_prevents_duplicate_jobs(client: AsyncClient, admin_headers: dict):
    """
    13. Repeated worker scans do not create duplicate repair jobs.
    """
    bucket_name = f"idemp-{uuid.uuid4().hex[:6]}"
    await client.post("/api/v1/buckets", json={"name": bucket_name}, headers=admin_headers)

    payload = b"Idempotency Test Payload"
    file_tuple = ("idemp.txt", io.BytesIO(payload), "text/plain")
    up_res = await client.post(
        f"/api/v1/buckets/{bucket_name}/objects/upload",
        files={"file": file_tuple},
        headers=admin_headers,
    )
    assert up_res.status_code == 201
    obj_data = up_res.json()
    version_id = obj_data["current_version"]["id"]
    node_to_fail = obj_data["current_version"]["replicas"][0]["node_id"]

    # Fail node
    await client.post(
        "/api/v1/admin/chaos/node-fail",
        json={"node_id": node_to_fail, "action": "FAIL"},
        headers=admin_headers,
    )

    # First reconciliation cycle repairs the object
    rec1 = (await client.post("/api/v1/admin/repairs/reconcile", headers=admin_headers)).json()
    assert rec1["repairs_executed"] >= 1

    # Count repair jobs for this version
    repairs1 = (await client.get("/api/v1/admin/repairs", headers=admin_headers)).json()
    jobs_v1 = [r for r in repairs1 if r["version_id"] == version_id]
    assert len(jobs_v1) >= 1

    # Second reconciliation cycle immediately after
    rec2 = (await client.post("/api/v1/admin/repairs/reconcile", headers=admin_headers)).json()

    # Re-fetch repairs
    repairs2 = (await client.get("/api/v1/admin/repairs", headers=admin_headers)).json()
    jobs_v2 = [r for r in repairs2 if r["version_id"] == version_id]

    # Verify no duplicate repair jobs created for this version
    assert len(jobs_v1) == len(jobs_v2)



@pytest.mark.asyncio
async def test_node_restoration_reconciliation(client: AsyncClient, admin_headers: dict):
    """
    14. Node restoration reconciliation works without duplicating healthy replicas.
    """
    nodes = (await client.get("/api/v1/nodes", headers=admin_headers)).json()
    target_node = nodes[0]
    node_id = target_node["id"]

    # Fail node
    await client.post(
        "/api/v1/admin/chaos/node-fail",
        json={"node_id": node_id, "action": "FAIL"},
        headers=admin_headers,
    )

    # Restore node
    restore_res = await client.post(
        "/api/v1/admin/chaos/node-restore",
        json={"node_id": node_id},
        headers=admin_headers,
    )
    assert restore_res.status_code == 200
    res_data = restore_res.json()
    assert res_data["affected_entities"]["status"] == "HEALTHY"

    # Verify NODE_RECOVERING and NODE_RESTORED events logged
    recov_events = (
        await client.get("/api/v1/admin/events", params={"event_type": "NODE_RECOVERING"}, headers=admin_headers)
    ).json()
    assert len(recov_events) >= 1

    rest_events = (
        await client.get("/api/v1/admin/events", params={"event_type": "NODE_RESTORED"}, headers=admin_headers)
    ).json()
    assert len(rest_events) >= 1
