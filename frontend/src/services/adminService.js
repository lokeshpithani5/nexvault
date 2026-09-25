import api from './api';
import { formatBytes } from './storageService';

// Active listeners for event stream (both SSE and live simulated events)
const eventListeners = new Set();

export const dispatchClusterEvent = (event) => {
  eventListeners.forEach((listener) => {
    try {
      listener(event);
    } catch {
      // Listener closed
    }
  });
};

// In-memory cluster state for responsive dev fallback
let devClusterSummary = {
  health: 'HEALTHY',
  healthPercent: 100.0,
  totalNodes: 6,
  healthyNodes: 6,
  failedNodes: 0,
  degradedNodes: 0,
  degradedObjects: 0,
  activeRepairs: 0,
  availabilitySLA: '100%',
  totalCapacityBytes: 64424509440, // 60.0 GB
  usedCapacityBytes: 22763326668,  // 21.2 GB
  availableCapacityBytes: 41661182772, // 38.8 GB
  utilizationPercent: 35.3,
  storageOverhead: '3.0×',
  logicalStorage: '6.6 GB',
  physicalStorage: '19.8 GB',
  completedRepairs: 18,
  avgRepairDurationMs: 438,
};

let devNodes = [
  {
    id: 1,
    name: 'node-01',
    daemon: 'node-01',
    port: 5001,
    zone: 'Zone A',
    status: 'HEALTHY',
    storageDir: 'storage/node1/',
    totalBytes: 10737418240,
    usedBytes: 3887010611,
    used: '3.62 GB',
    total: '10.0 GB',
    percent: 36.2,
    objectsCount: 248,
    replicaCount: 742,
    lastHeartbeat: '0.8s ago',
    pingMs: 1.8,
    uptime: '14d 6h 22m',
    partitioned: false,
    corrupted: false,
  },
  {
    id: 2,
    name: 'node-02',
    daemon: 'node-02',
    port: 5002,
    zone: 'Zone A',
    status: 'HEALTHY',
    storageDir: 'storage/node2/',
    totalBytes: 10737418240,
    usedBytes: 4090899005,
    used: '3.81 GB',
    total: '10.0 GB',
    percent: 38.1,
    objectsCount: 260,
    replicaCount: 780,
    lastHeartbeat: '1.1s ago',
    pingMs: 1.9,
    uptime: '14d 6h 22m',
    partitioned: false,
    corrupted: false,
  },
  {
    id: 3,
    name: 'node-03',
    daemon: 'node-03',
    port: 5003,
    zone: 'Zone A',
    status: 'HEALTHY',
    storageDir: 'storage/node3/',
    totalBytes: 10737418240,
    usedBytes: 3747348480,
    used: '3.49 GB',
    total: '10.0 GB',
    percent: 34.9,
    objectsCount: 238,
    replicaCount: 715,
    lastHeartbeat: '1.2s ago',
    pingMs: 2.1,
    uptime: '14d 6h 22m',
    partitioned: false,
    corrupted: false,
  },
  {
    id: 4,
    name: 'node-04',
    daemon: 'node-04',
    port: 5004,
    zone: 'Zone B',
    status: 'HEALTHY',
    storageDir: 'storage/node4/',
    totalBytes: 10737418240,
    usedBytes: 3972844748,
    used: '3.70 GB',
    total: '10.0 GB',
    percent: 37.0,
    objectsCount: 252,
    replicaCount: 758,
    lastHeartbeat: '0.9s ago',
    pingMs: 2.1,
    uptime: '14d 6h 22m',
    partitioned: false,
    corrupted: false,
  },
  {
    id: 5,
    name: 'node-05',
    daemon: 'node-05',
    port: 5005,
    zone: 'Zone B',
    status: 'HEALTHY',
    storageDir: 'storage/node5/',
    totalBytes: 10737418240,
    usedBytes: 4209067622,
    used: '3.92 GB',
    total: '10.0 GB',
    percent: 39.2,
    objectsCount: 268,
    replicaCount: 802,
    lastHeartbeat: '1.0s ago',
    pingMs: 1.7,
    uptime: '14d 6h 22m',
    partitioned: false,
    corrupted: false,
  },
  {
    id: 6,
    name: 'node-06',
    daemon: 'node-06',
    port: 5006,
    zone: 'Zone B',
    status: 'HEALTHY',
    storageDir: 'storage/node6/',
    totalBytes: 10737418240,
    usedBytes: 3768824627,
    used: '3.51 GB',
    total: '10.0 GB',
    percent: 35.1,
    objectsCount: 240,
    replicaCount: 720,
    lastHeartbeat: '1.4s ago',
    pingMs: 2.3,
    uptime: '14d 6h 22m',
    partitioned: false,
    corrupted: false,
  },
];

