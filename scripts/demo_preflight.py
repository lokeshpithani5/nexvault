"""
NEXVAULT Demo Preflight Verification Script
Checks the operational readiness of the full distributed storage cluster before demos.
Exits 0 on SUCCESS, 1 on FAILURE.
"""

import sys
import httpx

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BACKEND_URL = "http://127.0.0.1:8000"
STORAGE_NODES = [
    ("node-1", 5001, "ZONE_A"),
    ("node-2", 5002, "ZONE_A"),
    ("node-3", 5003, "ZONE_A"),
    ("node-4", 5004, "ZONE_B"),
    ("node-5", 5005, "ZONE_B"),
    ("node-6", 5006, "ZONE_B"),
]


def run_preflight():
    print("=" * 65)
    print("             NEXVAULT DEMO PREFLIGHT CHECK")
    print("             Storage that survives failure.")
    print("=" * 65)

    all_passed = True

    # 1. Backend reachable
    print("\n[1/5] Checking Coordinator Service (Port 8000)...")
    try:
        r = httpx.get(f"{BACKEND_URL}/", timeout=3.0)
        if r.status_code == 200 and r.json().get("product") == "NEXVAULT":
            print(f"  [PASS] Coordinator reachable on {BACKEND_URL} ({r.json().get('version')})")
        else:
            print(f"  [FAIL] Unexpected response from {BACKEND_URL}: {r.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Coordinator unreachable on {BACKEND_URL}: {e}")
        all_passed = False

    # 2. Check all 6 storage nodes
    print("\n[2/5] Checking All 6 Autonomous Storage Nodes (Ports 5001-5006)...")
    nodes_healthy = 0
    for node_id, port, zone in STORAGE_NODES:
        url = f"http://127.0.0.1:{port}/health"
        try:
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status")
                chunks = data.get("chunk_count", 0)
                used_kb = round(data.get("used_bytes", 0) / 1024, 1)
                print(f"  [PASS] {node_id} (Port {port}, {zone}): Status={status}, Chunks={chunks}, Stored={used_kb} KB")
                nodes_healthy += 1
            else:
                print(f"  [FAIL] {node_id} on port {port} returned status {r.status_code}")
                all_passed = False
        except Exception as e:
            print(f"  [FAIL] {node_id} on port {port} is OFFLINE: {e}")
            all_passed = False

    # 3. Authentication & Database connectivity
    print("\n[3/5] Testing API Authentication & Database Connectivity...")
    token = None
    try:
        r = httpx.post(
            f"{BACKEND_URL}/api/v1/auth/login",
            json={"email": "admin@nexvault.io", "password": "admin123"},
            timeout=3.0,
        )
        if r.status_code == 200:
            token = r.json().get("access_token")
            user = r.json().get("user", {})
            print(f"  [PASS] Successfully authenticated admin: {user.get('email')} (Role: {user.get('role')})")
        else:
            print(f"  [FAIL] Admin login failed: {r.status_code} {r.text}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Login request failed: {e}")
        all_passed = False

    # 4. Cluster overview & node count
    print("\n[4/5] Checking Cluster Topology & Health Telemetry...")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/cluster/overview", headers=headers, timeout=3.0)
        if r.status_code == 200:
            ov = r.json()
            nodes_info = ov.get("nodes", {})
            total_n = nodes_info.get("total", 0)
            healthy_n = nodes_info.get("healthy", 0)
            failed_n = nodes_info.get("failed", 0)
            degraded_n = nodes_info.get("degraded", 0)

            print(f"  [INFO] Cluster State: {ov.get('status')} (Health Score: {ov.get('health_score_pct')}%)")
            print(f"  [INFO] Node Status: {healthy_n}/{total_n} Healthy, {failed_n} Failed, {degraded_n} Degraded")

            if total_n == 6 and failed_n == 0:
                print("  [PASS] Expected 6 nodes registered with 0 failed nodes.")
            else:
                print(f"  [FAIL] Node topology abnormal: {failed_n} failed nodes present.")
                all_passed = False
        else:
            print(f"  [FAIL] Cluster overview returned status {r.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Failed to retrieve cluster overview: {e}")
        all_passed = False

    # 5. Degraded objects check
    print("\n[5/5] Checking Object Durability & Degraded Object Count...")
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/cluster/metrics", headers=headers, timeout=3.0)
        if r.status_code == 200:
            met = r.json()
            degraded_objs = met.get("degraded_object_count", 0)
            completed_repairs = met.get("repair_jobs_completed", 0)
            overhead = met.get("replication_overhead", 0.0)

            print(f"  [INFO] Completed Repairs: {completed_repairs}")
            print(f"  [INFO] Measured Storage Overhead: {overhead}x")
            print(f"  [INFO] Degraded Objects: {degraded_objs}")

            if degraded_objs == 0:
                print("  [PASS] All objects have full RF durability (0 degraded objects).")
            else:
                print(f"  [WARN] {degraded_objs} degraded object(s) detected. Self-healing loop will restore.")
        else:
            print(f"  [FAIL] Metrics endpoint returned status {r.status_code}")
            all_passed = False
    except Exception as e:
        print(f"  [FAIL] Metrics request failed: {e}")
        all_passed = False

    print("\n" + "=" * 65)
    if all_passed:
        print(" [SUCCESS] ALL PREFLIGHT CHECKS PASSED — NEXVAULT IS READY TO DEMO!")
        print("=" * 65)
        sys.exit(0)
    else:
        print(" [FAILURE] PREFLIGHT CHECKS FAILED! Run 'python scripts/demo_reset.py'")
        print("=" * 65)
        sys.exit(1)


if __name__ == "__main__":
    run_preflight()
