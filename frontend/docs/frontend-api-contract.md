# NEXVAULT — Frontend API Contract Specification
**System:** NEXVAULT Fault-Tolerant Distributed Object Storage  
**Control Plane Protocol:** REST / JSON / Server-Sent Events (SSE)  
**Base URL:** `http://localhost:8000/api` (Default via `VITE_API_BASE_URL`)

---

## 1. AUTH

### `authService.signup`
- **Method:** `POST`
- **Endpoint:** `/auth/signup`
- **Auth Required:** No
- **Role Required:** Public
- **Request Body:**
  ```json
  {
    "username": "teja_admin",
    "email": "teja@nexvault.io",
    "password": "SecurePassword123!",
    "role": "ADMIN" // "USER" | "ADMIN"
  }
  ```
- **Expected Response (201 Created):**
  ```json
  {
    "id": "usr-8a291f0",
    "username": "teja_admin",
    "email": "teja@nexvault.io",
    "role": "ADMIN",
    "created_at": "2026-09-26T02:00:00Z"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Password does not meet complexity requirements.
  - `409 Conflict`: Username or email already registered.
  - `422 Unprocessable Entity`: Malformed JSON schema.

---

### `authService.login`
- **Method:** `POST`
- **Endpoint:** `/auth/login`
- **Auth Required:** No
- **Role Required:** Public
- **Request Body:**
  ```json
  {
    "username": "teja_admin",
    "password": "SecurePassword123!"
  }
  ```
- **Expected Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "usr-8a291f0",
      "username": "teja_admin",
      "email": "teja@nexvault.io",
      "role": "ADMIN"
    }
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Invalid credentials.
  - `429 Too Many Requests`: Account lock or brute force rate limit.

---

### `authService.getMe`
- **Method:** `GET`
- **Endpoint:** `/auth/me`
- **Auth Required:** Yes (Bearer JWT)
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):**
  ```json
  {
    "id": "usr-8a291f0",
    "username": "teja_admin",
    "email": "teja@nexvault.io",
    "role": "ADMIN"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Token missing, malformed, or expired.

---

## 2. BUCKETS

### `storageService.listBuckets`
- **Method:** `GET`
- **Endpoint:** `/buckets`
- **Auth Required:** Yes (Bearer JWT)
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):**
  ```json
  [
    {
      "id": "b-101",
      "name": "production-backups",
      "policy": "REPLICATION_3",
      "min_read_quorum": 1,
      "min_write_quorum": 2,
      "objectsCount": 842,
      "logicalSizeBytes": 5218738176,
      "created_at": "2026-09-10T12:00:00Z"
    }
  ]
  ```
- **Error Responses:**
  - `401 Unauthorized`: Missing or invalid session.

---

### `storageService.createBucket`
- **Method:** `POST`
- **Endpoint:** `/buckets`
- **Auth Required:** Yes (Bearer JWT)
- **Role Required:** `USER` or `ADMIN`
- **Request Body:**
  ```json
  {
    "name": "customer-analytics-vault",
    "policy": "REPLICATION_3" // "REPLICATION_3" | "REPLICATION_2" | "ERASURE_CODING_4_2"
  }
  ```
