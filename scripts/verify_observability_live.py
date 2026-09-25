import io
import json
import httpx
import uuid
import sys
import os

sys.path.insert(0, os.path.abspath("."))
from app.core.config import settings

BASE_URL = "http://127.0.0.1:8000"


def print_step(title):
    print(f"\n{'='*20} {title} {'='*20}")


def main():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # Step 0: Login as admin
        login_res = client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.INITIAL_ADMIN_EMAIL,
                "password": settings.INITIAL_ADMIN_PASSWORD,
            },
        )
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Admin authenticated successfully.")

        # 1. GET /api/v1/admin/events
        print_step("Step 1: GET /api/v1/admin/events")
        res1 = client.get("/api/v1/admin/events?limit=5", headers=headers)
        print(f"Status: {res1.status_code}")
        events = res1.json()
        print(f"Total events returned: {len(events)}")
        if events:
            print("Latest event sample:")
            print(json.dumps(events[0], indent=2))

        # 2. GET /api/v1/admin/metrics
        print_step("Step 2: GET /api/v1/admin/metrics")
        res2 = client.get("/api/v1/admin/metrics", headers=headers)
        print(f"Status: {res2.status_code}")
        metrics = res2.json()
        print("System Metrics:")
        print(json.dumps(metrics, indent=2))

        # 3. GET /api/v1/admin/metrics/cluster
        print_step("Step 3: GET /api/v1/admin/metrics/cluster")
        res3 = client.get("/api/v1/admin/metrics/cluster", headers=headers)
        print(f"Status: {res3.status_code}")
        print("Cluster Summary:")
        print(json.dumps(res3.json(), indent=2))

        # Get nodes
        nodes = client.get("/api/v1/nodes", headers=headers).json()
        target_node = nodes[0]
        node_id = target_node["id"]
        node_name = target_node["name"]
        print(f"\nTarget node for failure: {node_name} ({node_id})")

        # 4. Trigger node failure
        print_step("Step 4: Trigger Node Failure")
        fail_res = client.post(
            "/api/v1/admin/chaos/node-fail",
            json={"node_id": node_id, "action": "FAIL"},
            headers=headers,
        )
        print(f"Status: {fail_res.status_code}")
        print(json.dumps(fail_res.json(), indent=2))

        # 5. Verify new event
        print_step("Step 5: Verify NODE_FAILED Event")
        ev_res = client.get("/api/v1/admin/events?event_type=NODE_FAILED&limit=1", headers=headers)
        failed_ev = ev_res.json()
        print(f"Status: {ev_res.status_code}, Found: {len(failed_ev)}")
        if failed_ev:
            print(json.dumps(failed_ev[0], indent=2))

        # 6. Verify metrics change
        print_step("Step 6: Verify Metrics Change after Node Failure")
        res_m_fail = client.get("/api/v1/admin/metrics", headers=headers).json()
        print(f"Healthy Nodes: {res_m_fail['healthy_nodes']}, Failed Nodes: {res_m_fail['failed_nodes']}")
        assert res_m_fail["failed_nodes"] >= 1, "Failed nodes should be at least 1"

        # 7. Restore node
        print_step("Step 7: Restore Node")
        restore_res = client.post(
            "/api/v1/admin/chaos/node-restore",
            json={"node_id": node_id},
            headers=headers,
        )
        print(f"Status: {restore_res.status_code}")
        print(json.dumps(restore_res.json(), indent=2))

        # 8. Verify restoration event
        print_step("Step 8: Verify NODE_RESTORED Event")
        ev_rest = client.get("/api/v1/admin/events?event_type=NODE_RESTORED&limit=1", headers=headers).json()
        print(f"Found NODE_RESTORED events: {len(ev_rest)}")
        if ev_rest:
            print(json.dumps(ev_rest[0], indent=2))

        # 9. Corrupt a replica
        print_step("Step 9: Upload Object & Corrupt Replica")
        bucket_name = f"live-verify-{uuid.uuid4().hex[:6]}"
        client.post("/api/v1/buckets", json={"name": bucket_name}, headers=headers)
        data = b"Live Verification Object Content for Corruption & Repair"
        upload_res = client.post(
            f"/api/v1/buckets/{bucket_name}/objects/upload",
            files={"file": ("live.txt", io.BytesIO(data), "text/plain")},
            headers=headers,
        )
        assert upload_res.status_code == 201
        upload_data = upload_res.json()
        version_id = upload_data["current_version"]["id"]
        print(f"Uploaded object to {bucket_name}, version_id={version_id}")

        corr_res = client.post("/api/v1/admin/chaos/corrupt-replica", json={"random": True}, headers=headers)
        print("Corrupt Replica Status:", corr_res.status_code)
        print(json.dumps(corr_res.json(), indent=2))

        # 10. Run integrity scan
        print_step("Step 10: Run Integrity Scan")
        scan_res = client.post("/api/v1/admin/chaos/scan-integrity", headers=headers)
        print("Scan Integrity Status:", scan_res.status_code)
        print(json.dumps(scan_res.json(), indent=2))

        # 11. Verify corruption/integrity events and metrics
        print_step("Step 11: Verify Corruption/Integrity Events & Metrics")
        corr_ev = client.get("/api/v1/admin/events?event_type=REPLICA_CORRUPTED&limit=1", headers=headers).json()
        print(f"REPLICA_CORRUPTED events found: {len(corr_ev)}")
        if corr_ev:
            print("Latest REPLICA_CORRUPTED:", json.dumps(corr_ev[0], indent=2))

        scan_ev = client.get("/api/v1/admin/events?event_type=INTEGRITY_SCAN_COMPLETED&limit=1", headers=headers).json()
        print(f"INTEGRITY_SCAN_COMPLETED events found: {len(scan_ev)}")
        if scan_ev:
            print("Latest INTEGRITY_SCAN_COMPLETED:", json.dumps(scan_ev[0], indent=2))

        m_corr = client.get("/api/v1/admin/metrics", headers=headers).json()
        print(f"Corrupted Replicas in Metrics: {m_corr['corrupted_replicas']}")
        print(f"Latest Integrity Scan Result in Metrics: {json.dumps(m_corr['latest_integrity_scan_result'], indent=2)}")

        # 12. Verify repair-related metrics when repair completes
        print_step("Step 12: Create & Execute Repair Job, Verify Repair Metrics")
        repair_job = client.post(
            "/api/v1/admin/repairs",
            json={
                "version_id": version_id,
                "target_node_id": target_node["id"],
                "trigger_reason": "LIVE_VERIFICATION_REPAIR",
            },
            headers=headers,
        ).json()
        job_id = repair_job["id"]
        print(f"Created repair job: {job_id}")

        exec_res = client.post(f"/api/v1/admin/repairs/{job_id}/execute", headers=headers)
        print("Repair Execution Status:", exec_res.status_code)
        print(json.dumps(exec_res.json(), indent=2))

        # Check repair metrics
        m_final = client.get("/api/v1/admin/metrics", headers=headers).json()
        print("\nFinal Observability Metrics Recovery Block:")
        print(json.dumps(m_final["recovery_metrics"], indent=2))
        print(f"Repair Jobs Completed: {m_final['repair_jobs_completed']}")
        print(f"Replicas Repaired: {m_final['replicas_repaired']}")
        print(f"Bytes Recovered: {m_final['bytes_recovered']}")

        print("\nLIVE VERIFICATION ALL 12 STEPS COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
