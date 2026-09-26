# NEXVAULT — Hackathon Demo Runbook

**Tagline**: Storage that survives failure.  
**Branch**: `lokesh/storage`  
**Current Test Status**: 31/31 passing tests.

---

## 1. Quick URLs

| Service | Local URL | Description |
| :--- | :--- | :--- |
| **React Dashboard** | [http://localhost:5173](http://localhost:5173) | Primary Operator & Chaos Engineering UI |
| **Control Plane Coordinator** | [http://127.0.0.1:8000](http://127.0.0.1:8000) | FastAPI Orchestrator & Metadata Engine |
| **Swagger / OpenAPI Docs** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive REST API Contract Explorer |
| **Storage Nodes (Zone A)** | Ports `5001`, `5002`, `5003` | Independent node daemons in Zone A |
| **Storage Nodes (Zone B)** | Ports `5004`, `5005`, `5006` | Independent node daemons in Zone B |

---

## 2. Demo Credentials

| Role | Email | Password | Privileges |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@nexvault.io` | `admin123` | Full Cluster Access, Chaos Lab, Node Faults, Reset |
| **User** | `demo@nexvault.io` | `demo123` | Bucket Explorer, Upload, Download, Telemetry |

---

## 3. How to Start NEXVAULT

### One-Command Unified Launcher (PowerShell)
```powershell
.\scripts\start_nexvault.ps1
```

### Manual Individual Commands
If starting services in separate terminal windows:
```bash
# Terminal 1 — Start 6 Storage Nodes & Backend Coordinator
python scripts/start_cluster.py

# Terminal 2 — Start React Frontend
cd frontend
npm run dev
```

---

## 4. Preflight & Demo Verification

Always run this before beginning a live demo to judges:
```bash
python scripts/demo_preflight.py
```
- Checks Coordinator HTTP availability on port 8000.
- Pings health of all 6 independent storage nodes (ports 5001–5006).
- Validates database connectivity and admin authentication.
- Verifies 0 failed nodes and 0 unresolved degraded objects.
- Exits code `0` on success.

---

## 5. Failure & Self-Healing Demo (Step-by-Step Script)

Follow these steps to demonstrate NEXVAULT's fault tolerance to judges:

1. **Upload an Object with RF=3**:
   - In the React UI, navigate to **Bucket Explorer** $\rightarrow$ `production-data`.
   - Upload any file (e.g. `audit_report.pdf` or an image).
   - Click the object $\rightarrow$ open **Object Specifications Modal**.
   - Show judges the 3 physical replica locations placed across **Zone A** and **Zone B** with exact SHA-256 hashes.

2. **Trigger a Physical Node Crash**:
   - Navigate to the **Chaos Lab** panel.
   - Under **Targeted Node Fault**, select one of the nodes holding a replica (e.g. `node-1` on port 5001).
   - Click **Crash / Revive**.
   - Observe in the top navigation bar: Cluster health updates to **DEGRADED**, and `node-1` shows red in the **Node Matrix**.

3. **Read Through Node Failure (Zero-Downtime Failover)**:
   - Go back to **Bucket Explorer** and click **Download** on the object.
   - The file downloads instantly and without error because the coordinator transparently fails over to surviving replicas.

4. **Observe Automated Background Repair**:
   - Open the **Repair Monitor** tab.
   - Observe the new **Automated Replica Repair Job** transition: `QUEUED` $\rightarrow$ `RUNNING` $\rightarrow$ `COMPLETED`.
   - Show the real recorded recovery metrics: `duration_ms` (~50ms) and `bytes_recovered`.
   - The object now has 3 healthy replicas restored using an available spare node.

5. **Silent Bit-Rot Injection & Integrity Healing**:
   - In the Object Modal, click **Corrupt Replica Chunk** on any replica.
   - Notice the status updates to `CORRUPTED`.
   - Download the file again: The coordinator detects the SHA-256 mismatch on the fly, serves good data from another replica, and heals the corrupted chunk.

---

## 6. Demo Reset & Emergency Recovery

### Quick In-App Reset
- Click **Reset Cluster to Healthy** in the Chaos Lab or call `api.resetDemoCluster()`.

### CLI Cluster Reset
If the demo gets into a chaotic state or a node process crashed unexpectedly:
```bash
python scripts/demo_reset.py
```
This command safely:
1. Restores and restarts any dead storage node processes.
2. Clears all simulated network partitions.
3. Clears transient replica error flags and prunes excess replicas.
4. Sweeps cryptographic SHA-256 integrity verification across the cluster.
5. Returns NEXVAULT to 100% operational health without deleting user data.
