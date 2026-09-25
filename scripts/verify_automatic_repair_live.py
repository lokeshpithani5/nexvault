import io
import json
import httpx
import uuid
import sys
import os
import time

sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings

BASE_URL = "http://127.0.0.1:8000"


def print_step(title):
    print(f"\n{'='*20} {title} {'='*20}")


def main():
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as client:
        # Step 0: Authenticate
        login_res = client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.INITIAL_ADMIN_EMAIL,
                "password": settings.INITIAL_ADMIN_PASSWORD,
            },
        )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Admin authenticated.")

        # 1. Upload a fresh RF3 object
        print_step("Step 1 & 2: Upload Fresh RF3 Object and Record Metadata")
        bucket_name = f"live-auto-repair-{uuid.uuid4().hex[:6]}"
        client.post("/api/v1/buckets", json={"name": bucket_name}, headers=headers)

        payload = b"NEXVAULT Live Automatic Self-Healing Demonstration Payload 2026"
        file_tuple = ("live_durability_demo.txt", io.BytesIO(payload), "text/plain")
        up_res = client.post(
            f"/api/v1/buckets/{bucket_name}/objects/upload",
            files={"file": file_tuple},
            headers=headers,
        )
        assert up_res.status_code == 201
        obj_info = up_res.json()
        version_id = obj_info["current_version"]["id"]
        sha256 = obj_info["current_version"]["sha256_checksum"]
        initial_replicas = obj_info["current_version"]["replicas"]
        initial_node_ids = [r["node_id"] for r in initial_replicas]

        print(f"Bucket: {bucket_name}")
        print(f"Object Key: live_durability_demo.txt, Version: {version_id}")
        print(f"SHA-256: {sha256}")
        print(f"Initial 3 Replica Nodes: {initial_node_ids}")
        assert len(initial_node_ids) == 3

        # 3. Physically fail one replica node through Chaos Lab
        print_step("Step 3: Physically Fail One Replica Node Through Chaos Lab")
        target_node_to_fail = initial_node_ids[0]
        nodes_map = {n["id"]: n["name"] for n in client.get("/api/v1/nodes", headers=headers).json()}
        failed_node_name = nodes_map.get(target_node_to_fail, target_node_to_fail)

        fail_res = client.post(
            "/api/v1/admin/chaos/node-fail",
            json={"node_id": target_node_to_fail, "action": "FAIL"},
            headers=headers,
        )
        assert fail_res.status_code == 200
        print(f"Successfully failed node: {failed_node_name} ({target_node_to_fail})")

        # 4. Verify object becomes DEGRADED
        print_step("Step 4: Verify Object State becomes DEGRADED")
        m_degraded = client.get("/api/v1/admin/metrics", headers=headers).json()
        print(f"Failed Nodes: {m_degraded['failed_nodes']}")
        print(f"Degraded Objects: {m_degraded['degraded_objects']}")
        assert m_degraded["failed_nodes"] >= 1
        assert m_degraded["degraded_objects"] >= 1

        # 5 & 6. Wait for the background repair worker and verify automatic repair job
        print_step("Step 5 & 6: Wait for Background Repair Worker (NO MANUAL EXECUTION)")
        print("Waiting for periodic RepairWorker cycle to discover and repair degraded object...")
        repaired = False
        target_replica = None
        new_node_id = None

        for attempt in range(12):
            time.sleep(1.0)
            # Check repair jobs for this version
            repairs = client.get("/api/v1/admin/repairs", headers=headers).json()
            matching_jobs = [r for r in repairs if r["version_id"] == version_id]
            if matching_jobs and matching_jobs[0]["status"] == "COMPLETED":
                print(f"  [+] Discovered automatic repair job {matching_jobs[0]['id']} with status {matching_jobs[0]['status']}!")
                repaired = True
                break
            else:
                print(f"  ... checking worker tick (attempt {attempt + 1}/12) ...")

        assert repaired, "Background worker did not automatically complete repair job within timeout!"

        # 7 & 8. Verify a healthy target node receives the replica and SHA-256 matches
        print_step("Step 7 & 8: Verify Healthy Target Node Received Rebuilt Replica and SHA-256 Matches")
        detail_res = client.get(
            f"/api/v1/buckets/{bucket_name}/objects/live_durability_demo.txt/metadata",
            headers=headers,
        )
        assert detail_res.status_code == 200
        detail = detail_res.json()
        curr_reps = detail["current_version"]["replicas"]
        healthy_reps = [r for r in curr_reps if r["status"] == "HEALTHY" and r["node_id"] != target_node_to_fail]
        print(f"Replicas on object now: {len(curr_reps)}")
        print(f"Healthy active replicas (excluding failed node): {len(healthy_reps)}")
        for r in healthy_reps:
            print(f"  - Replica {r['id']} on node {nodes_map.get(r['node_id'], r['node_id'])}: status={r['status']}, sha={r['stored_checksum'][:12]}...")
            assert r["stored_checksum"] == sha256
        assert len(healthy_reps) >= 3

        # 9. Verify object returns to HEALTHY
        print_step("Step 9: Verify Object Returns to HEALTHY")
        m_restored = client.get("/api/v1/admin/metrics", headers=headers).json()
        print(f"Total Objects: {m_restored['total_objects']}")
        print(f"Healthy Objects: {m_restored['healthy_objects']}")
        assert m_restored["healthy_objects"] >= 1

        # 10. Check events
        print_step("Step 10: Check Emitted Repair Events")
        for ev_type in ["REPAIR_CREATED", "REPAIR_STARTED", "CHECKSUM_VERIFIED", "REPLICA_REBUILT", "OBJECT_HEALTHY"]:
            ev_list = client.get(f"/api/v1/admin/events?event_type={ev_type}&limit=1", headers=headers).json()
            assert len(ev_list) >= 1
            print(f"  [OK] Event {ev_type}: {ev_list[0]['message']}")

        # 11. Check recovery metrics
        print_step("Step 11: Check Recovery Metrics")
        rec_m = m_restored["recovery_metrics"]
        print(json.dumps(rec_m, indent=2))
        assert rec_m["successful_repairs"] >= 1
        assert rec_m["average_recovery_time_seconds"] is not None

        # 12. Corrupt another physical replica
        print_step("Step 12: Corrupt Another Physical Replica")
        corr_target_rep = healthy_reps[0]["id"]
        corr_res = client.post(
            "/api/v1/admin/chaos/corrupt-replica",
            json={"replica_id": corr_target_rep},
            headers=headers,
        )
        assert corr_res.status_code == 200
        print(f"Corrupted replica: {corr_target_rep}")

        # 13 & 14. Run integrity scan & verify automatic repair occurs
        print_step("Step 13 & 14: Run Integrity Scan and Verify Automatic Repair Occurs")
        scan_res = client.post("/api/v1/admin/chaos/scan-integrity", headers=headers)
        assert scan_res.status_code == 200
        scan_data = scan_res.json()
        print(json.dumps(scan_data, indent=2))
        assert scan_data["affected_entities"]["corrupted"] >= 1
        assert scan_data["affected_entities"]["repaired"] >= 1

        # 15. Restore the failed node
        print_step("Step 15 & 16: Restore Failed Node and Verify Reconciliation")
        restore_res = client.post(
            "/api/v1/admin/chaos/node-restore",
            json={"node_id": target_node_to_fail},
            headers=headers,
        )
        assert restore_res.status_code == 200
        rest_data = restore_res.json()
        print(f"Restored node: {failed_node_name}")
        print(json.dumps(rest_data, indent=2))

        # Check final metrics
        final_summary = client.get("/api/v1/admin/metrics/cluster", headers=headers).json()
        print("\nFinal Cluster Health Summary:")
        print(json.dumps(final_summary, indent=2))
        assert final_summary["node_counts"]["healthy"] == 6
        assert final_summary["node_counts"]["failed"] == 0

        print("\n" + "=" * 60)
        print("ALL 16 LIVE VERIFICATION STEPS COMPLETED SUCCESSFULLY!")
        print("AUTOMATIC REPAIR CONFIRMED WITHOUT MANUAL REPAIR ENDPOINT INVOCATION!")
        print("=" * 60)


if __name__ == "__main__":
    main()
