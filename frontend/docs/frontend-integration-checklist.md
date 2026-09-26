# NEXVAULT — Backend Integration & End-to-End Verification Checklist

Use this checklist during backend integration to verify that the FastAPI control plane and 6 storage node daemons connect seamlessly to the React frontend.

---

## 1. AUTHENTICATION & ACCESS CONTROL
- [ ] **Signup** (`POST /api/auth/signup`)
  - [ ] Registers new user in PostgreSQL `users` table with bcrypt password hashing.
  - [ ] Rejects duplicate username or email with `409 Conflict`.
  - [ ] Returns JWT token and user profile object.
- [ ] **Login** (`POST /api/auth/login`)
  - [ ] Verifies credentials and issues valid Bearer JWT.
  - [ ] Persists token in `localStorage['nexvault_auth_token']`.
  - [ ] Redirects `USER` to `/user/dashboard` and `ADMIN` to `/admin/overview`.
- [ ] **Protected Routes**
  - [ ] Unauthenticated requests to `/user/*` or `/admin/*` redirect immediately to `/login`.
  - [ ] Expired tokens (`401 Unauthorized`) purge local storage and redirect to login with a warning toast.
- [ ] **Admin Authorization**
  - [ ] Users with `role: "USER"` attempting to access `/admin/*` routes are redirected to `/user/dashboard`.
  - [ ] Frontend `api.js` blocks client-side requests to `/admin/*` or `/chaos/*` if unauthenticated.
  - [ ] Backend returns `403 Forbidden` if a standard user token calls admin endpoints.

---

## 2. USER STORAGE WORKFLOWS
- [ ] **Create Bucket** (`POST /api/buckets`)
  - [ ] Provisions bucket with selected policy: `REPLICATION_3`, `REPLICATION_2`, or `ERASURE_CODING_4_2`.
  - [ ] Enforces lowercase alphanumeric naming and prevents duplicate bucket names.
- [ ] **List Buckets** (`GET /api/buckets`)
  - [ ] Displays live list of buckets with object counts and computed logical storage.
  - [ ] Displays accurate physical overhead multiplier (`3.0x`, `2.0x`, or `1.5x`).
- [ ] **Upload Object** (`POST /api/buckets/{name}/objects/upload`)
  - [ ] Accepts `multipart/form-data` with file and logical key.
  - [ ] Frontend displays real-time chunk streaming progress bar.
  - [ ] Successful upload displays computed SHA-256 hash and assigned replica nodes.
  - [ ] Rejection if write quorum cannot be achieved (e.g. fewer than 2 active replicas).
- [ ] **Download Object** (`GET /api/buckets/{name}/objects/{key}`)
  - [ ] Coordinator coordinates read quorum from nearest healthy storage node.
  - [ ] Verifies on-disk chunk SHA-256 before streaming bytes to client.
  - [ ] Streams binary file with correct MIME type and `ETag`.
- [ ] **Object Metadata Deep Inspection** (`GET /api/buckets/{name}/objects/{key}/details`)
  - [ ] Basic view shows: Name, Size, MIME type, Created, Modified, Status.
  - [ ] Advanced view shows: Version, Stored SHA-256, Durability policy, Replica locations (`Node 01:5001`, etc.), and Integrity match confirmation.
- [ ] **Object Versions**
  - [ ] Uploading an existing key increments version number (`v1` ➔ `v2`).
  - [ ] Querying `?version=1` downloads previous historical version.
- [ ] **Delete / Tombstone** (`DELETE /api/buckets/{name}/objects/{key}`)
  - [ ] Soft-deletes by recording tombstone version record (`is_tombstone: true`).
  - [ ] Object is hidden from normal active explorer while audit trail is preserved.

---

## 3. DISTRIBUTED STORAGE & FAULT-TOLERANCE
- [ ] **Replication & Cross-Zone Placement**
  - [ ] RF=3 writes place at least 1 replica in Zone A (Nodes 1–3) and 1 in Zone B (Nodes 4–6).
  - [ ] RF=2 writes maintain a strict cross-zone pair.
- [ ] **Node Status & Heartbeat Tracking**
  - [ ] 6 independent processes running on ports `5001`, `5002`, `5003`, `5004`, `5005`, `5006`.
  - [ ] Heartbeat daemon pings each node's `/health` endpoint every 3 seconds.
  - [ ] Missing heartbeats transition node from `HEALTHY` ➔ `DEGRADED` ➔ `FAILED`.
- [ ] **Integrity Verification (SHA-256 Scrub)**
  - [ ] Background scrubber reads on-disk chunks from `storage/nodeX/` and recomputes SHA-256.
  - [ ] Stored checksum vs. calculated checksum match confirms healthy state.
- [ ] **Autonomous Replica Repair**
  - [ ] Detection of a missing/failed replica queues a background repair job.
  - [ ] Source replica copies chunks to target node; SHA-256 is verified before marking healthy.
  - [ ] Recovery duration (TTR in ms) and bytes healed are recorded in `repair_jobs`.
- [ ] **Cluster Rebalancing**
  - [ ] Evaluates node capacity skew; triggers rebalancing when imbalance > 15%.
  - [ ] Throttles migrations to protect foreground read/write bandwidth.
- [ ] **Network Partition Simulation**
  - [ ] Isolating a node cuts coordinator access while preserving node's local disk files.
  - [ ] Quorum continues serving reads/writes using surviving partition nodes.
  - [ ] Lifting partition allows node to sync missing updates.
- [ ] **Corruption Detection & Healing**
  - [ ] Injecting bit-rot flips bytes on storage node disk.
  - [ ] Scrubber flags mismatch, locates healthy secondary replica, rebuilds corrupted block, and restores integrity.

---

## 4. ADMIN CONTROL PLANE & OBSERVABILITY
- [ ] **Cluster Overview** (`GET /api/admin/cluster`)
  - [ ] Renders live topology map of Zone A and Zone B.
  - [ ] Displays cluster health percentage, available capacity, and active self-healing jobs.
  - [ ] Clicking any node opens `NodeDetailsModal`.
  - [ ] Clicking an active repair opens `RepairDetailsModal`.
- [ ] **Nodes Management** (`GET /api/admin/nodes`)
  - [ ] Displays all 6 daemons, storage directory paths, and disk quota usage.
  - [ ] Supports node drain actions prior to scheduled maintenance.
- [ ] **Repairs Console** (`GET /api/admin/repairs`)
  - [ ] Displays historical and active repair jobs, TTR benchmarks, and self-healed volume.
  - [ ] Supports manual emergency repair sweep dispatch.
- [ ] **Integrity Console** (`GET /api/admin/integrity`)
  - [ ] Displays verified objects count, bit-rot history, and last scrub timestamp.
  - [ ] "Trigger Full Integrity Scrub" dispatches cluster-wide SHA-256 check.
- [ ] **Live Backend Event Stream** (`GET /api/events` SSE)
  - [ ] Streams structured JSON log records: Heartbeat lost, Node marked FAILED, Repair started, Checksum verified, Object restored.
- [ ] **Metrics & Overhead** (`GET /api/admin/metrics`)
  - [ ] Verifies availability SLA, RF=3 (3.0x) vs EC 4+2 (1.5x) overhead comparison, and p50/p99 latency.
- [ ] **Chaos Engineering Lab** (`/admin/chaos`)
  - [ ] Restricted strictly to `ADMIN` users.
  - [ ] Controls: Kill Node, Restore Node, Partition Route, Heal Route, Corrupt Replica, and Reset Cluster.
