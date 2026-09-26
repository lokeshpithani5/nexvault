# NEXVAULT — Frontend Integration & API Contract

**Base URL**: `http://127.0.0.1:8000/api/v1`  
**Swagger / OpenAPI Docs**: `http://127.0.0.1:8000/docs`  
**OpenAPI JSON**: `http://127.0.0.1:8000/openapi.json`

---

## 1. Authentication & Security Model

- **Method**: Bearer Token (JWT in `Authorization: Bearer <access_token>`).
- **Token Handling**:
  - Returned from `POST /auth/login` and `POST /auth/signup` in `access_token`.
  - Frontend client stores token in `localStorage.getItem("nexvault_token")` and attaches it via HTTP header `Authorization: Bearer <token>`.
  - If any API call returns `401 Unauthorized`, the frontend clears the token and prompts for login.
- **Role Detection**:
  - `role`: `"ADMIN"` or `"USER"`.
  - Stored inside the JWT payload (`payload.role`) and returned on `GET /auth/me` and `POST /auth/login`.
  - `USER` role can access Buckets, Objects, and Cluster Telemetry (read-only).
  - `ADMIN` role is required for Chaos Lab operations (`/chaos/*`) and Demo Reset (`/chaos/reset`).

### Pre-Seeded Hackathon Accounts
- **Administrator**: `admin@nexvault.io` / `admin123` (Role: `ADMIN`)
- **Standard Operator**: `demo@nexvault.io` / `demo123` (Role: `USER`)

---

## 2. API Endpoints Contract

### A. Authentication

#### `POST /auth/login`
- **Auth**: None
- **Request**:
  ```json
  {
    "email": "admin@nexvault.io",
    "password": "admin123"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user": {
      "id": "c1f7b884-...",
      "email": "admin@nexvault.io",
      "full_name": "Cluster Administrator",
      "role": "ADMIN",
      "is_active": true
    }
  }
  ```
- **Error Responses**:
  - `401 Unauthorized`: `{"detail": "Invalid email or password"}`

#### `POST /auth/signup`
- **Auth**: None
- **Request**:
  ```json
  {
    "email": "operator@nexvault.io",
    "password": "secretpassword",
    "full_name": "Operator Name",
    "role": "USER"
  }
  ```
- **Response** (`200 OK`): TokenResponse object as above.
- **Error Responses**:
  - `400 Bad Request`: `{"detail": "User with this email already exists"}`

#### `GET /auth/me`
- **Auth**: `Bearer <token>`
- **Response** (`200 OK`):
  ```json
  {
    "id": "c1f7b884-...",
    "email": "admin@nexvault.io",
    "full_name": "Cluster Administrator",
    "role": "ADMIN",
    "is_active": true
  }
  ```

---

### B. Buckets & Namespace Management

#### `GET /buckets`
- **Auth**: `Bearer <token>`
- **Response** (`200 OK`): Array of buckets:
  ```json
  [
    {
      "id": "b1a2c3d4-...",
      "name": "production-data",
      "owner_id": "c1f7b884-...",
      "replication_factor": 3,
      "durability_policy": "REPLICATION_3X",
      "object_count": 8,
      "total_bytes": 147415,
      "created_at": "2026-09-26T00:00:00Z"
    }
  ]
  ```

#### `POST /buckets`
- **Auth**: `Bearer <token>`
- **Request**:
  ```json
  {
    "name": "backup-archives",
    "replication_factor": 3,
    "durability_policy": "REPLICATION_3X"
  }
  ```
- **Response** (`201 Created`): Returns created Bucket object.
- **Error Responses**:
  - `400 Bad Request`: `{"detail": "Bucket with name 'backup-archives' already exists"}`
  - `422 Unprocessable Entity`: Validation failure on bucket name constraints.

#### `DELETE /buckets/{name}`
- **Auth**: `Bearer <token>`
- **Response** (`200 OK`): `{"deleted": true, "name": "backup-archives"}`

---

### C. Objects & Storage Operations

#### `GET /buckets/{bucket_name}/objects?include_deleted=false`
- **Auth**: `Bearer <token>`
- **Response** (`200 OK`):
  ```json
  [
    {
      "id": "e5f6a7b8-...",
      "key": "finance/q3_earnings_audit_2026.pdf",
      "version_num": 1,
      "size_bytes": 2894,
      "content_type": "application/pdf",
      "checksum_sha256": "8f4a2...",
      "storage_policy": "REPLICATION_3X",
      "is_deleted": false,
      "created_at": "2026-09-26T01:30:00Z",
      "replica_count": 3
    }
  ]
  ```

#### `POST /buckets/{bucket_name}/objects` (Upload)
- **Auth**: `Bearer <token>`
- **Format**: `multipart/form-data`
  - `file`: binary file payload (supports streaming large files >10 MB)
  - `key`: string (optional, defaults to `file.name`)
