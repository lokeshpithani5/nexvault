# NEXVAULT — Frontend Development Fallbacks & Adapter Audit

This document catalogizes **every single mock/fallback data structure** currently in the frontend. It explains the exact conditions under which fallbacks are invoked, how they are isolated, and the production behavior expected when connected to the live FastAPI Control Plane.

---

## Isolation Mechanism

All fallbacks are isolated strictly inside the `src/services/` layer:
1. Every service function attempts the **real HTTP endpoint first** via `api.js`.
2. Fallback logic is **ONLY triggered if**:
   - `err.isNetworkError === true` (the browser cannot connect to `http://localhost:8000`), **AND**
   - `api.isDevFallbackEnabled() === true`.
3. If the backend is running and returns an HTTP error code (`401`, `403`, `404`, `409`, `422`, `500`, `503`), the fallback is **BYPASSED** and the real error is passed directly to the UI.
4. **How to disable all development fallbacks immediately:**
   - In browser console: `localStorage.setItem('nexvault_dev_fallback_mode', 'false')`
   - Or set in `.env`: `VITE_ENABLE_DEV_FALLBACK=false`

---

## 1. Storage Service Fallbacks (`src/services/storageService.js`)

### Fallback 1: `storageService.listBuckets`
- **File:** `src/services/storageService.js`
- **Function:** `listBuckets()`
- **Mock Response:** `devStore.getBuckets()` (`INITIAL_BUCKETS`: 4 buckets: `production-backups`, `telemetry-logs`, `ai-models`, `corporate-docs`).
- **Real Endpoint Required:** `GET /buckets`
- **Expected Production Behavior:** Query PostgreSQL `buckets` table joined with computed chunk replica bytes. Returns real provisioned buckets for the authenticated user.

---

### Fallback 2: `storageService.createBucket`
- **File:** `src/services/storageService.js`
- **Function:** `createBucket(name, policy)`
- **Mock Response:** `devStore.addBucket(name, policy)` with client-generated UUID and localStorage persistence.
- **Real Endpoint Required:** `POST /buckets`
- **Expected Production Behavior:** Insert into PostgreSQL `buckets` table with owner ID and policy enum (`REPLICATION_3`, `REPLICATION_2`, `ERASURE_CODING_4_2`). Rejects duplicate names with `409 Conflict`.

---

### Fallback 3: `storageService.getBucket`
- **File:** `src/services/storageService.js`
- **Function:** `getBucket(bucketId)`
- **Mock Response:** Lookup from `devStore.getBuckets()`.
- **Real Endpoint Required:** `GET /buckets/{bucketId}`
- **Expected Production Behavior:** Return metadata, policy, object count, and total logical bytes for bucket. Returns `404 Not Found` if missing.

---

### Fallback 4: `storageService.deleteBucket`
- **File:** `src/services/storageService.js`
- **Function:** `deleteBucket(bucketId)`
- **Mock Response:** `devStore.deleteBucket(bucketId)` (removes from memory/localStorage).
- **Real Endpoint Required:** `DELETE /buckets/{bucketId}`
- **Expected Production Behavior:** Validates that bucket contains no active objects. Deletes record from PostgreSQL or throws `409 Conflict` if non-empty.

---

### Fallback 5: `storageService.listObjects`
- **File:** `src/services/storageService.js`
- **Function:** `listObjects(bucketName, prefix)`
- **Mock Response:** `devStore.getObjects(bucketName)` (`INITIAL_OBJECTS` array with 6 sample objects).
- **Real Endpoint Required:** `GET /buckets/{bucketName}/objects?prefix={prefix}`
- **Expected Production Behavior:** Queries PostgreSQL `objects` joined with `object_versions` where `is_latest = TRUE` and `is_tombstone = FALSE`.

---

### Fallback 6: `storageService.getObjectDetails`
- **File:** `src/services/storageService.js`
- **Function:** `getObjectDetails(bucketName, key)`
- **Mock Response:** `devStore.getObject(bucketName, key)`.
- **Real Endpoint Required:** `GET /buckets/{bucketName}/objects/{key}/details`
- **Expected Production Behavior:** Returns comprehensive entity joining `objects`, `object_versions`, `object_chunks`, `chunk_replicas`, and `storage_nodes`. Includes physical node locations and stored SHA-256 hash.

---

### Fallback 7: `storageService.uploadObject`
- **File:** `src/services/storageService.js`
- **Function:** `uploadObject(bucketName, key, file, onProgress)`
- **Mock Response:** Simulated 4-step interval progress callback yielding `devStore.addObject(...)` with simulated SHA-256 hash.
- **Real Endpoint Required:** `POST /buckets/{bucketName}/objects/upload` (`multipart/form-data`)
- **Expected Production Behavior:** Coordinator chunks incoming binary payload into 4MB blocks, calculates SHA-256, streams chunks in parallel to storage node ports (5001–5006), verifies write quorum (e.g. W=2), and commits version in PostgreSQL.

---

