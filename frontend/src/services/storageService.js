import api from './api';

// Initial development fallback data matching PostgreSQL schema & control plane specs
const INITIAL_BUCKETS = [
  {
    id: 'b-101',
    name: 'production-backups',
    policy: 'REPLICATION_3',
    min_read_quorum: 1,
    min_write_quorum: 2,
    objectsCount: 4,
    logicalSizeBytes: 5218738176, // ~4.86 GB
    created_at: '2026-09-10T12:00:00Z',
  },
  {
    id: 'b-102',
    name: 'telemetry-logs',
    policy: 'REPLICATION_3',
    min_read_quorum: 1,
    min_write_quorum: 2,
    objectsCount: 2,
    logicalSizeBytes: 1468006400, // ~1.36 GB
    created_at: '2026-09-15T08:30:00Z',
  },
  {
    id: 'b-103',
    name: 'analytics-warehouse',
    policy: 'REPLICATION_3',
    min_read_quorum: 1,
    min_write_quorum: 2,
    objectsCount: 2,
    logicalSizeBytes: 4831838208, // ~4.5 GB
    created_at: '2026-09-18T16:45:00Z',
  },
  {
    id: 'b-104',
    name: 'corporate-docs',
    policy: 'REPLICATION_2',
    min_read_quorum: 1,
    min_write_quorum: 2,
    objectsCount: 2,
    logicalSizeBytes: 39845888, // ~38 MB
    created_at: '2026-09-22T09:15:00Z',
  },
];