- **Response** (`201 Created`):
  ```json
  {
    "status": "UPLOADED",
    "bucket": "production-data",
    "key": "finance/q3_earnings_audit_2026.pdf",
    "version_num": 1,
    "size_bytes": 2894,
    "checksum_sha256": "8f4a2...",
    "replicas_placed": 3,
    "durability_policy": "REPLICATION_3X"
  }
  ```

#### `GET /buckets/{bucket_name}/objects/{key}` (Download)
- **Auth**: `Bearer <token>`
- **Query Params**: `version_num` (optional, defaults to latest)
- **Response** (`200 OK`):
  - Streams raw file binary content
  - Headers:
    - `Content-Disposition: attachment; filename="<filename>"`
    - `X-Content-SHA256: <sha256_hash>`
    - `X-NexVault-Version: 1`
    - `X-Durability-Policy: REPLICATION_3X`
- **Error Responses**:
  - `404 Not Found`: `{"detail": "Object '<key>' not found in bucket '<bucket_name>'"}`

#### `DELETE /buckets/{bucket_name}/objects/{key}`
- **Auth**: `Bearer <token>`
- **Behavior**: Appends soft-delete Tombstone version; preserves historical versions.
- **Response** (`200 OK`):
  ```json
  {
    "deleted": true,
    "bucket": "production-data",
    "key": "finance/q3_earnings_audit_2026.pdf",
    "tombstone_version": 2,
    "message": "Object soft-deleted with tombstone v2. Historical versions preserved."
  }
  ```

#### `GET /buckets/{bucket_name}/objects/{key}/details`
- **Auth**: `Bearer <token>`
- **Response** (`200 OK`): Complete version tree, physical node locations, zone distribution, and replica health matrix:
  ```json
  {
    "object_id": "e5f6a7b8-...",
    "bucket": "production-data",
    "key": "finance/q3_earnings_audit_2026.pdf",
    "is_deleted": false,
    "current_version_num": 1,
    "durability_policy": "REPLICATION_3X",
    "versions": [
      {
        "version_id": "v1-guid...",
        "version_num": 1,
        "size_bytes": 2894,
        "content_type": "application/pdf",
        "checksum_sha256": "8f4a2...",
        "is_tombstone": false,
        "storage_policy": "REPLICATION_3X",
        "created_at": "2026-09-26T01:30:00Z",
        "availability_state": "OPTIMAL",
        "healthy_replicas_count": 3,
        "required_replication_factor": 3,
        "replicas": [
          {
            "replica_id": "rep-1-...",
            "node_id": "node-1",
            "node_name": "Storage Node 1 (US-East-1A)",
            "zone": "ZONE_A",
            "port": 5001,
            "node_status": "HEALTHY",
            "node_partitioned": false,
            "blob_id": "production-data_finance_q3...blob",
            "replica_status": "HEALTHY",
            "stored_checksum": "8f4a2...",
            "last_verified_at": "2026-09-26T02:00:00Z",
            "error_detail": null
          }
        ]
      }
    ]
  }
  ```

---

### D. Cluster Telemetry & Observability

#### `GET /cluster/overview`
- **Auth**: Optional / `Bearer <token>`
- **Response** (`200 OK`):
  ```json
  {
    "status": "HEALTHY",
    "health_score_pct": 100.0,
    "nodes": {
      "total": 6,
      "healthy": 6,
      "degraded": 0,
      "failed": 0
    },
    "storage": {
      "total_capacity_bytes": 64424509440,
      "total_used_bytes": 435637,
      "available_bytes": 64424073803,
      "utilization_pct": 0.0
    },
    "inventory": {
      "buckets_count": 2,
      "active_objects_count": 8,
      "active_repairs_count": 0
    },
    "timestamp": "2026-09-26T02:15:00Z"
  }
  ```

#### `GET /cluster/nodes`
- **Auth**: Optional / `Bearer <token>`
- **Response** (`200 OK`): Array of 6 independent storage node status objects:
  ```json
  [
    {
      "id": "node-1",
      "name": "Storage Node 1 (US-East-1A)",
      "host": "127.0.0.1",
      "port": 5001,
      "zone": "ZONE_A",
      "status": "HEALTHY",
      "is_simulated_partitioned": false,
      "capacity_bytes": 10737418240,
      "used_bytes": 72606,
      "replica_count": 8,
      "last_heartbeat_at": "2026-09-26T02:15:00Z"
    }
  ]
  ```

