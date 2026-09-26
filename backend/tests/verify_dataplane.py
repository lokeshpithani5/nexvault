"""
NEXVAULT Data Plane Comprehensive Verification Script
Executes all required data-plane verification checks:
1. End-to-end PUT, HEAD, GET, physical disk verification, SHA-256 match, DELETE, 404 verification on Node 1
2. Independent failure/recovery of Node 3 while Nodes 1, 2, 4, 5, 6 stay online
3. Node isolation verification between Node 1 and Node 4
4. Large-file streaming verification (10 MB payload)
5. Security / Path-traversal rejection verification (../, ../../)
"""

import sys
import os
import hashlib
import time
from pathlib import Path
import httpx

# Ensure UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT_DIR = Path(__file__).parent.parent.parent.resolve()
NODE_PORTS = [5001, 5002, 5003, 5004, 5005, 5006]


def verify_all_nodes_healthy():
    print("\n--- [Step 5] Checking All 6 Nodes Health & Independence ---")
    for port in NODE_PORTS:
        url = f"http://127.0.0.1:{port}/health"
        r = httpx.get(url, timeout=3.0)
        assert r.status_code == 200, f"Node on port {port} not healthy"
        data = r.json()
        assert data["status"] == "HEALTHY"
        print(f"  ✓ {data['node_id']} (Port {port}, {data['zone']}) is HEALTHY, {data['chunk_count']} chunks on disk")


def test_node1_end_to_end():
    print("\n--- [Step 6] Real End-to-End Test on Node 1 (Port 5001) ---")
    blob_id = "test-e2e-verification-blob"
    original_bytes = b"NEXVAULT Data Plane Verification: Resilience and strict plane separation!\n" * 50
    expected_sha256 = hashlib.sha256(original_bytes).hexdigest()
    node1_url = "http://127.0.0.1:5001"

    # 1. PUT
    print(f"  1. PUT /chunks/{blob_id} ({len(original_bytes)} bytes)...")
    put_resp = httpx.put(
        f"{node1_url}/chunks/{blob_id}",
        content=original_bytes,
        headers={"Content-Type": "application/octet-stream"},
        timeout=5.0,
    )
    assert put_resp.status_code == 200, f"PUT failed: {put_resp.text}"
    put_data = put_resp.json()
    assert put_data["sha256"] == expected_sha256
    print(f"     ✓ PUT returned status 200, computed SHA-256 matches: {expected_sha256}")

    # 2. Check Physical File on Disk
    disk_file = ROOT_DIR / "storage" / "node1" / f"{blob_id}.blob"
    assert disk_file.exists(), f"Physical file {disk_file} does not exist on disk!"
    assert disk_file.stat().st_size == len(original_bytes)
    on_disk_bytes = disk_file.read_bytes()
    assert hashlib.sha256(on_disk_bytes).hexdigest() == expected_sha256
    print(f"     ✓ Physical file verified on disk: storage/node1/{blob_id}.blob ({disk_file.stat().st_size} bytes)")

    # 3. HEAD
    print(f"  2. HEAD /chunks/{blob_id}...")
    head_resp = httpx.head(f"{node1_url}/chunks/{blob_id}", timeout=3.0)
    assert head_resp.status_code == 200
    assert head_resp.headers["x-content-sha256"] == expected_sha256
    assert int(head_resp.headers["content-length"]) == len(original_bytes)
    print("     ✓ HEAD returned 200 with matching Content-Length and X-Content-SHA256 headers")

    # 4. GET
    print(f"  3. GET /chunks/{blob_id}...")
    get_resp = httpx.get(f"{node1_url}/chunks/{blob_id}", timeout=5.0)
    assert get_resp.status_code == 200
    downloaded_bytes = get_resp.content
    assert downloaded_bytes == original_bytes, "Downloaded bytes do not match original bytes!"
    downloaded_sha256 = hashlib.sha256(downloaded_bytes).hexdigest()
    assert downloaded_sha256 == expected_sha256
    assert get_resp.headers["x-content-sha256"] == expected_sha256
    print("     ✓ GET returned 200, downloaded bytes match exactly, SHA-256 matches")

    # 5. DELETE
    print(f"  4. DELETE /chunks/{blob_id}...")
    del_resp = httpx.delete(f"{node1_url}/chunks/{blob_id}", timeout=3.0)
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True
    assert not disk_file.exists(), "Physical file still exists after delete!"
    print("     ✓ DELETE returned 200, physical file confirmed removed from disk")

    # 6. Verify 404 after delete
    print(f"  5. Verify GET /chunks/{blob_id} returns 404 after deletion...")
    get_after = httpx.get(f"{node1_url}/chunks/{blob_id}", timeout=3.0)
    assert get_after.status_code == 404
    print("     ✓ GET returned 404 Not Found as expected")


