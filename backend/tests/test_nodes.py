"""
Step 1 Verification: Test Storage Node Daemons
Tests independent processes on ports 5001-5006.
Verifies PUT, GET, HEAD, DELETE, List, Health, and Chaos Bit-Rot endpoints.
"""

import hashlib
import httpx
import pytest

NODE_PORTS = [5001, 5002, 5003, 5004, 5005, 5006]
BASE_URLS = [f"http://127.0.0.1:{p}" for p in NODE_PORTS]


def test_all_nodes_health():
    """Verify all 6 nodes are running independently and report correct zones."""
    # Reset all node chaos states to HEALTHY first
    for port in NODE_PORTS:
        try:
            httpx.post(f"http://127.0.0.1:{port}/chaos/set-state", json={"state": "HEALTHY"}, timeout=1.0)
        except Exception:
            pass

    for port in NODE_PORTS:
        url = f"http://127.0.0.1:{port}/health"
        resp = httpx.get(url, timeout=3.0)
        assert resp.status_code == 200, f"Node on port {port} failed health check"
        data = resp.json()
        assert data["status"] == "HEALTHY"
        assert data["port"] == port
        expected_zone = "ZONE_A" if port in (5001, 5002, 5003) else "ZONE_B"
        assert data["zone"] == expected_zone
        print(f"✓ Node {data['node_id']} (Port {port}) is HEALTHY in {expected_zone}")


def test_put_get_head_delete_lifecycle():
    """Verify complete chunk lifecycle on node 1 (port 5001)."""
    blob_id = "test-blob-12345"
    test_data = b"Hello distributed systems world! Testing NEXVAULT node."
    expected_hash = hashlib.sha256(test_data).hexdigest()
    node_url = "http://127.0.0.1:5001"

    # 1. PUT
    put_resp = httpx.put(
        f"{node_url}/chunks/{blob_id}",
        content=test_data,
        headers={"Content-Type": "application/octet-stream"},
        timeout=3.0,
    )
    assert put_resp.status_code == 200
    put_json = put_resp.json()
    assert put_json["blob_id"] == blob_id
    assert put_json["sha256"] == expected_hash
    assert put_json["size"] == len(test_data)

    # 2. HEAD
    head_resp = httpx.head(f"{node_url}/chunks/{blob_id}", timeout=3.0)
    assert head_resp.status_code == 200
    assert head_resp.headers["x-content-sha256"] == expected_hash
    assert int(head_resp.headers["content-length"]) == len(test_data)

    # 3. GET
    get_resp = httpx.get(f"{node_url}/chunks/{blob_id}", timeout=3.0)
    assert get_resp.status_code == 200
    assert get_resp.content == test_data
    assert get_resp.headers["x-content-sha256"] == expected_hash

    # 4. DELETE
    del_resp = httpx.delete(f"{node_url}/chunks/{blob_id}", timeout=3.0)
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    # 5. Verify 404 after delete
    get_after = httpx.get(f"{node_url}/chunks/{blob_id}", timeout=3.0)
    assert get_after.status_code == 404


def test_bit_rot_corruption_injection():
    """Verify chaos bit-rot endpoint flips bytes and diverges from original SHA-256."""
    blob_id = "test-corrupt-target"
    original_data = b"Critical enterprise document bytes to test bit-rot detection"
    original_hash = hashlib.sha256(original_data).hexdigest()
    node_url = "http://127.0.0.1:5002"

    # PUT original
    httpx.put(f"{node_url}/chunks/{blob_id}", content=original_data)

    # Trigger chaos corruption
    corrupt_resp = httpx.post(f"{node_url}/chaos/corrupt/{blob_id}")
    assert corrupt_resp.status_code == 200
    corrupt_data = corrupt_resp.json()
    assert corrupt_data["corrupted"] is True
    corrupted_hash = corrupt_data["new_corrupted_sha256"]
    assert corrupted_hash != original_hash

    # GET chunk and verify it now has the corrupted hash
    get_resp = httpx.get(f"{node_url}/chunks/{blob_id}")
    assert get_resp.headers["x-content-sha256"] == corrupted_hash
    assert get_resp.content != original_data

    # Clean up
    httpx.delete(f"{node_url}/chunks/{blob_id}")


if __name__ == "__main__":
    pytest.main(["-v", __file__])