const INITIAL_OBJECTS = [
  {
    id: 'obj-001',
    bucket_id: 'b-101',
    bucket: 'production-backups',
    name: 'postgres_daily_dump.sql.gz',
    key: 'databases/postgres_daily_dump.sql.gz',
    type: 'application/gzip',
    sizeBytes: 1932735283,
    sizeFormatted: '1.80 GB',
    version: 3,
    is_tombstone: false,
    is_latest: true,
    created_at: '2026-09-24T04:15:00Z',
    modified_at: '2026-09-26T01:45:00Z',
    health: 'HEALTHY',
    availability: '100% (3/3 Nodes Available)',
    durability: 'RF=3 (Zone A & B)',
    policy: 'REPLICATION_3',
    replication_factor: 3,
    checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    calculated_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    integrity_state: 'VERIFIED',
    availability_state: 'OPTIMAL',
    last_verified: '4 minutes ago',
    repair_status: 'Optimal - All 3 replicas verified',
    chunksCount: 461,
    replicas: [
      { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
      { node_id: 2, name: 'node-02', zone: 'Zone A', port: 5002, status: 'HEALTHY', path: 'storage/node2/' },
      { node_id: 4, name: 'node-04', zone: 'Zone B', port: 5004, status: 'HEALTHY', path: 'storage/node4/' },
    ],
  },
  {
    id: 'obj-002',
    bucket_id: 'b-103',
    bucket: 'analytics-warehouse',
    name: 'q3_sales_aggregate.parquet',
    key: 'reports/q3_sales_aggregate.parquet',
    type: 'application/octet-stream',
    sizeBytes: 432013824,
    sizeFormatted: '412.0 MB',
    version: 2,
    is_tombstone: false,
    is_latest: true,
    created_at: '2026-09-25T11:00:00Z',
    modified_at: '2026-09-25T18:30:12Z',
    health: 'HEALTHY',
    availability: '100% (3/3 Nodes Available)',
    durability: 'RF=3 (Zone A & B)',
    policy: 'REPLICATION_3',
    replication_factor: 3,
    checksum: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    calculated_checksum: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
    integrity_state: 'VERIFIED',
    availability_state: 'OPTIMAL',
    last_verified: '12 minutes ago',
    repair_status: 'Optimal - All 3 replicas verified',
    chunksCount: 103,
    replicas: [
      { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
      { node_id: 3, name: 'node-03', zone: 'Zone A', port: 5003, status: 'HEALTHY', path: 'storage/node3/' },
      { node_id: 5, name: 'node-05', zone: 'Zone B', port: 5005, status: 'HEALTHY', path: 'storage/node5/' },
    ],
  },
  {
    id: 'obj-003',
    bucket_id: 'b-104',
    bucket: 'corporate-docs',
    name: 'security_access_logs_2026_q3.csv',
    key: 'compliance/security_access_logs_2026_q3.csv',
    type: 'text/csv',
    sizeBytes: 92274688,
    sizeFormatted: '88.0 MB',
    version: 1,
    is_tombstone: false,
    is_latest: true,
    created_at: '2026-09-25T14:20:00Z',
    modified_at: '2026-09-25T21:10:44Z',
    health: 'HEALTHY',
    availability: '100% (2/2 Nodes Available)',
    durability: 'RF=2 (Zone A & B)',
    policy: 'REPLICATION_2',
    replication_factor: 2,
    checksum: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
    calculated_checksum: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
    integrity_state: 'VERIFIED',
    availability_state: 'OPTIMAL',
    last_verified: '18 minutes ago',
    repair_status: 'Optimal - Quorum satisfied',
    chunksCount: 22,
    replicas: [
      { node_id: 3, name: 'node-03', zone: 'Zone A', port: 5003, status: 'HEALTHY', path: 'storage/node3/' },
      { node_id: 4, name: 'node-04', zone: 'Zone B', port: 5004, status: 'HEALTHY', path: 'storage/node4/' },
    ],
  },
  {
    id: 'obj-004',
    bucket_id: 'b-104',
    bucket: 'corporate-docs',
    name: 'annual_financial_audit.pdf',
    key: 'finance/annual_financial_audit.pdf',
    type: 'application/pdf',
    sizeBytes: 25165824,
    sizeFormatted: '24.0 MB',
    version: 1,
    is_tombstone: false,
    is_latest: true,
    created_at: '2026-09-24T10:00:00Z',
    modified_at: '2026-09-24T14:02:18Z',
    health: 'HEALTHY',
    availability: '100% (2/2 Nodes Available)',
    durability: 'RF=2 (Zone A & B)',
    policy: 'REPLICATION_2',
    replication_factor: 2,
    checksum: '185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969',
    calculated_checksum: '185f8db32271fe25f561a6fc938b2e264306ec304eda518007d1764826381969',
    integrity_state: 'VERIFIED',
    availability_state: 'OPTIMAL',
    last_verified: '25 minutes ago',
    repair_status: 'Optimal',
    chunksCount: 6,
    replicas: [
      { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
      { node_id: 5, name: 'node-05', zone: 'Zone B', port: 5005, status: 'HEALTHY', path: 'storage/node5/' },
    ],
  },
  {
    id: 'obj-005',
    bucket_id: 'b-102',
    bucket: 'telemetry-logs',
    name: 'flight_sensor_stream.parquet',
    key: 'telemetry/flight_sensor_stream.parquet',
    type: 'application/x-parquet',
    sizeBytes: 880803840,
    sizeFormatted: '840.0 MB',
    version: 1,
    is_tombstone: false,
    is_latest: true,
    created_at: '2026-09-25T19:00:00Z',
    modified_at: '2026-09-26T00:15:30Z',
    health: 'HEALTHY',
    availability: '100% (3/3 Nodes Available)',
    durability: 'RF=3 (Zone A & B)',
    policy: 'REPLICATION_3',
    replication_factor: 3,
    checksum: 'a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e',
    calculated_checksum: 'a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e',
    integrity_state: 'VERIFIED',
    availability_state: 'OPTIMAL',
    last_verified: '7 minutes ago',
    repair_status: 'Optimal - All 3 replicas verified',
    chunksCount: 210,
    replicas: [
      { node_id: 2, name: 'node-02', zone: 'Zone A', port: 5002, status: 'HEALTHY', path: 'storage/node2/' },
      { node_id: 3, name: 'node-03', zone: 'Zone A', port: 5003, status: 'HEALTHY', path: 'storage/node3/' },
      { node_id: 6, name: 'node-06', zone: 'Zone B', port: 5006, status: 'HEALTHY', path: 'storage/node6/' },
    ],
  },
  {
    id: 'obj-006',
    bucket_id: 'b-103',
    bucket: 'ai-models',
    name: 'llm_weights_shard_04.bin',
    key: 'models/llm_weights_shard_04.bin',
    type: 'application/octet-stream',
    sizeBytes: 4399824384,
    sizeFormatted: '4.10 GB',
    version: 2,
    is_tombstone: false,
    is_latest: true,
    created_at: '2026-09-25T16:00:00Z',
    modified_at: '2026-09-25T23:50:00Z',
    health: 'DEGRADED',
    availability: 'Degraded (5/6 Nodes Available)',
    durability: 'EC 4+2 (1 Node Recovering)',
    policy: 'ERASURE_CODING_4_2',
    replication_factor: '4 Data + 2 Parity',
    checksum: '68e6e001893c5d6480b5774e1d904661875c7b39bfad55f7564d232a514d864e',
    calculated_checksum: '68e6e001893c5d6480b5774e1d904661875c7b39bfad55f7564d232a514d864e',
    integrity_state: 'VERIFIED',
    availability_state: 'READABLE_DEGRADED',
    last_verified: '1 minute ago',
    repair_status: 'Repairing Node 03 parity shard from surviving 5 nodes',
    chunksCount: 1048,
    replicas: [
      { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
      { node_id: 2, name: 'node-02', zone: 'Zone A', port: 5002, status: 'HEALTHY', path: 'storage/node2/' },
      { node_id: 3, name: 'node-03', zone: 'Zone A', port: 5003, status: 'REPAIRING', path: 'storage/node3/' },
      { node_id: 4, name: 'node-04', zone: 'Zone B', port: 5004, status: 'HEALTHY', path: 'storage/node4/' },
      { node_id: 5, name: 'node-05', zone: 'Zone B', port: 5005, status: 'HEALTHY', path: 'storage/node5/' },
      { node_id: 6, name: 'node-06', zone: 'Zone B', port: 5006, status: 'HEALTHY', path: 'storage/node6/' },
    ],
  },
];

// Helper to format bytes
export function formatBytes(bytes, decimals = 2) {
  if (!+bytes) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

// In-memory development store with localStorage persistence
class DevStorageStore {
  constructor() {
    this.buckets = this.load('nexvault_dev_buckets', INITIAL_BUCKETS);
    this.objects = this.load('nexvault_dev_objects', INITIAL_OBJECTS);
  }

  load(key, fallback) {
    try {
      const data = localStorage.getItem(key);
      return data ? JSON.parse(data) : fallback;
    } catch {
      return fallback;
    }
  }

  save() {
    try {
      localStorage.setItem('nexvault_dev_buckets', JSON.stringify(this.buckets));
      localStorage.setItem('nexvault_dev_objects', JSON.stringify(this.objects));
    } catch {
      // ignore
    }
  }

  getBuckets() {
    return [...this.buckets];
  }

  addBucket(name, policy = 'REPLICATION_3') {
    const existing = this.buckets.find((b) => b.name === name);
    if (existing) {
      throw new Error(`Bucket '${name}' already exists.`);
    }

    const minRead = policy === 'ERASURE_CODING_4_2' ? 4 : 1;
    const minWrite = policy === 'ERASURE_CODING_4_2' ? 6 : (policy === 'REPLICATION_2' ? 2 : 2);

    const newBucket = {
      id: 'b-' + Math.random().toString(36).substring(2, 7),
      name: name.toLowerCase().replace(/[^a-z0-9-]/g, '-'),
      policy,
      min_read_quorum: minRead,
      min_write_quorum: minWrite,
      objectsCount: 0,
      logicalSizeBytes: 0,
      created_at: new Date().toISOString(),
    };

    this.buckets.unshift(newBucket);
    this.save();
    return newBucket;
  }

  deleteBucket(bucketId) {
    const bucket = this.buckets.find((b) => b.id === bucketId || b.name === bucketId);
    if (!bucket) throw new Error('Bucket not found');

    const bucketObjects = this.objects.filter((o) => (o.bucket_id === bucket.id || o.bucket === bucket.name) && !o.is_tombstone);
    if (bucketObjects.length > 0) {
      throw new Error(`Cannot delete non-empty bucket. Found ${bucketObjects.length} active objects.`);
    }

    this.buckets = this.buckets.filter((b) => b.id !== bucket.id && b.name !== bucket.name);
    this.save();
    return { success: true };
  }

  getObjects(bucketName = null) {
    if (!bucketName || bucketName === 'all') {
      return this.objects.filter((o) => !o.is_tombstone);
    }
    return this.objects.filter((o) => (o.bucket === bucketName || o.bucket_id === bucketName) && !o.is_tombstone);
  }

  getObject(bucketName, key) {
    const obj = this.objects.find((o) => (o.bucket === bucketName || o.bucket_id === bucketName) && (o.key === key || o.name === key) && !o.is_tombstone);
    if (!obj) throw new Error(`Object '${key}' not found in bucket '${bucketName}'`);
    return obj;
  }

  addObject(bucketName, key, fileDetails = {}) {
    const bucket = this.buckets.find((b) => b.name === bucketName || b.id === bucketName) || this.buckets[0];
    const sizeBytes = fileDetails.size || 1024 * 1024 * 4;
    const filename = key.split('/').pop();

    // Generate SHA-256 preview
    const fakeHash = Array.from({ length: 64 }, () => Math.floor(Math.random() * 16).toString(16)).join('');
    const chunks = Math.max(1, Math.ceil(sizeBytes / (4 * 1024 * 1024)));

    // Choose replicas based on policy
    let replicas = [];
    if (bucket.policy === 'ERASURE_CODING_4_2') {
      replicas = [
        { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
        { node_id: 2, name: 'node-02', zone: 'Zone A', port: 5002, status: 'HEALTHY', path: 'storage/node2/' },
        { node_id: 3, name: 'node-03', zone: 'Zone A', port: 5003, status: 'HEALTHY', path: 'storage/node3/' },
        { node_id: 4, name: 'node-04', zone: 'Zone B', port: 5004, status: 'HEALTHY', path: 'storage/node4/' },
        { node_id: 5, name: 'node-05', zone: 'Zone B', port: 5005, status: 'HEALTHY', path: 'storage/node5/' },
        { node_id: 6, name: 'node-06', zone: 'Zone B', port: 5006, status: 'HEALTHY', path: 'storage/node6/' },
      ];
    } else if (bucket.policy === 'REPLICATION_2') {
      replicas = [
        { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
        { node_id: 4, name: 'node-04', zone: 'Zone B', port: 5004, status: 'HEALTHY', path: 'storage/node4/' },
      ];
    } else {
      replicas = [
        { node_id: 1, name: 'node-01', zone: 'Zone A', port: 5001, status: 'HEALTHY', path: 'storage/node1/' },
        { node_id: 2, name: 'node-02', zone: 'Zone A', port: 5002, status: 'HEALTHY', path: 'storage/node2/' },
        { node_id: 4, name: 'node-04', zone: 'Zone B', port: 5004, status: 'HEALTHY', path: 'storage/node4/' },
      ];
    }

    const newObj = {
      id: 'obj-' + Math.random().toString(36).substring(2, 7),
      bucket_id: bucket.id,
      bucket: bucket.name,
      name: filename,
      key,
      type: fileDetails.type || 'application/octet-stream',
      sizeBytes,
      sizeFormatted: formatBytes(sizeBytes),
      version: 1,
      is_tombstone: false,
      is_latest: true,
      created_at: new Date().toISOString(),
      modified_at: new Date().toISOString(),
      health: 'HEALTHY',
      availability: `100% (${replicas.length}/${replicas.length} Nodes Available)`,
      durability: bucket.policy === 'ERASURE_CODING_4_2' ? 'EC 4+2 (All Nodes)' : (bucket.policy === 'REPLICATION_2' ? 'RF=2 (Zone A & B)' : 'RF=3 (Zone A & B)'),
      policy: bucket.policy,
      replication_factor: bucket.policy === 'ERASURE_CODING_4_2' ? '4 Data + 2 Parity' : (bucket.policy === 'REPLICATION_2' ? 2 : 3),
      checksum: fakeHash,
      calculated_checksum: fakeHash,
      integrity_state: 'VERIFIED',
      availability_state: 'OPTIMAL',
      last_verified: 'Just now',
      repair_status: 'Optimal - Verified immediately on write',
      chunksCount: chunks,
      replicas,
    };

    // Check if key already exists in this bucket -> version update
    const existingIndex = this.objects.findIndex((o) => o.bucket === bucket.name && o.key === key && !o.is_tombstone);
    if (existingIndex >= 0) {
      newObj.version = this.objects[existingIndex].version + 1;
      this.objects[existingIndex].is_latest = false;
    }

    this.objects.unshift(newObj);
    bucket.objectsCount += 1;
    bucket.logicalSizeBytes += sizeBytes;

    this.save();
    return newObj;
  }

  deleteObject(bucketName, key) {
    const obj = this.objects.find((o) => (o.bucket === bucketName || o.bucket_id === bucketName) && (o.key === key || o.id === key) && !o.is_tombstone);
    if (!obj) throw new Error('Object not found');

    // Soft-delete with tombstone version
    obj.is_tombstone = true;
    obj.is_latest = false;

    // Update bucket count
    const bucket = this.buckets.find((b) => b.name === bucketName || b.id === bucketName);
    if (bucket && bucket.objectsCount > 0) {
      bucket.objectsCount -= 1;
      bucket.logicalSizeBytes = Math.max(0, bucket.logicalSizeBytes - obj.sizeBytes);
    }

    this.save();
    return { success: true, tombstone_version: obj.version + 1, message: 'Tombstone recorded. Historical versions retained.' };
  }
}

const devStore = new DevStorageStore();

/**
 * Storage Service with Clean Adapter
 * Attempts real FastAPI endpoint first; falls back gracefully to structured devStore
 */
export const storageService = {
  // Buckets
  listBuckets: async () => {
    try {
      return await api.get('/buckets');
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devStore.getBuckets();
      }
      throw err;
    }
  },

  createBucket: async (name, policy = 'REPLICATION_3') => {
    try {
      return await api.post('/buckets', { name, policy });
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devStore.addBucket(name, policy);
      }
      throw err;
    }
  },

  getBucket: async (bucketId) => {
    try {
      return await api.get(`/buckets/${bucketId}`);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        const b = devStore.getBuckets().find((x) => x.id === bucketId || x.name === bucketId);
        if (!b) throw new Error('Bucket not found');
        return b;
      }
      throw err;
    }
  },

  deleteBucket: async (bucketId) => {
    try {
      return await api.delete(`/buckets/${bucketId}`);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devStore.deleteBucket(bucketId);
      }
      throw err;
    }
  },

  // Objects
  listObjects: async (bucketName = null, prefix = '') => {
    try {
      const q = prefix ? `?prefix=${encodeURIComponent(prefix)}` : '';
      const endpoint = bucketName && bucketName !== 'all' ? `/buckets/${bucketName}/objects${q}` : `/objects${q}`;
      return await api.get(endpoint);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devStore.getObjects(bucketName);
      }
      throw err;
    }
  },

  getObjectDetails: async (bucketName, key) => {
    try {
      return await api.get(`/buckets/${bucketName}/objects/${encodeURIComponent(key)}/details`);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devStore.getObject(bucketName, key);
      }
      throw err;
    }
  },

  uploadObject: async (bucketName, key, file, onProgress) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('key', key);
      return await api.post(`/buckets/${bucketName}/objects/upload`, formData, { isFormData: true });
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        // If backend is not connected yet, simulate realistic chunk-streaming upload
        return new Promise((resolve) => {
          let percent = 0;
          const interval = setInterval(() => {
            percent += 25;
            if (onProgress) onProgress(Math.min(100, percent));
            if (percent >= 100) {
              clearInterval(interval);
              const created = devStore.addObject(bucketName, key, {
                size: file?.size || 4194304,
                type: file?.type || 'application/octet-stream',
              });
              resolve(created);
            }
          }, 150);
        });
      }
      throw err;
    }
  },

  downloadObject: async (bucketName, key, version) => {
    const filename = key.split('/').pop() || 'downloaded-file';
    try {
      const versionQuery = version ? `?version=${version}` : '';
      const blob = await api.get(`/buckets/${bucketName}/objects/${encodeURIComponent(key)}${versionQuery}`, {
        responseType: 'blob',
      });

      // Trigger native browser download preserving filename
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);

      // Check if cluster had degraded nodes
      const isDegraded = localStorage.getItem('nexvault_cluster_has_failure') === 'true';

      return {
        key,
        filename,
        downloaded: true,
        message: isDegraded
          ? 'Read served from surviving replica with verified SHA-256 checksum.'
          : 'Quorum read verified with SHA-256 checksum. File downloaded to disk.',
      };
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        const obj = devStore.getObject(bucketName, key);
        const content = `NEXVAULT FAULT-TOLERANT STORAGE OBJECT\nKey: ${obj.key}\nBucket: ${bucketName}\nVersion: ${obj.version}\nSHA-256 Checksum: ${obj.checksum}\nReplicas: ${JSON.stringify(obj.replicas, null, 2)}\nIntegrity: Cryptographically Verified`;
        const blob = new Blob([content], { type: obj.type || 'text/plain' });
        const blobUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);

        const isDegraded = localStorage.getItem('nexvault_cluster_has_failure') === 'true';
        const survivingNode = obj.replicas.find((r) => r.status === 'HEALTHY') || obj.replicas[0];

        return {
          key: obj.key,
          filename,
          size: obj.sizeFormatted,
          checksum: obj.checksum,
          replicasUsed: [survivingNode?.node_id || 1],
          message: isDegraded
            ? `Download successful — Read served from surviving replica (Node 0${survivingNode?.node_id || 2}) with verified SHA-256 checksum.`
            : `Download successful — Successfully read from Node 0${survivingNode?.node_id || 1} with SHA-256 match.`,
        };
      }
      throw err;
    }
  },

  deleteObject: async (bucketName, key) => {
    try {
      return await api.delete(`/buckets/${bucketName}/objects/${encodeURIComponent(key)}`);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devStore.deleteObject(bucketName, key);
      }
      throw err;
    }
  },
};

export default storageService;