### Fallback 8: `storageService.downloadObject`
- **File:** `src/services/storageService.js`
- **Function:** `downloadObject(bucketName, key, version)`
- **Mock Response:** Simulated download message confirming node read and mock SHA-256.
- **Real Endpoint Required:** `GET /buckets/{bucketName}/objects/{key}?version={version}`
- **Expected Production Behavior:** Coordinator issues concurrent read request to healthy replica nodes, computes on-the-fly checksum, verifies against stored SHA-256, and streams binary byte payload to client.

---

### Fallback 9: `storageService.deleteObject`
- **File:** `src/services/storageService.js`
- **Function:** `deleteObject(bucketName, key)`
- **Mock Response:** Marks `is_tombstone = true` in `devStore`.
- **Real Endpoint Required:** `DELETE /buckets/{bucketName}/objects/{key}`
- **Expected Production Behavior:** Soft-deletes by writing a new object version record with `is_tombstone = TRUE`. Does not immediately purge data plane bytes, enabling version rollback.

---

## 2. Admin Service Fallbacks (`src/services/adminService.js`)

### Fallback 10: `adminService.getClusterSummary`
- **File:** `src/services/adminService.js`
- **Function:** `getClusterSummary()`
- **Mock Response:** `DEV_CLUSTER_SUMMARY` (6 nodes, 1 degraded, 99.98% health, 60.0 GB raw capacity).
- **Real Endpoint Required:** `GET /admin/cluster`
- **Expected Production Behavior:** Coordinator queries `storage_nodes` table, computes node health based on 3-second heartbeat timeouts, and tallies cluster capacity.

---

### Fallback 11: `adminService.listNodes`
- **File:** `src/services/adminService.js`
- **Function:** `listNodes()`
- **Mock Response:** `DEV_NODES` (6 nodes, ports 5001–5006, Zone A / Zone B, Node 03 status `RECOVERING`).
- **Real Endpoint Required:** `GET /admin/nodes`
- **Expected Production Behavior:** Returns real daemon process telemetry from coordinator's node heartbeat tracker.

---

### Fallback 12: `adminService.getNodeDetails`
- **File:** `src/services/adminService.js`
- **Function:** `getNodeDetails(nodeId)`
- **Mock Response:** Node entity from `DEV_NODES` with local `storage/nodeX/` path and recent node events.
- **Real Endpoint Required:** `GET /admin/nodes/{nodeId}`
- **Expected Production Behavior:** Direct ping & stats query to node daemon endpoint `http://127.0.0.1:{5000+id}/health` combined with PostgreSQL metadata.

---

### Fallback 13: `adminService.getTopologyRelationships`
- **File:** `src/services/adminService.js`
- **Function:** `getTopologyRelationships()`
- **Mock Response:** `DEV_TOPOLOGY_RELATIONSHIPS` (Sample cross-zone mapping for 3 objects).
- **Real Endpoint Required:** `GET /admin/topology/relationships`
- **Expected Production Behavior:** Returns replica-to-node placement matrix from `chunk_replicas` table.

---

### Fallback 14: `adminService.getActiveRepairs`
- **File:** `src/services/adminService.js`
- **Function:** `getActiveRepairs()`
- **Mock Response:** `DEV_ACTIVE_REPAIRS` (1 active repair: `rep-7f2a` rebuilding Node 03 parity shard on Node 06).
- **Real Endpoint Required:** `GET /admin/repairs`
- **Expected Production Behavior:** Returns active jobs from `repair_jobs` table where `status = 'IN_PROGRESS'`.

---

### Fallback 15: `adminService.getRecentFailures`
- **File:** `src/services/adminService.js`
- **Function:** `getRecentFailures()`
- **Mock Response:** `DEV_RECENT_FAILURES` (3 incidents: Heartbeat Lost, Bit-rot Checksum Mismatch, Simulated Partition).
- **Real Endpoint Required:** `GET /admin/failures`
- **Expected Production Behavior:** Queries `cluster_events` table where `severity IN ('WARN', 'ERROR')` or `repair_jobs` with completed recovery duration.

---

### Fallback 16: `adminService.getDurabilityOverview`
- **File:** `src/services/adminService.js`
- **Function:** `getDurabilityOverview()`
- **Mock Response:** `DEV_DURABILITY_POLICIES` (`RF=3`, `RF=2`, `EC 4+2`).
- **Real Endpoint Required:** `GET /admin/durability`
- **Expected Production Behavior:** Aggregates storage consumption grouped by bucket `durability_policy`.

---

### Fallback 17: `adminService.getIntegrityOverview`
- **File:** `src/services/adminService.js`
- **Function:** `getIntegrityOverview()`
- **Mock Response:** `DEV_INTEGRITY_SUMMARY` (1036 verified, 0 corrupt, 18 repaired, SHA-256).
- **Real Endpoint Required:** `GET /admin/integrity`
- **Expected Production Behavior:** Telemetry from the background integrity scrubber daemon.

---

### Fallback 18: `adminService.getLiveEvents`
- **File:** `src/services/adminService.js`
- **Function:** `getLiveEvents(limit)`
- **Mock Response:** `DEV_LIVE_EVENTS` (6 structured log records).
- **Real Endpoint Required:** `GET /admin/events?limit={limit}`
- **Expected Production Behavior:** Top recent records from PostgreSQL `cluster_events` table sorted by timestamp descending.