let devRepairs = [
  {
    id: 'rep-9812',
    trigger: 'NODE_FAILURE',
    object: 'postgres_daily_dump.sql.gz',
    sourceNode: 'node-02',
    targetNode: 'node-04',
    bytesRestored: '4.0 MB',
    duration: '412 ms',
    durationMs: 412,
    status: 'COMPLETED',
    timestamp: '14 mins ago',
  },
  {
    id: 'rep-9811',
    trigger: 'CORRUPTION_DETECTED',
    object: 'q3_sales_aggregate.parquet',
    sourceNode: 'node-01',
    targetNode: 'node-05',
    bytesRestored: '4.0 MB',
    duration: '388 ms',
    durationMs: 388,
    status: 'COMPLETED',
    timestamp: '32 mins ago',
  },
  {
    id: 'rep-9810',
    trigger: 'REBALANCE',
    object: 'flight_sensor_stream.parquet',
    sourceNode: 'node-05',
    targetNode: 'node-03',
    bytesRestored: '4.0 MB',
    duration: '512 ms',
    durationMs: 512,
    status: 'COMPLETED',
    timestamp: '1 hour ago',
  },
  {
    id: 'rep-9809',
    trigger: 'NODE_FAILURE',
    object: 'security_access_logs_2026_q3.csv',
    sourceNode: 'node-03',
    targetNode: 'node-06',
    bytesRestored: '4.0 MB',
    duration: '440 ms',
    durationMs: 440,
    status: 'COMPLETED',
    timestamp: '2 hours ago',
  },
];

let devLiveEvents = [
  { id: 108, timestamp: new Date(Date.now() - 60000).toLocaleTimeString(), severity: 'SUCCESS', category: 'REPAIR', node: 'node-04', message: 'OBJECT_RESTORED: database/postgres_daily_dump.sql.gz (3 replicas healthy)' },
  { id: 107, timestamp: new Date(Date.now() - 70000).toLocaleTimeString(), severity: 'SUCCESS', category: 'INTEGRITY', node: 'node-04', message: 'CHECKSUM_VERIFIED: SHA-256 e3b0c44298fc... matched stored catalog metadata' },
  { id: 106, timestamp: new Date(Date.now() - 75000).toLocaleTimeString(), severity: 'INFO', category: 'REPAIR', node: 'node-02', message: 'REPLICA_COPIED: Chunk #14 (4.0 MB) streamed from node-02 to node-04 via internal data plane' },
  { id: 105, timestamp: new Date(Date.now() - 85000).toLocaleTimeString(), severity: 'INFO', category: 'REPAIR', node: 'Control Plane', message: 'REPAIR_STARTED: Repair job created targeting node-04 in Zone B' },
  { id: 104, timestamp: new Date(Date.now() - 95000).toLocaleTimeString(), severity: 'WARN', category: 'STORAGE', node: 'Control Plane', message: 'OBJECT_DEGRADED: database/postgres_daily_dump.sql.gz (2/3 replicas available)' },
  { id: 103, timestamp: new Date(Date.now() - 100000).toLocaleTimeString(), severity: 'ERROR', category: 'HEARTBEAT', node: 'node-03', message: 'NODE_FAILED: node-03 marked FAILED (Missed 3 consecutive heartbeat cycles on port 5003)' },
];

