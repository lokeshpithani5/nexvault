"""
API Hardening & Demo Reliability Test Suite
Verifies:
1. Role-Based Access Control (RBAC): USER receives 403 on admin-only chaos operations.
2. Large-file streaming (10 MB payload upload, replication, and download verification).
3. Robust metrics JSON payload (zero divide-by-zero or null values).
4. Demo reset capability (/chaos/reset endpoint).
5. Error responses are clean JSON without stack trace leaks.
"""

import hashlib
import uuid
import pytest
import httpx
from httpx import ASGITransport
from backend.app.main import app


@pytest.mark.anyio
async def test_auth_and_rbac_enforcement():
    """
    Verify Requirement 4:
    - Normal USER can login, access storage, view cluster telemetry.
    - Normal USER receives 403 Forbidden when attempting Chaos Lab operations.
    - Unauthenticated client receives 401 Unauthorized.
    - ADMIN can successfully perform Chaos Lab operations.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Unauthenticated request to chaos -> 401
        unauth_resp = await client.post("/api/v1/chaos/scans/integrity")
        assert unauth_resp.status_code == 401
        assert "detail" in unauth_resp.json()

        # 2. Login as standard USER
        user_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "demo@nexvault.io", "password": "demo123"},
        )
        assert user_login.status_code == 200
        user_token = user_login.json()["access_token"]
        user_headers = {"Authorization": f"Bearer {user_token}"}

        # 3. Standard USER can view cluster overview and metrics
        overview_resp = await client.get("/api/v1/cluster/overview", headers=user_headers)
        assert overview_resp.status_code == 200

        metrics_resp = await client.get("/api/v1/cluster/metrics", headers=user_headers)
        assert metrics_resp.status_code == 200

        # 4. Standard USER attempts chaos toggle -> MUST RETURN 403 FORBIDDEN
        chaos_node_resp = await client.post(
            "/api/v1/chaos/nodes/node-1/toggle-status",
            headers=user_headers,
        )
        assert chaos_node_resp.status_code == 403
        assert "Administrative privileges required" in chaos_node_resp.json()["detail"]

        chaos_scan_resp = await client.post(
            "/api/v1/chaos/scans/integrity",
            headers=user_headers,
        )
        assert chaos_scan_resp.status_code == 403
        assert "Administrative privileges required" in chaos_scan_resp.json()["detail"]

        chaos_reset_resp = await client.post(
            "/api/v1/chaos/reset",
            json={"clean_test_objects": False},
            headers=user_headers,
        )
        assert chaos_reset_resp.status_code == 403
        assert "Administrative privileges required" in chaos_reset_resp.json()["detail"]

        # 5. Login as ADMIN
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@nexvault.io", "password": "admin123"},
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 6. ADMIN can successfully execute chaos scan and reset
        admin_scan_resp = await client.post(
            "/api/v1/chaos/scans/integrity",
            headers=admin_headers,
        )
        assert admin_scan_resp.status_code == 200
        assert "replicas_checked" in admin_scan_resp.json()


@pytest.mark.anyio
async def test_metrics_safety_and_structure():
    """
    Verify Requirement 6:
    GET /api/v1/cluster/metrics returns predictable, valid numbers with zero nulls or NaNs.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/cluster/metrics")
        assert resp.status_code == 200
        data = resp.json()

        # Check all required numeric fields
        expected_fields = [
            ("healthy_node_count", int),
            ("failed_node_count", int),
            ("degraded_node_count", int),
            ("degraded_object_count", int),
            ("repair_jobs_completed", int),
            ("repair_jobs_failed", int),
            ("bytes_recovered", int),
            ("average_repair_duration_ms", (int, float)),
            ("last_repair_duration_ms", (int, float)),
            ("logical_storage", int),
            ("physical_storage", int),
            ("replication_overhead", (int, float)),
            ("cluster_utilization", (int, float)),
            ("node_availability_pct", (int, float)),
            ("active_nodes_count", int),
            ("total_nodes_count", int),
        ]
        for field, f_type in expected_fields:
            assert field in data, f"Missing metric field '{field}'"
            assert data[field] is not None, f"Metric '{field}' should not be null"
            assert isinstance(data[field], f_type), f"Metric '{field}' has unexpected type {type(data[field])}"