- **Expected Response (201 Created):**
  ```json
  {
    "id": "b-204",
    "name": "customer-analytics-vault",
    "policy": "REPLICATION_3",
    "min_read_quorum": 1,
    "min_write_quorum": 2,
    "objectsCount": 0,
    "logicalSizeBytes": 0,
    "created_at": "2026-09-26T02:30:00Z"
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Invalid bucket name formatting (must be lowercase alphanumeric + hyphens).
  - `409 Conflict`: Bucket name already exists.

---

### `storageService.getBucket`
- **Method:** `GET`
- **Endpoint:** `/buckets/{bucketId}`
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):** Bucket metadata entity.
- **Error Responses:**
  - `404 Not Found`: Bucket ID or name does not exist.

---

### `storageService.deleteBucket`
- **Method:** `DELETE`
- **Endpoint:** `/buckets/{bucketId}`
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (204 No Content or 200 OK):**
  ```json
  { "success": true, "message": "Bucket deleted successfully." }
  ```
- **Error Responses:**
  - `404 Not Found`: Bucket does not exist.
  - `409 Conflict`: Cannot delete non-empty bucket. Active objects must first be deleted.

---

## 3. OBJECTS

### `storageService.listObjects`
- **Method:** `GET`
- **Endpoint:** `/buckets/{bucketName}/objects` (or `/objects` for global listing)
- **Query Parameters:**
  - `prefix` (optional string): Key prefix for virtual folder hierarchy.
  - `limit` (optional integer): Pagination limit (default 100).
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):**
  ```json
  [
    {
      "id": "obj-001",
      "bucket": "production-backups",
      "name": "postgres_daily_dump.sql.gz",
      "key": "databases/postgres_daily_dump.sql.gz",
      "type": "application/gzip",
      "sizeBytes": 1932735283,
      "sizeFormatted": "1.80 GB",
      "version": 3,
      "is_tombstone": false,
      "is_latest": true,
      "created_at": "2026-09-24T04:15:00Z",
      "modified_at": "2026-09-26T01:45:00Z",
      "health": "HEALTHY",
      "availability": "100% (3/3 Nodes Available)",
      "durability": "RF=3 (Zone A & B)",
      "policy": "REPLICATION_3",
      "replication_factor": 3,
      "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "chunksCount": 461,
      "replicas": [
        { "node_id": 1, "name": "node-01", "zone": "Zone A", "port": 5001, "status": "HEALTHY" },
        { "node_id": 2, "name: "node-02", "zone": "Zone A", "port": 5002, "status": "HEALTHY" },
        { "node_id": 4, "name": "node-04", "zone": "Zone B", "port": 5004, "status": "HEALTHY" }
      ]
    }
  ]
  ```
- **Error Responses:**
  - `404 Not Found`: Bucket does not exist.

---

### `storageService.getObjectDetails`
- **Method:** `GET`
- **Endpoint:** `/buckets/{bucketName}/objects/{key}/details`
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):** Full object inspection entity containing Basic Metadata + Advanced Distributed Details (SHA-256 verification, replicas, chunk matrix, and availability state).
- **Error Responses:**
  - `404 Not Found`: Object key not found.

---

### `storageService.deleteObject`
- **Method:** `DELETE`
- **Endpoint:** `/buckets/{bucketName}/objects/{key}`
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):**
  ```json
  {
    "success": true,
    "tombstone_version": 4,
    "message": "Object version soft-deleted. Tombstone recorded; audit history preserved."
  }
  ```
- **Error Responses:**
  - `404 Not Found`: Object not found.

---

## 4. UPLOAD

### `storageService.uploadObject`
- **Method:** `POST`
- **Endpoint:** `/buckets/{bucketName}/objects/upload`
- **Content-Type:** `multipart/form-data`
- **Request Form Data:**
  - `file`: Binary file stream
  - `key`: Logical storage path (e.g., `databases/postgres_dump.sql.gz`)
- **Headers:** Optional `X-Expected-SHA256` for client-side precomputed hash validation.
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (201 Created):**
  ```json
  {
    "id": "obj-9817",
    "bucket": "production-backups",
    "key": "databases/postgres_dump.sql.gz",
    "sizeBytes": 4194304,
    "sizeFormatted": "4.0 MB",
    "version": 1,
    "checksum": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    "policy": "REPLICATION_3",
    "chunksCount": 1,
    "replicas": [
      { "node_id": 1, "zone": "Zone A", "port": 5001, "status": "HEALTHY" },
      { "node_id": 2, "zone": "Zone A", "port": 5002, "status": "HEALTHY" },
      { "node_id": 4, "zone": "Zone B", "port": 5004, "status": "HEALTHY" }
    ],
    "message": "Write quorum acknowledged by 3 nodes across Zone A and Zone B."
  }
  ```
- **Error Responses:**
  - `400 Bad Request`: Checksum mismatch (client vs computed).
  - `503 Service Unavailable`: Insufficient healthy storage nodes to achieve write quorum (e.g. fewer than 2 active replicas).
  - `504 Gateway Timeout`: Node communication timed out during chunk write.

---

## 5. DOWNLOAD

### `storageService.downloadObject`
- **Method:** `GET`
- **Endpoint:** `/buckets/{bucketName}/objects/{key}`
- **Query Parameters:**
  - `version` (optional integer): Retrieve a specific historical version (defaults to latest non-tombstone).
- **Auth Required:** Yes
- **Role Required:** `USER` or `ADMIN`
- **Expected Response (200 OK):**
  - **Headers:**
    - `Content-Type`: `application/octet-stream` (or object's MIME type)
    - `Content-Length`: Size in bytes
    - `ETag`: `"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"` (SHA-256)
    - `X-Nexvault-Nodes`: `1,2` (Nodes participating in quorum read)
  - **Body:** Binary payload stream
- **Error Responses:**
  - `404 Not Found`: Object or version not found (or latest version is a tombstone).
  - `503 Service Unavailable`: Insufficient healthy replicas or shards to reconstruct object.

---

## 6. VERSIONS

- Version tracking is built into `/buckets/{bucketName}/objects/{key}` endpoints via the `version` query parameter.
- The control plane increments the version number monotonically with each upload to the same key.
- Soft-deletions generate a tombstone version: `is_tombstone: true`.

---

## 7. ADMIN CLUSTER

### `adminService.getClusterSummary`
- **Method:** `GET`
- **Endpoint:** `/admin/cluster`
- **Auth Required:** Yes (Bearer JWT)
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):**
  ```json
  {
    "healthPercent": 99.98,
    "totalNodes": 6,
    "healthyNodes": 5,
    "failedNodes": 0,
    "degradedNodes": 1,
    "degradedObjects": 1,
    "activeRepairs": 1,
    "availabilitySLA": "99.999%",
    "totalCapacityBytes": 64424509440,
    "usedCapacityBytes": 22763326668,
    "availableCapacityBytes": 41661182772,
    "utilizationPercent": 35.3
  }
  ```
- **Error Responses:**
  - `401 Unauthorized`: Unauthenticated.
  - `403 Forbidden`: User has role `USER` instead of `ADMIN`.

---

## 8. NODES

### `adminService.listNodes`
- **Method:** `GET`
- **Endpoint:** `/admin/nodes`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):**
  ```json
  [
    {
      "id": 1,
      "name": "Node 01",
      "daemon": "node-01",
      "port": 5001,
      "zone": "Zone A",
      "status": "HEALTHY", // "HEALTHY" | "DEGRADED" | "FAILED" | "RECOVERING"
      "storageDir": "storage/node1/",
      "totalBytes": 10737418240,
      "usedBytes": 3887010611,
      "percent": 36.2,
      "objectsCount": 248,
      "replicaCount": 742,
      "lastHeartbeat": "0.8s ago",
      "pingMs": 1.8,
      "uptime": "14d 6h 22m"
    }
  ]
  ```

### `adminService.getNodeDetails`
- **Method:** `GET`
- **Endpoint:** `/admin/nodes/{nodeId}`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Node details object + `recentEvents` array.

---

## 9. REPLICATION

### `adminService.getDurabilityOverview`
- **Method:** `GET`
- **Endpoint:** `/admin/durability`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Breakdown of policies (`REPLICATION_3`, `REPLICATION_2`, `ERASURE_CODING_4_2`), overhead multipliers, objects count, and raw usage.

### `adminService.getTopologyRelationships`
- **Method:** `GET`
- **Endpoint:** `/admin/topology/relationships`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Cross-zone object replica mapping array.

---

## 10. INTEGRITY

### `adminService.getIntegrityOverview`
- **Method:** `GET`
- **Endpoint:** `/admin/integrity`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):**
  ```json
  {
    "objectsVerified": 1036,
    "integrityFailures": 1,
    "corruptReplicas": 0,
    "replicasRepaired": 18,
    "lastScrub": "4 minutes ago",
    "algorithm": "SHA-256 Cryptographic Checksum"
  }
  ```

### `adminService.triggerIntegrityScrub`
- **Method:** `POST`
- **Endpoint:** `/admin/integrity/scrub`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (202 Accepted):** Scrub task dispatched.

---

## 11. REPAIRS

### `adminService.getActiveRepairs`
- **Method:** `GET`
- **Endpoint:** `/admin/repairs`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Array of active self-healing jobs.

### `adminService.triggerEmergencyRepair`
- **Method:** `POST`
- **Endpoint:** `/admin/repairs/trigger`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (202 Accepted):** Emergency sweep dispatched.

---

## 12. REBALANCING

### `adminService.getRebalanceMetrics`
- **Method:** `GET`
- **Endpoint:** `/admin/rebalance/status`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Max skew percentage, zone symmetry, threshold.

### `adminService.triggerRebalance`
- **Method:** `POST`
- **Endpoint:** `/admin/rebalance/trigger`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Rebalance decision and migration schedule.

---

## 13. EVENTS

### `adminService.getLiveEvents`
- **Method:** `GET`
- **Endpoint:** `/admin/events?limit={limit}`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):** Array of structured event log records.

### `adminService.subscribeEvents` (SSE Stream)
- **Method:** `GET` (Streaming)
- **Endpoint:** `/events`
- **Headers:** `Accept: text/event-stream`
- **Expected Stream Events:** Server-Sent Events containing JSON encoded state transitions (`HEARTBEAT`, `INTEGRITY`, `REPAIR`, `CHAOS`).

---

## 14. CHAOS LAB

All Chaos Lab endpoints are strictly restricted to `ADMIN` role.

| Function | Method | Endpoint | Request Body |
|---|---|---|---|
| `chaosService.killNode` | `POST` | `/chaos/kill-node/{nodeId}` | `{}` |
| `chaosService.restoreNode` | `POST` | `/chaos/restore-node/{nodeId}` | `{}` |
| `chaosService.partitionNode` | `POST` | `/chaos/partition-node/{nodeId}` | `{"isolated": true}` |
| `chaosService.healPartition` | `POST` | `/chaos/heal-partition/{nodeId}` | `{}` |
| `chaosService.corruptReplica` | `POST` | `/chaos/corrupt-replica` | `{"node_id": 3, "chunk_id": "..."}` |
| `chaosService.triggerClusterScrub`| `POST` | `/chaos/trigger-scrub` | `{}` |
| `chaosService.triggerEmergencyRepair`| `POST` | `/chaos/trigger-repair` | `{}` |

---

## 15. METRICS

### `adminService.getMetrics`
- **Method:** `GET`
- **Endpoint:** `/admin/metrics`
- **Auth Required:** Yes
- **Role Required:** `ADMIN`
- **Expected Response (200 OK):**
  ```json
  {
    "availability": "99.999%",
    "ttrMs": 438,
    "recoveredBytes": 75497472,
    "clusterUtilization": 35.3
  }
  ```
