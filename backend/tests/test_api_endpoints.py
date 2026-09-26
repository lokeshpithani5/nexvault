"""
Step 7 Verification: Full Coordinator REST API Endpoints Integration Test
"""

import uuid
import httpx
import pytest
from httpx import ASGITransport
from backend.app.main import app


@pytest.mark.anyio
async def test_full_api_workflow():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Root
        root_resp = await client.get("/")
        assert root_resp.status_code == 200
        assert root_resp.json()["product"] == "NEXVAULT"

        # 2. Login as Admin
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@nexvault.io", "password": "admin123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 3. Get /auth/me
        me_resp = await client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "admin@nexvault.io"
        assert me_resp.json()["role"] == "ADMIN"

        # 4. Create Bucket
        bucket_name = f"api-test-bucket-{uuid.uuid4().hex[:6]}"
        b_create = await client.post(
            "/api/v1/buckets",
            json={"name": bucket_name, "replication_factor": 2},
            headers=headers,
        )
        assert b_create.status_code == 201
        assert b_create.json()["name"] == bucket_name
        assert b_create.json()["replication_factor"] == 2

        # 5. Upload Object
        test_content = b"NEXVAULT End-to-End API Object Upload Test Payload"
        files = {"file": ("test_doc.txt", test_content, "text/plain")}
        data = {"key": "docs/test_doc.txt"}
        upload_resp = await client.post(
            f"/api/v1/buckets/{bucket_name}/objects",
            data=data,
            files=files,
            headers=headers,
        )
        assert upload_resp.status_code == 201
        assert upload_resp.json()["status"] == "UPLOADED"
        assert upload_resp.json()["replicas_placed"] == 2

        # 6. List Objects in Bucket
        list_resp = await client.get(f"/api/v1/buckets/{bucket_name}/objects", headers=headers)
        assert list_resp.status_code == 200
        items = list_resp.json()
        assert len(items) >= 1
        assert items[0]["key"] == "docs/test_doc.txt"

        # 7. Download Object
        dl_resp = await client.get(f"/api/v1/buckets/{bucket_name}/objects/docs/test_doc.txt", headers=headers)
        assert dl_resp.status_code == 200
        assert dl_resp.content == test_content

        # 8. Get Advanced Object Details
        details_resp = await client.get(
            f"/api/v1/buckets/{bucket_name}/objects/docs/test_doc.txt/details",
            headers=headers,
        )
        assert details_resp.status_code == 200
        details = details_resp.json()
        assert details["key"] == "docs/test_doc.txt"
        assert len(details["versions"]) >= 1
        assert len(details["versions"][0]["replicas"]) == 2
        print(f"✓ Advanced details returned replica topology: {[r['node_id'] for r in details['versions'][0]['replicas']]}")

        # 9. Cluster Overview & Nodes
        ov_resp = await client.get("/api/v1/cluster/overview")
        assert ov_resp.status_code == 200
        assert ov_resp.json()["nodes"]["total"] == 6

        nodes_resp = await client.get("/api/v1/cluster/nodes")
        assert nodes_resp.status_code == 200
        assert len(nodes_resp.json()) == 6

        # 10. Metrics
        metrics_resp = await client.get("/api/v1/cluster/metrics")
        assert metrics_resp.status_code == 200
        assert "overhead" in metrics_resp.json()

        # 11. Chaos Lab: Toggle node status
        toggle_resp = await client.post(
            "/api/v1/chaos/nodes/node-3/toggle-status",
            headers=headers,
        )
        assert toggle_resp.status_code == 200
        # Restore
        await client.post("/api/v1/chaos/nodes/node-3/toggle-status", headers=headers)
        print("✓ Full API workflow verified successfully!")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
