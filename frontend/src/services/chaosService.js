import api from './api';
import adminService from './adminService';

export const chaosService = {
  killNode: async (nodeId) => {
    try {
      return await api.post(`/chaos/kill-node/${nodeId}`, {});
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateKillNode(Number(nodeId));
      }
      throw err;
    }
  },

  restoreNode: async (nodeId) => {
    try {
      return await api.post(`/chaos/restore-node/${nodeId}`, {});
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateRestoreNode(Number(nodeId));
      }
      throw err;
    }
  },

  partitionNode: async (nodeId, isolated = true) => {
    try {
      return await api.post(`/chaos/partition-node/${nodeId}`, { isolated });
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulatePartitionNode(Number(nodeId), isolated);
      }
      throw err;
    }
  },

  healPartition: async (nodeId) => {
    try {
      return await api.post(`/chaos/heal-partition/${nodeId}`, {});
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulatePartitionNode(Number(nodeId), false);
      }
      throw err;
    }
  },

  corruptReplica: async (nodeId, chunkId = 'chunk-001') => {
    try {
      return await api.post('/chaos/corrupt-replica', { node_id: Number(nodeId), chunk_id: chunkId });
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateCorruptReplica(Number(nodeId), chunkId);
      }
      throw err;
    }
  },

  triggerClusterScrub: async () => {
    try {
      return await api.post('/chaos/trigger-scrub', {});
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateTriggerScrub();
      }
      throw err;
    }
  },

  triggerEmergencyRepair: async () => {
    try {
      return await api.post('/chaos/trigger-repair', {});
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateEmergencyRepair();
      }
      throw err;
    }
  },

  triggerRebalance: async () => {
    try {
      return await api.post('/chaos/rebalance', {});
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateRebalance();
      }
      throw err;
    }
  },

  resetCluster: async () => {
    try {
      // Tries demo reset or chaos reset
      try {
        return await api.post('/demo/reset', {});
      } catch {
        return await api.post('/chaos/reset', {});
      }
    } catch (err) {
      if (err.isNetworkError && api.isDevFallbackEnabled()) {
        return adminService.simulateResetCluster();
      }
      throw err;
    }
  },
};

export default chaosService;
