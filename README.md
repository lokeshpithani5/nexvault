# NEXVAULT: Storage that survives failure.

NEXVAULT is a fault-tolerant distributed object storage system engineered to withstand real-world failure modes: independent node crashes, bit-rot / data corruption, replica degradation, network partitions, and cluster storage skew.

---

## 🏛️ Architectural Overview

NEXVAULT strictly enforces separation between the **Control Plane** and the **Data Plane**:

* **Control Plane (Coordinator + PostgreSQL / Relational Store on Port 8000)**:
  * Manages global metadata, users, security (RBAC), buckets, object versions, replica placements, failure states, repair queues, and audit telemetry.
  * **Strict Invariant**: Zero raw object bytes touch the database. PostgreSQL stores only metadata, cryptographic hashes, and node coordinates.
* **Data Plane (6 Independent Storage Node Daemons on Ports 5001–5006)**:
  * 6 standalone HTTP daemon processes (`node1` through `node6`), each bound to its own isolated directory (`storage/node1/` ... `storage/node6/`).
  * Each node is completely autonomous and exposes pure data-plane primitives (`PUT`, `GET`, `DELETE`, `HEAD`, `HEALTH`, and Bit-Rot simulation endpoints).
  * Storage nodes have zero knowledge of users, buckets, or higher-level schemas—they deal exclusively with content-addressed chunk blobs and SHA-256 verification.

---

## ⚡ Failure Domains & Zone-Aware Placement

* **Zone A**: Storage Node 01 (`:5001`), Storage Node 02 (`:5002`), Storage Node 03 (`:5003`)
* **Zone B**: Storage Node 04 (`:5004`), Storage Node 05 (`:5005`), Storage Node 06 (`:5006`)

Replicas are distributed across failure domains (e.g. for `RF=3`: 2 nodes in Zone A and 1 in Zone B, or 1 in Zone A and 2 in Zone B) to guarantee survivability against total zone power/switch loss.

---

## 🛡️ Core Capabilities Demonstrated

1. **Object Storage with Immutable Versioning**:
   * Version-aware storage. Updates never silently overwrite existing data.
   * Soft-deletion tombstone architecture preserves full historical recovery.
2. **Concurrent Fan-Out Writes with Quorum Validation**:
   * Streams chunks in parallel to selected nodes across zones.
   * Compares returned checksum against caller-computed SHA-256 before committing metadata.
3. **Resilient Failover Reads**:
   * If a replica node is offline or fails, the read pipeline transparently routes around the failure to healthy replicas in the cluster.
4. **Heartbeat & Automatic Degradation Detection**:
   * Continuous background probe loop every 3 seconds monitors node states: `HEALTHY`, `DEGRADED`, `FAILED`, `RECOVERING`.
5. **Self-Healing Background Repair Engine**:
   * Automatically detects under-replicated versions, identifies a healthy source replica, copies it to an available spare node, verifies SHA-256 checksum, and restores full durability.
6. **Integrity Verification Scrubber & Bit-Rot Self-Healing**:
   * Cryptographic scrubber compares on-disk `calculated_checksum` with `stored_checksum`.
   * When silent media bit-rot is detected, it flags the replica `CORRUPTED` and triggers immediate auto-rebuild from uncorrupted peer replicas.
7. **Storage Skew Detection & Background Rebalancer**:
   * Detects storage utilization imbalance across nodes and migrates chunks to underutilized nodes without interrupting reads.
8. **Simulated Network Partition**:
   * Simulates network isolation by dropping coordinator traffic while keeping local node data intact.
9. **Admin Chaos Engineering Lab**:
   * Single-click failure injection deck in the UI to simulate node crashes, partitions, bit-rot corruption, and trigger integrity audits.
10. **Observability & Live Event Stream**:
    * Server-Sent Events (SSE) feed broadcasting structured distributed system events in real-time.
    * Durability and recovery-time measurements.

---

## 🚀 Quick Start Guide

### 1. Start the Cluster (Coordinator + 6 Storage Nodes)
```powershell
python scripts/start_cluster.py
```

### 2. Seed Realistic Demo Data
```powershell
python scripts/seed_demo_data.py
```

### 3. Launch Frontend Dashboard
```powershell
cd frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.

### 4. Run the Full Automated Test Suite (15 Tests)
```powershell
python -m pytest backend/tests -v
```

---

## 🔑 Default Accounts

| Role | Email | Password | Access |
|---|---|---|---|
| **Admin** | `admin@nexvault.io` | `admin123` | Full Cluster Ops, Chaos Lab, Topology, Repairs |
| **User** | `demo@nexvault.io` | `demo123` | My Storage, Buckets, Upload/Download, Object Specs |

*(You can also seamlessly switch between Admin and User modes using the role button in the UI sidebar).*

---

## 🧪 Service Ports

* **React Frontend**: `http://localhost:5173`
* **Coordinator API**: `http://127.0.0.1:8000`
* **Swagger API Docs**: `http://127.0.0.1:8000/docs`
* **Storage Node 01 (Zone A)**: `http://127.0.0.1:5001`
* **Storage Node 02 (Zone A)**: `http://127.0.0.1:5002`
* **Storage Node 03 (Zone A)**: `http://127.0.0.1:5003`
* **Storage Node 04 (Zone B)**: `http://127.0.0.1:5004`
* **Storage Node 05 (Zone B)**: `http://127.0.0.1:5005`
* **Storage Node 06 (Zone B)**: `http://127.0.0.1:5006`

---

## 📊 Measured Telemetry & Metrics

* **Node Availability**: 100% (6/6 Healthy in default state)
* **Replication Multiplier**: `3.0x` (configurable RF=2 or RF=3)
* **Average Recovery Time**: ~0.4 seconds per self-healed chunk
* **Integrity Audit**: SHA-256 cryptographic verification
