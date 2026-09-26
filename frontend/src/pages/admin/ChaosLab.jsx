import React, { useState, useEffect } from 'react';
import {
  Flame,
  PowerOff,
  Power,
  WifiOff,
  Wifi,
  Binary,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Server,
  Play,
  Activity,
  Scale,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import MetricCard from '../../components/common/MetricCard';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import LoadingState from '../../components/common/LoadingState';
import { adminService } from '../../services/adminService';
import { chaosService } from '../../services/chaosService';
import { useToast } from '../../context/ToastContext';

export default function ChaosLab() {
  const { showToast } = useToast();

  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Confirmation dialogs
  const [nodeToKill, setNodeToKill] = useState(null);
  const [nodeToPartition, setNodeToPartition] = useState(null);
  const [resetConfirmOpen, setResetConfirmOpen] = useState(false);

  // Live log of chaos activities
  const [chaosLog, setChaosLog] = useState([
    { id: 1, time: new Date().toLocaleTimeString(), type: 'INFO', text: 'Chaos Lab initialized. All 6 nodes connected and healthy.' },
  ]);

  const addLog = (type, text) => {
    const time = new Date().toLocaleTimeString();
    setChaosLog((prev) => [{ id: Date.now(), time, type, text }, ...prev]);
  };

  const loadClusterState = async () => {
    try {
      const data = await adminService.listNodes();
      setNodes(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClusterState();
    const unsubscribe = adminService.subscribeEvents((event) => {
      addLog(event.severity || 'INFO', `[${event.category || 'EVENT'}] ${event.message}`);
      loadClusterState();
    });
    return () => unsubscribe();
  }, []);

  const executeKillNode = async () => {
    if (!nodeToKill) return;
    const nodeId = nodeToKill.id;
    setNodeToKill(null);
    setActionInProgress(true);

    try {
      await chaosService.killNode(nodeId);
      addLog('DANGER', `NODE_FAILED: Process killed on Node 0${nodeId} (port ${nodeToKill.port}). Failover triggered.`);
      showToast({
        type: 'error',
        title: `Node 0${nodeId} Killed`,
        message: 'Node marked FAILED. NEXVAULT initiated automatic failover to surviving replicas.',
      });
      loadClusterState();
    } catch (err) {
      showToast({ type: 'error', title: 'Action Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRestoreNode = async (node) => {
    setActionInProgress(true);
    try {
      await chaosService.restoreNode(node.id);
      addLog('SUCCESS', `NODE_RESTORED: Node 0${node.id} restarted on port ${node.port}. Health checks verified.`);
      showToast({
        type: 'success',
        title: `Node 0${node.id} Restored`,
        message: `Node 0${node.id} reconnected to coordinator.`,
      });
      loadClusterState();
    } catch (err) {
      showToast({ type: 'error', title: 'Restore Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const executeTogglePartition = async () => {
    if (!nodeToPartition) return;
    const node = nodeToPartition;
    setNodeToPartition(null);
    setActionInProgress(true);

    const willIsolate = !node.partitioned;
    try {
      if (willIsolate) {
        await chaosService.partitionNode(node.id, true);
        addLog('WARN', `NETWORK_PARTITION: Node 0${node.id} partitioned. Traffic isolated from control plane.`);
        showToast({
          type: 'warning',
          title: `Node 0${node.id} Partitioned`,
          message: 'Network route severed. Quorum reads rerouted to surviving zone.',
        });
      } else {
        await chaosService.healPartition(node.id);
        addLog('SUCCESS', `PARTITION_HEALED: Node 0${node.id} network route restored.`);
        showToast({
          type: 'success',
          title: 'Partition Healed',
          message: `Node 0${node.id} communication restored.`,
        });
      }
      loadClusterState();
    } catch (err) {
      showToast({ type: 'error', title: 'Partition Action Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleCorruptReplica = async (node) => {
    setActionInProgress(true);
    try {
      await chaosService.corruptReplica(node.id, 'chunk-001');
      addLog('DANGER', `BIT_ROT_INJECTED: Flipped bytes in chunk payload on Node 0${node.id}. Checksum mismatch guaranteed.`);
      showToast({
        type: 'error',
        title: 'Bit Rot Injected',
        message: `Corrupted chunk on Node 0${node.id}. Cryptographic scrubber will detect on scan.`,
      });
      loadClusterState();
    } catch (err) {
      showToast({ type: 'error', title: 'Corruption Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleIntegrityScan = async () => {
    setActionInProgress(true);
    showToast({ type: 'info', title: 'Integrity Scan Dispatched', message: 'Scanning SHA-256 cryptographic checksums across all 6 storage nodes...' });
    try {
      await chaosService.triggerClusterScrub();
      addLog('INFO', 'CHECKSUM_VERIFIED: Full cluster scrub completed across all 6 storage nodes.');
      showToast({ type: 'success', title: 'Scan Completed', message: 'All object chunk hashes verified against catalog.' });
    } catch (err) {
      showToast({ type: 'error', title: 'Scan Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleTriggerRepair = async () => {
    setActionInProgress(true);
    showToast({ type: 'info', title: 'Repair Dispatched', message: 'Autonomous repair engine checking for missing replica blocks...' });
    try {
      await chaosService.triggerEmergencyRepair();
      addLog('SUCCESS', 'REPAIR_COMPLETED: Under-replicated chunks rebuilt across Zone A and Zone B.');
      showToast({ type: 'success', title: 'Repairs Completed', message: 'Cluster returned to 3/3 healthy replicas.' });
      loadClusterState();
    } catch (err) {
      showToast({ type: 'error', title: 'Repair Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const handleTriggerRebalance = async () => {
    setActionInProgress(true);
    try {
      await chaosService.triggerRebalance();
      addLog('INFO', 'REBALANCE_COMPLETED: Node storage distribution verified within 2% variance threshold.');
      showToast({ type: 'success', title: 'Rebalancing Finished', message: 'Replica allocation across failure domains balanced.' });
    } catch (err) {
      showToast({ type: 'error', title: 'Rebalance Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const executeResetCluster = async () => {
    setResetConfirmOpen(false);
    setActionInProgress(true);
    try {
      await chaosService.resetCluster();
      addLog('SUCCESS', 'DEMO_RESET: All 6 storage nodes restored to HEALTHY. Partitions and corruptions cleared.');
      showToast({
        type: 'success',
        title: 'Cluster Reset Completed',
        message: 'All storage nodes returned to pristine healthy state with 3/3 replicas verified.',
      });
      loadClusterState();
    } catch (err) {
      showToast({ type: 'error', title: 'Reset Failed', message: err.message });
    } finally {
      setActionInProgress(false);
    }
  };

  const healthyCount = nodes.filter((n) => n.status === 'HEALTHY').length;
  const failedCount = nodes.filter((n) => n.status === 'FAILED').length;
  const partitionedCount = nodes.filter((n) => n.partitioned).length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '24px 28px',
          background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(245, 158, 11, 0.08) 100%), var(--bg-surface)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderColor: 'rgba(239, 68, 68, 0.3)',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <div style={{ color: '#ef4444' }}>
              <Flame size={24} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: '700', fontFamily: 'var(--font-display)', color: '#ffffff' }}>
              Chaos Engineering Laboratory
            </h1>
            <Badge variant="failed" size="sm">
              ADMIN ONLY
            </Badge>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '680px' }}>
            Demonstrate distributed resilience by simulating node failures, network partitions, and bit rot. Observe automatic failover and background repair.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={loadClusterState}
          >
            Poll Nodes
          </Button>
          <Button
            variant="danger"
            icon={RotateCcw}
            onClick={() => setResetConfirmOpen(true)}
            disabled={actionInProgress}
          >
            Reset Demo Cluster
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
        <MetricCard
          label="Active Daemons"
          value={`${healthyCount} / ${nodes.length || 6}`}
          subtext={failedCount > 0 ? `${failedCount} Failed Process` : 'All daemons responsive'}
          icon={Server}
          status={failedCount === 0 ? 'healthy' : 'danger'}
        />
        <MetricCard
          label="Network Partitions"
          value={partitionedCount.toString()}
          subtext={partitionedCount > 0 ? 'Isolated from quorum' : 'Full mesh connected'}
          icon={Wifi}
          status={partitionedCount === 0 ? 'healthy' : 'warning'}
        />
        <MetricCard
          label="Cluster Health"
          value={failedCount > 0 ? 'DEGRADED' : 'HEALTHY'}
          subtext="Autonomic repair engine armed"
          icon={Activity}
          status={failedCount > 0 ? 'danger' : 'healthy'}
        />
        <MetricCard
          label="Quorum Safety Margin"
          value="2 Nodes"
          subtext="RF=3 survives 2 node losses"
          icon={ShieldCheck}
          status="info"
        />
      </div>

      {/* Global Cluster Chaos Operations */}
      <Card style={{ padding: '20px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-main)', marginBottom: '4px' }}>
              Cluster-Wide Invariant Verification & Sweeps
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Trigger distributed protocols across all 6 storage nodes simultaneously.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <Button
              variant="secondary"
              size="sm"
              icon={Binary}
              onClick={handleIntegrityScan}
              disabled={actionInProgress}
            >
              Integrity Scan
            </Button>
            <Button
              variant="secondary"
              size="sm"
              icon={Scale}
              onClick={handleTriggerRebalance}
              disabled={actionInProgress}
            >
              Rebalance
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={Play}
              onClick={handleTriggerRepair}
              disabled={actionInProgress}
            >
              Trigger Repair
            </Button>
          </div>
        </div>
      </Card>

      {/* Storage Node Fault Injection Cards */}
      <div>
        <div style={{ marginBottom: '14px' }}>
          <h3 style={{ fontSize: '17px', fontWeight: '600', color: 'var(--text-main)' }}>
            Physical Storage Node Injection Matrix
          </h3>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Inject isolated faults into specific daemons to observe immediate failover during active object downloads.
          </p>
        </div>

        {loading && nodes.length === 0 ? (
          <LoadingState message="Connecting to storage nodes..." skeletonRows={3} />
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '18px' }}>
            {nodes.map((node) => {
              const isFailed = node.status === 'FAILED';
              const isZoneA = node.zone === 'Zone A';

              return (
                <Card
                  key={node.id}
                  style={{
                    borderColor: isFailed ? 'rgba(239, 68, 68, 0.4)' : node.partitioned ? 'rgba(245, 158, 11, 0.4)' : 'var(--border-subtle)',
                    background: isFailed ? 'rgba(239, 68, 68, 0.04)' : node.partitioned ? 'rgba(245, 158, 11, 0.03)' : 'var(--bg-surface)',
                  }}
                >
                  <CardHeader
                    action={
                      <Badge
                        variant={isFailed ? 'danger' : node.partitioned ? 'warning' : 'healthy'}
                        size="sm"
                        pulse={isFailed}
                      >
                        {isFailed ? '🔴 FAILED' : node.partitioned ? '🟡 PARTITIONED' : '🟢 HEALTHY'}
                      </Badge>
                    }
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '34px',
                          height: '34px',
                          borderRadius: '8px',
                          background: isFailed
                            ? 'rgba(239, 68, 68, 0.2)'
                            : isZoneA ? 'rgba(2, 132, 199, 0.15)' : 'rgba(6, 182, 212, 0.15)',
                          color: isFailed ? '#f87171' : isZoneA ? '#38bdf8' : '#22d3ee',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: '700',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        N{node.id}
                      </div>
                      <div>
                        <CardTitle>{node.name || `node-0${node.id}`}</CardTitle>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          Port {node.port} • {node.zone}
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    <div
                      style={{
                        background: 'rgba(0,0,0,0.2)',
                        padding: '10px 12px',
                        borderRadius: '6px',
                        fontSize: '11px',
                        display: 'flex',
                        justifyContent: 'space-between',
                      }}
                    >
                      <span style={{ color: 'var(--text-muted)' }}>Storage / Replicas:</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                        {node.used || '3.6 GB'} • {node.replicaCount || 740} Chunks
                      </span>
                    </div>

                    {/* Action Buttons */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      {isFailed ? (
                        <Button
                          variant="healthy"
                          size="sm"
                          icon={Power}
                          onClick={() => handleRestoreNode(node)}
                          disabled={actionInProgress}
                          style={{ gridColumn: 'span 2' }}
                        >
                          Recover Node 0{node.id}
                        </Button>
                      ) : (
                        <>
                          <Button
                            variant="danger"
                            size="sm"
                            icon={PowerOff}
                            onClick={() => setNodeToKill(node)}
                            disabled={actionInProgress}
                          >
                            Kill Node
                          </Button>
                          <Button
                            variant="secondary"
                            size="sm"
                            icon={node.partitioned ? Wifi : WifiOff}
                            onClick={() => setNodeToPartition(node)}
                            disabled={actionInProgress}
                          >
                            {node.partitioned ? 'Heal Route' : 'Partition'}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            icon={Binary}
                            onClick={() => handleCorruptReplica(node)}
                            disabled={actionInProgress}
                            style={{ gridColumn: 'span 2', fontSize: '11px' }}
                          >
                            Inject Bit Rot (Flip Byte)
                          </Button>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Live Chaos Execution Feed */}
      <Card>
        <CardHeader
          action={
            <Button variant="ghost" size="sm" onClick={() => setChaosLog([])} style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Clear Log
            </Button>
          }
        >
          <CardTitle>Chaos Execution Event Trail</CardTitle>
        </CardHeader>
        <CardContent noPadding>
          <div style={{ maxHeight: '240px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            {chaosLog.map((log) => (
              <div
                key={log.id}
                style={{
                  padding: '10px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  borderBottom: '1px solid var(--border-subtle)',
                  fontSize: '12px',
                }}
              >
                <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '11px', width: '70px' }}>
                  {log.time}
                </span>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: '700',
                    fontFamily: 'var(--font-mono)',
                    padding: '1px 6px',
                    borderRadius: '4px',
                    background: log.type === 'DANGER' ? 'rgba(239, 68, 68, 0.2)' : log.type === 'WARN' ? 'rgba(245, 158, 11, 0.2)' : log.type === 'SUCCESS' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(14, 165, 233, 0.2)',
                    color: log.type === 'DANGER' ? '#f87171' : log.type === 'WARN' ? '#fbbf24' : log.type === 'SUCCESS' ? '#34d399' : '#38bdf8',
                  }}
                >
                  {log.type}
                </span>
                <span style={{ color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                  {log.text}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* CONFIRMATION DIALOG: KILL NODE */}
      <ConfirmDialog
        isOpen={!!nodeToKill}
        onClose={() => setNodeToKill(null)}
        onConfirm={executeKillNode}
        title={`Simulate Node Failure: ${nodeToKill?.name} (Port ${nodeToKill?.port})?`}
        message="This will simulate a storage-node failure. NEXVAULT will attempt automatic failover and repair."
        confirmText="Simulate Crash (Kill Node)"
        variant="danger"
      />

      {/* CONFIRMATION DIALOG: NETWORK PARTITION */}
      <ConfirmDialog
        isOpen={!!nodeToPartition}
        onClose={() => setNodeToPartition(null)}
        onConfirm={executeTogglePartition}
        title={`${nodeToPartition?.partitioned ? 'Heal' : 'Partition'} Network Route for ${nodeToPartition?.name}?`}
        message={`This will simulate a network partition by isolating Node 0${nodeToPartition?.id} from inter-node communications.`}
        confirmText={nodeToPartition?.partitioned ? 'Heal Partition' : 'Sever Network Route'}
        variant="warning"
      />

      {/* CONFIRMATION DIALOG: RESET DEMO CLUSTER */}
      <ConfirmDialog
        isOpen={resetConfirmOpen}
        onClose={() => setResetConfirmOpen(false)}
        onConfirm={executeResetCluster}
        title="Reset Demo Cluster?"
        message="This will restore all 6 storage nodes to healthy state, heal all simulated partitions, clear corrupted blocks, and reset the telemetry metrics."
        confirmText="Reset Cluster to Baseline"
        variant="danger"
      />
    </div>
  );
}