def test_node3_failure_and_recovery():
    print("\n--- [Step 7] Node 3 Failure and Independent Recovery Test ---")
    sys.path.insert(0, str(ROOT_DIR))
    from scripts.cluster_nodes import kill_node, start_node, check_node_health

    # Stop ONLY Node 3
    print("  Stopping ONLY Node 3 (Port 5003)...")
    kill_node("node-3")
    time.sleep(1.0)

    # Verify Node 3 is unreachable
    is_up_3, _ = check_node_health(5003)
    assert not is_up_3, "Node 3 should be unreachable!"
    print("  ✓ Node 3 confirmed UNREACHABLE (Port 5003 down)")

    # Verify Nodes 1, 2, 4, 5, 6 remain reachable
    print("  Verifying remaining nodes (1, 2, 4, 5, 6) remain reachable...")
    for port in [5001, 5002, 5004, 5005, 5006]:
        is_up, _ = check_node_health(port)
        assert is_up, f"Node on port {port} should still be reachable!"
    print("  ✓ Nodes 1, 2, 4, 5, and 6 are healthy and serving requests independently!")

    # Restart Node 3
    print("  Restarting Node 3...")
    start_node("node-3")
    time.sleep(1.5)

    is_up_3_after, info = check_node_health(5003)
    assert is_up_3_after, "Node 3 should be back online!"
    assert info["status"] == "HEALTHY"
    print("  ✓ Node 3 restarted and verified HEALTHY on Port 5003!")


def test_node_isolation():
    print("\n--- [Step 8] Node Isolation Verification (Node 1 vs Node 4) ---")
    blob_id_n1 = "isolation-test-node1-only"
    blob_id_n4 = "isolation-test-node4-only"
    data1 = b"DATA_EXCLUSIVE_TO_NODE_1"
    data4 = b"DATA_EXCLUSIVE_TO_NODE_4"

    # PUT blob1 on Node 1 (port 5001)
    httpx.put(f"http://127.0.0.1:5001/chunks/{blob_id_n1}", content=data1)
    # PUT blob4 on Node 4 (port 5004)
    httpx.put(f"http://127.0.0.1:5004/chunks/{blob_id_n4}", content=data4)

    # Verify Node 1 has blob1, but does NOT have blob4
    assert httpx.get(f"http://127.0.0.1:5001/chunks/{blob_id_n1}").status_code == 200
    assert httpx.get(f"http://127.0.0.1:5001/chunks/{blob_id_n4}").status_code == 404

    # Verify Node 4 has blob4, but does NOT have blob1
    assert httpx.get(f"http://127.0.0.1:5004/chunks/{blob_id_n4}").status_code == 200
    assert httpx.get(f"http://127.0.0.1:5004/chunks/{blob_id_n1}").status_code == 404

    # Verify physical directories
    assert (ROOT_DIR / "storage" / "node1" / f"{blob_id_n1}.blob").exists()
    assert not (ROOT_DIR / "storage" / "node1" / f"{blob_id_n4}.blob").exists()
    assert (ROOT_DIR / "storage" / "node4" / f"{blob_id_n4}.blob").exists()
    assert not (ROOT_DIR / "storage" / "node4" / f"{blob_id_n1}.blob").exists()

    # Clean up
    httpx.delete(f"http://127.0.0.1:5001/chunks/{blob_id_n1}")
    httpx.delete(f"http://127.0.0.1:5004/chunks/{blob_id_n4}")
    print("  ✓ Full isolation verified: Node 1 and Node 4 hold disjoint data spaces without cross-contamination.")