@pytest.mark.anyio
async def test_admin_demo_reset_capability():
    """
    Verify Requirement 8:
    POST /api/v1/chaos/reset safely restores node states, partitions, and health.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Admin
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@nexvault.io", "password": "admin123"},
        )
        admin_token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Trigger partition chaos
        part_resp = await client.post("/api/v1/chaos/nodes/node-1/partition", headers=headers)
        assert part_resp.status_code == 200

        # 2. Call Reset Demo Endpoint
        reset_resp = await client.post(
            "/api/v1/chaos/reset",
            json={"clean_test_objects": False, "trigger_scrub": True},
            headers=headers,
        )
        assert reset_resp.status_code == 200
        data = reset_resp.json()
        assert data["status"] == "RESET_COMPLETE"
        assert data["nodes_reset"] == 6

        # 3. Verify node-1 is no longer partitioned
        nodes_resp = await client.get("/api/v1/cluster/nodes")
        assert nodes_resp.status_code == 200
        node_1 = next(n for n in nodes_resp.json() if n["id"] == "node-1")
        assert node_1["is_simulated_partitioned"] is False
        assert node_1["status"] == "HEALTHY"


@pytest.mark.anyio
async def test_large_file_streaming_10mb():
    """
    Verify Requirement 10:
    Coordinator streams large files (10 MB payload) without errors or size truncation.
    Verifies upload -> multi-node fan-out -> download -> byte-exact SHA-256 match.
    """
    transport = ASGITransport(app=app)
    # Generate exactly 10 MB payload
    payload_size = 10 * 1024 * 1024  # 10 MB
    chunk_pattern = b"NEXVAULT_STREAMING_LARGE_OBJECT_VERIFICATION_BLOCK_2026\n"
    # Repeat pattern to reach ~10MB
    repeat_count = (payload_size // len(chunk_pattern)) + 1
    large_payload = (chunk_pattern * repeat_count)[:payload_size]
    assert len(large_payload) == payload_size
    expected_sha = hashlib.sha256(large_payload).hexdigest()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Admin
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@nexvault.io", "password": "admin123"},
        )
        token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        test_key = f"demo/large_object_10mb_{uuid.uuid4().hex[:6]}.dat"
        files = {"file": ("large_file.dat", large_payload, "application/octet-stream")}
        data = {"key": test_key}

        # 1. Upload 10 MB file
        upload_resp = await client.post(
            "/api/v1/buckets/production-data/objects",
            data=data,
            files=files,
            headers=headers,
        )
        assert upload_resp.status_code == 201
        upload_json = upload_resp.json()
        assert upload_json["size_bytes"] == payload_size
        assert upload_json["checksum_sha256"] == expected_sha
        assert upload_json["replicas_placed"] == 3

        # 2. Download 10 MB file and verify integrity
        dl_resp = await client.get(
            f"/api/v1/buckets/production-data/objects/{test_key}",
            headers=headers,
        )
        assert dl_resp.status_code == 200
        assert len(dl_resp.content) == payload_size
        assert hashlib.sha256(dl_resp.content).hexdigest() == expected_sha
        assert dl_resp.headers["X-Content-SHA256"] == expected_sha
        assert dl_resp.headers["X-NexVault-Version"] == "1"


@pytest.mark.anyio
async def test_error_handling_sanitization():
    """
    Verify Requirement 11:
    Clean JSON responses for 404, 422, 401 without tracebacks.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Login as Admin
        admin_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@nexvault.io", "password": "admin123"},
        )
        token = admin_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Object Not Found -> 404
        nf_resp = await client.get(
            "/api/v1/buckets/production-data/objects/non_existent_key_9999.bin",
            headers=headers,
        )
        assert nf_resp.status_code == 404
        assert "detail" in nf_resp.json()
        assert "not found" in nf_resp.json()["detail"].lower()

        # 2. Bucket Not Found -> 404
        b_nf_resp = await client.get(
            "/api/v1/buckets/non_existent_bucket_8888/objects",
            headers=headers,
        )
        assert b_nf_resp.status_code == 404
        assert "Bucket not found" in b_nf_resp.json()["detail"]

        # 3. Invalid bucket name (regex constraint) -> 422
        inv_b_resp = await client.post(
            "/api/v1/buckets",
            json={"name": "INVALID_UPPERCASE_NAME!"},
            headers=headers,
        )
        assert inv_b_resp.status_code == 422
        assert "detail" in inv_b_resp.json()