#### `GET /cluster/metrics`
- **Auth**: Optional / `Bearer <token>`
- **Safety**: Guaranteed valid numeric types; zero-safe (no divide-by-zero or `null` values):
  ```json
  {
    "healthy_node_count": 6,
    "failed_node_count": 0,
    "degraded_node_count": 0,
    "degraded_object_count": 0,
    "repair_jobs_completed": 326,
    "repair_jobs_failed": 0,
    "bytes_recovered": 353965,
    "average_repair_duration_ms": 51.4,
    "last_repair_duration_ms": 46.0,
    "logical_storage": 147415,
    "physical_storage": 435637,
    "replication_overhead": 2.96,
    "cluster_utilization": 0.0,
    "node_availability_pct": 100.0,
    "active_nodes_count": 6,
    "total_nodes_count": 6
  }
  ```

#### `GET /cluster/repairs`
- **Auth**: Optional / `Bearer <token>`
- **Response** (`200 OK`):
  ```json
  {
    "repairs": [
      {
        "id": "job-guid...",
        "version_id": "ver-guid...",
        "source_node_id": "node-2",
        "target_node_id": "node-6",
        "status": "COMPLETED",
        "trigger_reason": "UNDER_REPLICATED",
        "bytes_recovered": 2894,
        "duration_ms": 50.0,
        "previous_replica_count": 2,
        "resulting_replica_count": 3,
        "started_at": "2026-09-26T02:10:00Z",
        "finished_at": "2026-09-26T02:10:00.050Z",
        "error_message": null,
        "created_at": "2026-09-26T02:10:00Z"
      }
    ],
    "rebalances": []
  }
  ```

---

### E. Events & Real-Time SSE Stream

#### `GET /events?limit=50&severity=ALL`
- **Auth**: Optional / `Bearer <token>`
- **Response** (`200 OK`): Array of structured distributed events ordered chronologically (newest first).

#### `GET /events/stream` (Live Server-Sent Events)
- **Auth**: Optional
- **Format**: `text/event-stream`
- **Browser Connection**:
  ```javascript
  const es = new EventSource("http://127.0.0.1:8000/api/v1/events/stream");
  es.onmessage = (e) => {
    const event = JSON.parse(e.data);
    console.log(event.event_type, event.message, event.metadata_json);
  };
  ```
- **Keep-Alive**: Automatic `: ping\n\n` comments every 15 seconds prevent connection drops.

---

### F. Chaos Lab & Demo Operations (ADMIN ONLY)

*Non-admin users calling these endpoints will receive `HTTP 403 Forbidden`.*

#### `POST /chaos/nodes/{node_id}/toggle-status`
- **Auth**: `ADMIN`
- **Action**: Simulates real process crash or restoration. Transitions node between `HEALTHY` and `FAILED`.
- **Response** (`200 OK`): `{"node_id": "node-1", "new_status": "FAILED"}`

#### `POST /chaos/nodes/{node_id}/partition`
- **Auth**: `ADMIN`
- **Action**: Toggles simulated network partition. Coordinator fails over to surviving zones while local disk remains 100% intact.
- **Response** (`200 OK`): `{"node_id": "node-1", "is_simulated_partitioned": true}`

#### `POST /chaos/replicas/{replica_id}/corrupt`
- **Auth**: `ADMIN`
- **Action**: Injects real on-disk bit-rot corruption into the replica's physical `.blob` file.
- **Response** (`200 OK`): `{"status": "CORRUPTED", "replica_id": "...", "node_id": "node-1"}`

#### `POST /chaos/scans/integrity`
- **Auth**: `ADMIN`
- **Action**: Triggers immediate cluster-wide cryptographic SHA-256 verification across all physical replicas.
- **Response** (`200 OK`): `{"total_replicas_scanned": 24, "corrupted_replicas_found": 0, "healthy_replicas": 24}`

#### `POST /chaos/repair/trigger`
- **Auth**: `ADMIN`
- **Action**: Triggers an immediate self-healing replica repair cycle.
- **Response** (`200 OK`): `{"completed_repairs": 1, "failed_repairs": 0}`

#### `POST /chaos/rebalance/trigger?force=true`
- **Auth**: `ADMIN`
- **Action**: Re-evaluates node storage loads and migrates replicas from overloaded to underloaded nodes.

#### `POST /chaos/reset` (Demo Reset Endpoint)
- **Auth**: `ADMIN`
- **Request**:
  ```json
  {
    "clean_test_objects": false,
    "trigger_scrub": true
  }
  ```
- **Action**:
  - Restores all 6 node processes and sets `status = "HEALTHY"`.
  - Clears all simulated network partitions.
  - Clears transient error flags on replicas.
  - Executes cryptographic integrity scan and self-repair.
  - Safe: Never destroys user data (`clean_test_objects` defaults to `false`).
- **Response** (`200 OK`):
  ```json
  {
    "status": "RESET_COMPLETE",
    "nodes_reset": 6,
    "partitions_cleared": 6,
    "objects_cleaned": 0,
    "message": "NEXVAULT cluster successfully restored to clean healthy operational state."
  }
  ```