export const adminService = {
  getClusterSummary: async () => {
    try {
      try {
        return await api.get('/admin/cluster');
      } catch {
        return await api.get('/cluster/overview');
      }
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return { ...devClusterSummary };
      }
      throw err;
    }
  },

  listNodes: async () => {
    try {
      try {
        return await api.get('/admin/nodes');
      } catch {
        return await api.get('/nodes');
      }
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return [...devNodes];
      }
      throw err;
    }
  },

  getNodeDetails: async (nodeId) => {
    try {
      return await api.get(`/admin/nodes/${nodeId}`);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        const node = devNodes.find((n) => n.id === Number(nodeId));
        if (!node) throw new Error(`Node ${nodeId} not found`);
        return node;
      }
      throw err;
    }
  },

  getActiveRepairs: async () => {
    try {
      try {
        return await api.get('/cluster/repairs');
      } catch {
        return await api.get('/admin/repairs');
      }
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return [...devRepairs];
      }
      throw err;
    }
  },

  getRecentFailures: async () => {
    try {
      return await api.get('/admin/failures');
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        const failed = devNodes.filter((n) => n.status === 'FAILED' || n.status === 'DEGRADED');
        return failed.map((n) => ({
          node: n.name,
          port: n.port,
          zone: n.zone,
          type: n.partitioned ? 'NETWORK_PARTITION' : 'HEARTBEAT_TIMEOUT',
          time: 'Active Incident',
          recoveryStatus: 'Repair Queued',
        }));
      }
      throw err;
    }
  },

  getDurabilityOverview: async () => {
    try {
      return await api.get('/admin/durability');
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return [
          {
            name: 'Replication Factor 3 (RF=3)',
            overhead: '3.0× (300%)',
            concept: 'Enterprise default. Survives 2 concurrent node failures across Zone A and Zone B.',
            objectsCount: 8,
            rawUsed: '19.8 GB',
            status: 'ACTIVE_DEFAULT',
          },
          {
            name: 'Replication Factor 2 (RF=2)',
            overhead: '2.0× (200%)',
            concept: 'Standard redundancy. Survives 1 node outage with cross-zone placement.',
            objectsCount: 2,
            rawUsed: '1.4 GB',
            status: 'AVAILABLE',
          },
        ];
      }
      throw err;
    }
  },

  getIntegrityOverview: async () => {
    try {
      return await api.get('/admin/integrity');
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return {
          objectsVerified: 1036,
          integrityFailures: 0,
          corruptReplicas: 0,
          replicasRepaired: devRepairs.length,
          lastScrub: '4 minutes ago',
          algorithm: 'SHA-256 Cryptographic Checksum',
        };
      }
      throw err;
    }
  },

  getLiveEvents: async (limit = 10) => {
    try {
      return await api.get(`/admin/events?limit=${limit}`);
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return devLiveEvents.slice(0, limit);
      }
      throw err;
    }
  },

  getMetrics: async () => {
    try {
      try {
        return await api.get('/admin/metrics');
      } catch {
        return await api.get('/cluster/metrics');
      }
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        const healthy = devNodes.filter((n) => n.status === 'HEALTHY').length;
        const degraded = devNodes.filter((n) => n.status === 'DEGRADED').length;
        const failed = devNodes.filter((n) => n.status === 'FAILED').length;

        return {
          logicalStorage: '6.6 GB',
          physicalStorage: '19.8 GB',
          storageOverhead: '3.0×',
          availability: failed > 0 ? '99.98%' : '100%',
          completedRepairs: devRepairs.length,
          avgRepairDuration: '438 ms',
          avgRepairDurationMs: 438,
          repairedBytes: '72.0 MB',
          totalNodes: 6,
          healthyNodes: healthy,
          degradedNodes: degraded,
          failedNodes: failed,
          clusterUtilization: 35.3,
        };
      }
      throw err;
    }
  },

  /**
   * Native browser SSE stream for events
   * Endpoint: /api/v1/events/stream
   */
  subscribeEvents: (onMessage, onError) => {
    eventListeners.add(onMessage);

    let eventSource = null;
    try {
      const sseUrl = `${api.origin}/api/v1/events/stream`;
      eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          onMessage(data);
        } catch {
          onMessage({
            id: Date.now(),
            message: e.data,
            timestamp: new Date().toLocaleTimeString(),
            severity: 'INFO',
          });
        }
      };

      eventSource.onerror = (err) => {
        if (onError) onError(err);
      };
    } catch (e) {
      if (onError) onError(e);
    }

    return () => {
      eventListeners.delete(onMessage);
      if (eventSource) {
        eventSource.close();
      }
    };
  },

  // -------------------------------------------------------------
  // SIMULATION HOOKS FOR THE KILLER DEMO & STANDALONE EVALUATION
  // -------------------------------------------------------------

  simulateKillNode: (nodeId) => {
    const node = devNodes.find((n) => n.id === nodeId);
    if (node) {
      node.status = 'FAILED';
      localStorage.setItem('nexvault_cluster_has_failure', 'true');

      devClusterSummary.health = 'DEGRADED';
      devClusterSummary.healthPercent = 83.33;
      devClusterSummary.healthyNodes = devNodes.filter((n) => n.status === 'HEALTHY').length;
      devClusterSummary.failedNodes = devNodes.filter((n) => n.status === 'FAILED').length;
      devClusterSummary.degradedObjects = 1;

      const eventTime = new Date().toLocaleTimeString();
      const failEvent = {
        id: Date.now(),
        timestamp: eventTime,
        severity: 'ERROR',
        category: 'HEARTBEAT',
        node: node.name,
        message: `NODE_FAILED: ${node.name} on port ${node.port} unreachable. Missed 3 consecutive heartbeat cycles.`,
      };
      const degEvent = {
        id: Date.now() + 1,
        timestamp: eventTime,
        severity: 'WARN',
        category: 'STORAGE',
        node: 'Control Plane',
        message: `OBJECT_DEGRADED: Object postgres_daily_dump.sql.gz under-replicated (2/3 healthy replicas).`,
      };

      devLiveEvents.unshift(failEvent, degEvent);
      dispatchClusterEvent(failEvent);
      dispatchClusterEvent(degEvent);

      // Trigger killer demo auto-repair sequence after 4.5s
      setTimeout(() => {
        adminService.simulateEmergencyRepair();
      }, 4500);
    }
    return { success: true, message: `Node 0${nodeId} marked FAILED.` };
  },

  simulateRestoreNode: (nodeId) => {
    const node = devNodes.find((n) => n.id === nodeId);
    if (node) {
      node.status = 'HEALTHY';
      node.partitioned = false;
      node.corrupted = false;
      devClusterSummary.healthyNodes = devNodes.filter((n) => n.status === 'HEALTHY').length;
      devClusterSummary.failedNodes = devNodes.filter((n) => n.status === 'FAILED').length;

      if (devClusterSummary.failedNodes === 0) {
        devClusterSummary.health = 'HEALTHY';
        devClusterSummary.healthPercent = 100.0;
        localStorage.removeItem('nexvault_cluster_has_failure');
      }

      const evt = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        severity: 'SUCCESS',
        category: 'HEARTBEAT',
        node: node.name,
        message: `NODE_RESTORED: ${node.name} reconnected on port ${node.port}. Health checks passing.`,
      };
      devLiveEvents.unshift(evt);
      dispatchClusterEvent(evt);
    }
    return { success: true, message: `Node 0${nodeId} restored.` };
  },

  simulatePartitionNode: (nodeId, isolated) => {
    const node = devNodes.find((n) => n.id === nodeId);
    if (node) {
      node.partitioned = isolated;
      node.status = isolated ? 'DEGRADED' : 'HEALTHY';
      const evt = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        severity: isolated ? 'WARN' : 'SUCCESS',
        category: 'NETWORK',
        node: node.name,
        message: isolated
          ? `NETWORK_PARTITION: ${node.name} isolated from inter-node communication.`
          : `PARTITION_HEALED: ${node.name} network connectivity restored.`,
      };
      devLiveEvents.unshift(evt);
      dispatchClusterEvent(evt);
    }
    return { success: true, message: `Node 0${nodeId} partition state updated.` };
  },

  simulateCorruptReplica: (nodeId, chunkId) => {
    const node = devNodes.find((n) => n.id === nodeId);
    if (node) {
      node.corrupted = true;
      const evt = {
        id: Date.now(),
        timestamp: new Date().toLocaleTimeString(),
        severity: 'ERROR',
        category: 'INTEGRITY',
        node: node.name,
        message: `BIT_ROT_DETECTED: Checksum mismatch on ${node.name} for ${chunkId}. Stored SHA-256 does not match calculated.`,
      };
      devLiveEvents.unshift(evt);
      dispatchClusterEvent(evt);
    }
    return { success: true, message: `Bit rot injected on Node 0${nodeId}.` };
  },

  simulateTriggerScrub: () => {
    const evt = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString(),
      severity: 'INFO',
      category: 'INTEGRITY',
      node: 'Control Plane',
      message: 'CHECKSUM_VERIFIED: Full cluster cryptographic scrub finished across all 6 storage nodes. 0 corrupted blocks.',
    };
    devLiveEvents.unshift(evt);
    dispatchClusterEvent(evt);
    return { success: true, message: 'Cluster scrub completed successfully.' };
  },

  simulateEmergencyRepair: () => {
    const time = new Date().toLocaleTimeString();
    const repairEvt1 = {
      id: Date.now(),
      timestamp: time,
      severity: 'INFO',
      category: 'REPAIR',
      node: 'Control Plane',
      message: 'REPAIR_STARTED: Rebuilding missing replica for postgres_daily_dump.sql.gz',
    };
    const repairEvt2 = {
      id: Date.now() + 1,
      timestamp: time,
      severity: 'INFO',
      category: 'REPAIR',
      node: 'node-02',
      message: 'REPLICA_COPIED: Streamed chunk replica from node-02 (Zone A) to node-04 (Zone B)',
    };
    const repairEvt3 = {
      id: Date.now() + 2,
      timestamp: time,
      severity: 'SUCCESS',
      category: 'INTEGRITY',
      node: 'node-04',
      message: 'CHECKSUM_VERIFIED: SHA-256 match confirmed on target node',
    };
    const repairEvt4 = {
      id: Date.now() + 3,
      timestamp: time,
      severity: 'SUCCESS',
      category: 'REPAIR',
      node: 'Control Plane',
      message: 'REPAIR_COMPLETED: OBJECT_RESTORED (3/3 replicas healthy)',
    };

    devLiveEvents.unshift(repairEvt4, repairEvt3, repairEvt2, repairEvt1);
    dispatchClusterEvent(repairEvt1);
    setTimeout(() => dispatchClusterEvent(repairEvt2), 300);
    setTimeout(() => dispatchClusterEvent(repairEvt3), 600);
    setTimeout(() => {
      dispatchClusterEvent(repairEvt4);
      devClusterSummary.health = 'HEALTHY';
      devClusterSummary.healthPercent = 100.0;
      devClusterSummary.degradedObjects = 0;
      devClusterSummary.completedRepairs += 1;
      localStorage.removeItem('nexvault_cluster_has_failure');
    }, 900);

    const newRepair = {
      id: 'rep-' + Math.floor(1000 + Math.random() * 9000),
      trigger: 'AUTONOMOUS_HEAL',
      object: 'postgres_daily_dump.sql.gz',
      sourceNode: 'node-02',
      targetNode: 'node-04',
      bytesRestored: '4.0 MB',
      duration: '412 ms',
      durationMs: 412,
      status: 'COMPLETED',
      timestamp: 'Just now',
    };
    devRepairs.unshift(newRepair);

    return { success: true, message: 'Emergency repair completed. Invariants verified.' };
  },

  simulateRebalance: () => {
    const evt = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString(),
      severity: 'INFO',
      category: 'REBALANCE',
      node: 'Control Plane',
      message: 'REBALANCE_COMPLETED: Cross-zone replica distribution symmetric. Skew < 2%.',
    };
    devLiveEvents.unshift(evt);
    dispatchClusterEvent(evt);
    return { success: true, message: 'Rebalance executed successfully.' };
  },

  simulateResetCluster: () => {
    devNodes.forEach((n) => {
      n.status = 'HEALTHY';
      n.partitioned = false;
      n.corrupted = false;
    });

    devClusterSummary.health = 'HEALTHY';
    devClusterSummary.healthPercent = 100.0;
    devClusterSummary.healthyNodes = 6;
    devClusterSummary.failedNodes = 0;
    devClusterSummary.degradedNodes = 0;
    devClusterSummary.degradedObjects = 0;
    devClusterSummary.availabilitySLA = '100%';
    localStorage.removeItem('nexvault_cluster_has_failure');

    const evt = {
      id: Date.now(),
      timestamp: new Date().toLocaleTimeString(),
      severity: 'SUCCESS',
      category: 'CLUSTER',
      node: 'Control Plane',
      message: 'DEMO_RESET: Cluster returned to baseline. All 6 nodes healthy, 3/3 replicas verified.',
    };
    devLiveEvents.unshift(evt);
    dispatchClusterEvent(evt);

    return { success: true, message: 'Cluster reset to pristine healthy state.' };
  },
};

export default adminService;