def test_large_file_streaming():
    print("\n--- [Step 9] Large-File Streaming Handling (10 MB Chunk) ---")
    blob_id = "large-test-10mb"
    # Create 10 MB payload in 64KB patterns
    chunk_pattern = b"A" * 65536
    total_chunks = 160  # 160 * 64KB = 10,485,760 bytes = 10 MB
    expected_size = total_chunks * len(chunk_pattern)

    hasher = hashlib.sha256()
    for _ in range(total_chunks):
        hasher.update(chunk_pattern)
    expected_sha256 = hasher.hexdigest()

    # Generator for streaming PUT without buffering entire 10MB in one chunk
    def stream_generator():
        for _ in range(total_chunks):
            yield chunk_pattern

    print(f"  Streaming 10 MB payload ({expected_size} bytes) via PUT to Node 2 (Port 5002)...")
    start_put = time.time()
    with httpx.Client() as client:
        resp = client.put(
            f"http://127.0.0.1:5002/chunks/{blob_id}",
            content=stream_generator(),
            headers={"Content-Type": "application/octet-stream"},
            timeout=30.0,
        )
    put_duration = round(time.time() - start_put, 3)
    assert resp.status_code == 200, f"Large PUT failed: {resp.text}"
    put_json = resp.json()
    assert put_json["size"] == expected_size
    assert put_json["sha256"] == expected_sha256
    print(f"  ✓ Large PUT succeeded in {put_duration}s. Server reported size: {put_json['size']}, sha256: {put_json['sha256'][:16]}...")

    # Streaming GET
    print("  Streaming 10 MB payload back via GET from Node 2...")
    start_get = time.time()
    get_hasher = hashlib.sha256()
    downloaded_size = 0
    with httpx.Client() as client:
        with client.stream("GET", f"http://127.0.0.1:5002/chunks/{blob_id}", timeout=30.0) as stream_resp:
            assert stream_resp.status_code == 200
            for chunk in stream_resp.iter_bytes(chunk_size=65536):
                get_hasher.update(chunk)
                downloaded_size += len(chunk)
    get_duration = round(time.time() - start_get, 3)

    assert downloaded_size == expected_size
    assert get_hasher.hexdigest() == expected_sha256
    print(f"  ✓ Large GET stream verified in {get_duration}s. Exact bytes: {downloaded_size}, SHA-256 matched 100%!")

    # Clean up
    httpx.delete(f"http://127.0.0.1:5002/chunks/{blob_id}")


def test_path_traversal_security():
    print("\n--- [Step 10] Security / Path-Traversal Rejection Verification ---")
    import socket

    # 1. URL-encoded traversal attempts through HTTP client
    encoded_payloads = [
        "..%2fescape.txt",
        "..%2f..%2fetc%2fpasswd",
        "%2e%2e%2fwindows%2fwin.ini",
        "..%5cwindows%5csystem32",
        "subdir%2f..%2f..%2fsecret",
    ]

    for payload in encoded_payloads:
        # PUT attempt
        put_url = f"http://127.0.0.1:5001/chunks/{payload}"
        r_put = httpx.put(put_url, content=b"MALICIOUS_DATA", timeout=3.0)
        assert r_put.status_code == 400, f"Expected 400 for unsafe path '{payload}', got {r_put.status_code}"
        assert "Path traversal rejected" in r_put.json().get("detail", "")
        print(f"  ✓ Rejected unsafe PUT '{payload}' with HTTP 400: {r_put.json()['detail']}")

        # GET attempt
        get_url = f"http://127.0.0.1:5001/chunks/{payload}"
        r_get = httpx.get(get_url, timeout=3.0)
        assert r_get.status_code == 400, f"Expected 400 for unsafe GET '{payload}', got {r_get.status_code}"
        print(f"  ✓ Rejected unsafe GET '{payload}' with HTTP 400: {r_get.json()['detail']}")

    # 2. Raw HTTP socket request with unencoded ../
    s = socket.socket()
    s.connect(("127.0.0.1", 5001))
    raw_req = b"PUT /chunks/../escape.txt HTTP/1.1\r\nHost: 127.0.0.1:5001\r\nContent-Length: 9\r\n\r\nMALICIOUS"
    s.sendall(raw_req)
    raw_resp = s.recv(1024).decode()
    s.close()
    assert "400 Bad Request" in raw_resp
    print("  ✓ Raw socket 'PUT /chunks/../escape.txt' strictly rejected with HTTP 400 Bad Request")

    print("  ✓ All path traversal vectors successfully blocked. Nodes strictly confine writes/reads to their root storage directory.")


if __name__ == "__main__":
    print("=" * 65)
    print("       NEXVAULT DATA PLANE DEEP VERIFICATION SUITE")
    print("=" * 65)
    verify_all_nodes_healthy()
    test_node1_end_to_end()
    test_node3_failure_and_recovery()
    test_node_isolation()
    test_large_file_streaming()
    test_path_traversal_security()
    print("\n" + "=" * 65)
    print("  ALL DATA PLANE REQUIREMENTS VERIFIED & ASSERTED SUCCESSFULLY!")
    print("=" * 65)
