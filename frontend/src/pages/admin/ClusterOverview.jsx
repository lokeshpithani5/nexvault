import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Server,
  Activity,
  HardDrive,
  ShieldCheck,
  ShieldAlert,
  Flame,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Layers,
  ArrowRight,
  Clock,
  Radio,
  ExternalLink,
  Cpu,
  Binary,
  FileCode,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import MetricCard from '../../components/common/MetricCard';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import ProgressBar from '../../components/common/ProgressBar';
import StatusIndicator from '../../components/common/StatusIndicator';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';
import LoadingState from '../../components/common/LoadingState';
import ErrorState from '../../components/common/ErrorState';
import NodeDetailsModal from '../../components/admin/NodeDetailsModal';
import RepairDetailsModal from '../../components/admin/RepairDetailsModal';
import ObjectDetailsModal from '../../components/storage/ObjectDetailsModal';
import { adminService } from '../../services/adminService';
import { storageService, formatBytes } from '../../services/storageService';
import { useToast } from '../../context/ToastContext';

export default function ClusterOverview() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Cluster State from Admin Service Adapter
  const [clusterSummary, setClusterSummary] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [topologyRelationships, setTopologyRelationships] = useState([]);
  const [activeRepairs, setActiveRepairs] = useState([]);
  const [recentFailures, setRecentFailures] = useState([]);
  const [durabilityPolicies, setDurabilityPolicies] = useState([]);
  const [integrityOverview, setIntegrityOverview] = useState(null);
  const [liveEvents, setLiveEvents] = useState([]);

  // Modals
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedRepair, setSelectedRepair] = useState(null);
  const [selectedObjectForDetails, setSelectedObjectForDetails] = useState(null);

  const loadClusterData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        summary,
        nodeList,
        relationships,
        repairs,
        failures,
        durability,
        integrity,
        events,
      ] = await Promise.all([
        adminService.getClusterSummary(),
        adminService.listNodes(),
        adminService.getTopologyRelationships(),
        adminService.getActiveRepairs(),
        adminService.getRecentFailures(),
        adminService.getDurabilityOverview(),
        adminService.getIntegrityOverview(),
        adminService.getLiveEvents(8),
      ]);

      setClusterSummary(summary);
      setNodes(nodeList);
      setTopologyRelationships(relationships);
      setActiveRepairs(repairs);
      setRecentFailures(failures);
      setDurabilityPolicies(durability);
      setIntegrityOverview(integrity);
      setLiveEvents(events);
    } catch (err) {
      setError(err);
      showToast({ type: 'error', title: 'Cluster Sync Error', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClusterData();
  }, []);

  const handleOpenDegradedObject = async (objectKey) => {
    try {
      const allObjects = await storageService.listObjects();
      const matched = allObjects.find((o) => o.key === objectKey || o.name === objectKey);
      if (matched) {
        setSelectedObjectForDetails(matched);
      } else {
        showToast({ type: 'info', title: 'Inspecting Object', message: `Fetching metadata for '${objectKey}'...` });
      }
    } catch {
      // ignore
    }
  };

  const zoneA = nodes.filter((n) => n.zone === 'Zone A');
  const zoneB = nodes.filter((n) => n.zone === 'Zone B');

  if (loading && !clusterSummary) {
    return <LoadingState message="Connecting to NEXVAULT Control Plane & polling storage nodes..." skeletonRows={6} />;
  }

  if (error && !clusterSummary) {
    return (
      <ErrorState
        title="Cluster Telemetry Unavailable"
        message={error.message || 'Unable to establish connection with NEXVAULT Control Plane.'}
        onRetry={loadClusterData}
      />
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 1. TOP BANNER & CHAOS LAB ENTRY */}
      <div
        className="glass-panel"
        style={{
          padding: '24px 28px',
          background: 'radial-gradient(ellipse at 80% 20%, rgba(14, 165, 233, 0.15) 0%, transparent 60%), linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, rgba(13, 20, 36, 0.9) 100%)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderColor: 'var(--border-glow)',
          boxShadow: 'var(--shadow-lg)',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ffffff',
                boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)',
              }}
            >
              <Server size={20} />
            </div>
            <h1 style={{ fontSize: '22px', fontWeight: '700', fontFamily: 'var(--font-display)', color: '#ffffff' }}>
              Cluster Topology & Distributed Control Plane
            </h1>
            <Badge variant="healthy" size="sm" pulse>
              CONTROL PLANE ACTIVE
            </Badge>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '720px' }}>
            Multi-node distributed object storage partitioned across independent physical daemons (Ports 5001–5006) and isolated failure zones (Zone A & Zone B).
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Button
            variant="secondary"
            icon={RotateCw}
            onClick={() => {
              loadClusterData();
              showToast({ type: 'info', title: 'Telemetry Synced', message: 'Refreshed node heartbeats and repair states.' });
            }}
          >
            Poll Nodes
          </Button>

          {/* OPEN CHAOS LAB ENTRY */}
          <Button
            variant="danger"
            size="md"
            icon={Flame}
            onClick={() => navigate('/admin/chaos')}
            style={{
              boxShadow: '0 0 18px rgba(239, 68, 68, 0.35)',
              border: '1px solid rgba(239, 68, 68, 0.5)',
            }}
          >
            OPEN CHAOS LAB
          </Button>
        </div>
      </div>

      {/* 2. HIGH-IMPACT CLUSTER HEALTH HEADER (SECTION 10 METRICS) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: '14px' }}>
        <MetricCard
          label="Cluster Health"
          value={clusterSummary?.health || (clusterSummary?.failedNodes > 0 ? 'DEGRADED' : 'HEALTHY')}
          subtext={clusterSummary?.failedNodes > 0 ? `${clusterSummary.failedNodes} Node Outage` : 'All invariants satisfied'}
          icon={Activity}
          status={clusterSummary?.health === 'DEGRADED' || clusterSummary?.failedNodes > 0 ? 'danger' : 'healthy'}
          trend={{ direction: 'up', value: 'Active' }}
        />
        <MetricCard
          label="Nodes"
          value={`${clusterSummary?.healthyNodes ?? 6} / ${clusterSummary?.totalNodes ?? 6} Healthy`}
          subtext="Zone A (3) & Zone B (3)"
          icon={Server}
          status={(clusterSummary?.healthyNodes ?? 6) === 6 ? 'healthy' : 'warning'}
        />
        <MetricCard
          label="Availability"
          value={clusterSummary?.availabilitySLA || '100%'}
          subtext="Read/Write Quorum Intact"
          icon={ShieldCheck}
          status="healthy"
        />
        <MetricCard
          label="Storage Overhead"
          value={clusterSummary?.storageOverhead || '3.0×'}
          subtext="RF=3 (300% Raw/Logical)"
          icon={Layers}
          status="info"
        />
        <MetricCard
          label="Repairs"
          value={`${clusterSummary?.completedRepairs ?? 18} Completed`}
          subtext="Self-healing engine active"
          icon={Wrench}
          status="healthy"
        />
        <MetricCard
          label="Objects"
          value={`${clusterSummary?.objectsCount ?? 8} Objects`}
          subtext="100% Quorum verified"
          icon={CheckCircle2}
          status="default"
        />
        <MetricCard
          label="Storage"
          value={`${clusterSummary?.logicalStorage || '6.6 GB'} / ${clusterSummary?.physicalStorage || '19.8 GB'}`}
          subtext="Logical vs Physical Raw"
          icon={HardDrive}
          status="default"
        />
      </div>

      {/* 3. CLUSTER TOPOLOGY: 6 INDEPENDENT NODES ACROSS ZONE A & ZONE B */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div>
            <h3 style={{ fontSize: '17px', fontWeight: '600', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
              Independent Storage Nodes & Failure Domains
            </h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              6 independent daemons running on localhost ports 5001–5006 with isolated directories. Click any node for detailed metrics.
            </span>
          </div>
          <Badge variant="info" size="sm">
            Zone Anti-Affinity Enabled
          </Badge>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          {/* ZONE A */}
          <Card elevated style={{ borderColor: 'rgba(56, 189, 248, 0.2)' }}>
            <CardHeader
              action={
                <Badge variant="info" size="sm">
                  Zone A (Ports 5001–5003)
                </Badge>
              }
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Server size={18} style={{ color: 'var(--primary-light)' }} />
                <CardTitle>FAILURE DOMAIN A</CardTitle>
              </div>
            </CardHeader>
            <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {zoneA.map((node) => (
                <div
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className="glass-panel"
                  style={{
                    padding: '16px',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    backgroundColor: 'var(--bg-surface-elevated)',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--primary-light)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '8px',
                          background: 'rgba(2, 132, 199, 0.2)',
                          color: '#38bdf8',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: '700',
                          fontSize: '13px',
                        }}
                      >
                        0{node.id}
                      </div>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text-main)' }}>
                          {node.name}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          Port {node.port} • {node.storageDir}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--cyan-accent)' }}>
                        {node.pingMs} ms
                      </span>
                      <StatusIndicator status={node.status} size="sm" />
                    </div>
                  </div>

                  {/* Utilization Bar */}
                  <ProgressBar
                    value={node.percent}
                    variant="primary"
                    height={6}
                    showPercentage
                    label={`${formatBytes(node.usedBytes)} / ${formatBytes(node.totalBytes)} (${node.objectsCount} objects • ${node.replicaCount} replicas)`}
                  />

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                    <span>Heartbeat: {node.lastHeartbeat}</span>
                    <span style={{ color: 'var(--primary-light)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '2px' }}>
                      Inspect Node <ExternalLink size={11} />
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* ZONE B */}
          <Card elevated style={{ borderColor: 'rgba(6, 182, 212, 0.2)' }}>
            <CardHeader
              action={
                <Badge variant="recovering" size="sm">
                  Zone B (Ports 5004–5006)
                </Badge>
              }
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Server size={18} style={{ color: 'var(--cyan-accent)' }} />
                <CardTitle>FAILURE DOMAIN B</CardTitle>
              </div>
            </CardHeader>
            <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {zoneB.map((node) => (
                <div
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className="glass-panel"
                  style={{
                    padding: '16px',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                    backgroundColor: 'var(--bg-surface-elevated)',
                    transition: 'all 0.2s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--cyan-accent)')}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '8px',
                          background: 'rgba(6, 182, 212, 0.2)',
                          color: '#22d3ee',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontFamily: 'var(--font-mono)',
                          fontWeight: '700',
                          fontSize: '13px',
                        }}
                      >
                        0{node.id}
                      </div>
                      <div>
                        <div style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text-main)' }}>
                          {node.name}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          Port {node.port} • {node.storageDir}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--cyan-accent)' }}>
                        {node.pingMs} ms
                      </span>
                      <StatusIndicator status={node.status} size="sm" />
                    </div>
                  </div>

                  {/* Utilization Bar */}
                  <ProgressBar
                    value={node.percent}
                    variant="cyan"
                    height={6}
                    showPercentage
                    label={`${formatBytes(node.usedBytes)} / ${formatBytes(node.totalBytes)} (${node.objectsCount} objects • ${node.replicaCount} replicas)`}
                  />

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                    <span>Heartbeat: {node.lastHeartbeat}</span>
                    <span style={{ color: 'var(--cyan-accent)', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '2px' }}>
                      Inspect Node <ExternalLink size={11} />
                    </span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 4. TOPOLOGY CONNECTIONS: VISUAL CROSS-ZONE REPLICA RELATIONSHIPS */}
      <Card>
        <CardHeader
          action={
            <Badge variant="healthy" size="sm">
              Cross-Zone Distribution Verified
            </Badge>
          }
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Layers size={18} style={{ color: 'var(--primary-light)' }} />
            <CardTitle>Topology Connections: Object ➔ Replica Placement Matrix</CardTitle>
          </div>
        </CardHeader>
        <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {topologyRelationships.map((item, idx) => (
            <div
              key={idx}
              style={{
                padding: '16px',
                borderRadius: '10px',
                background: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileCode size={18} style={{ color: 'var(--cyan-accent)' }} />
                  <div>
                    <span
                      onClick={() => handleOpenDegradedObject(item.objectName)}
                      style={{
                        fontWeight: '600',
                        fontSize: '13px',
                        color: 'var(--text-main)',
                        fontFamily: 'var(--font-mono)',
                        cursor: 'pointer',
                        textDecoration: 'underline',
                      }}
                      title="Inspect Object Details"
                    >
                      {item.objectName}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                      in [{item.bucket}]
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <Badge variant={item.policy === 'ERASURE_CODING_4_2' ? 'recovering' : 'info'} size="sm">
                    {item.policy}
                  </Badge>
                  <StatusIndicator status={item.status} size="sm" />
                </div>
              </div>

              {/* Replica Node Connector Pins */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', minWidth: '60px' }}>
                  Replicas:
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  {item.replicas.map((r, rIdx) => (
                    <div
                      key={rIdx}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '6px',
                        padding: '4px 10px',
                        borderRadius: '6px',
                        background: r.status === 'RECOVERING' ? 'rgba(245, 158, 11, 0.15)' : (r.zone === 'Zone A' ? 'rgba(2, 132, 199, 0.15)' : 'rgba(6, 182, 212, 0.15)'),
                        border: `1px solid ${r.status === 'RECOVERING' ? 'rgba(245, 158, 11, 0.4)' : (r.zone === 'Zone A' ? 'rgba(56, 189, 248, 0.3)' : 'rgba(34, 211, 238, 0.3)')}`,
                      }}
                    >
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', fontWeight: '700', color: r.zone === 'Zone A' ? '#38bdf8' : '#22d3ee' }}>
                        N{r.nodeId}
                      </span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        ({r.zone})
                      </span>
                      <StatusIndicator status={r.status} size="sm" showDot />
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontStyle: 'italic', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
                {item.note}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* 5. STORAGE CAPACITY OVERVIEW & ACTIVE SELF-HEALING REPAIRS */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Storage Capacity Overview */}
        <Card elevated>
          <CardHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <HardDrive size={18} style={{ color: 'var(--primary-light)' }} />
              <CardTitle>Cluster Physical Storage Capacity</CardTitle>
            </div>
          </CardHeader>
          <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div>
                <span style={{ fontSize: '28px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
                  {formatBytes(clusterSummary?.usedCapacityBytes || 0)}
                </span>
                <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginLeft: '6px' }}>
                  used of {formatBytes(clusterSummary?.totalCapacityBytes || 0)}
                </span>
              </div>
              <span style={{ fontSize: '16px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)' }}>
                {clusterSummary?.utilizationPercent}%
              </span>
            </div>

            <ProgressBar
              value={clusterSummary?.utilizationPercent || 35.3}
              variant="gradient"
              height={10}
              showPercentage
            />

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              <div style={{ padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Total Raw</span>
                <div style={{ fontSize: '14px', fontWeight: '600', fontFamily: 'var(--font-mono)', marginTop: '2px' }}>
                  {formatBytes(clusterSummary?.totalCapacityBytes || 0)}
                </div>
              </div>

              <div style={{ padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Available</span>
                <div style={{ fontSize: '14px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: '#10b981', marginTop: '2px' }}>
                  {formatBytes(clusterSummary?.availableCapacityBytes || 0)}
                </div>
              </div>

              <div style={{ padding: '10px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Overhead Ratio</span>
                <div style={{ fontSize: '14px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)', marginTop: '2px' }}>
                  2.8x Avg
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Active Self-Healing Repairs */}
        <Card elevated>
          <CardHeader
            action={
              <Badge variant="warning" size="sm" pulse>
                1 ACTIVE JOB
              </Badge>
            }
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wrench size={18} style={{ color: '#f59e0b' }} />
              <CardTitle>Autonomous Self-Healing Engine</CardTitle>
            </div>
          </CardHeader>
          <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {activeRepairs.map((repair) => (
              <div
                key={repair.id}
                onClick={() => setSelectedRepair(repair)}
                className="glass-panel"
                style={{
                  padding: '16px',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  backgroundColor: 'var(--bg-surface-elevated)',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                      {repair.object}
                    </span>
                    <div style={{ fontSize: '11px', color: '#f87171', marginTop: '2px' }}>
                      {repair.failedNodeName} Outage Detected ➔ Rebuilding on {repair.targetNodeName}
                    </div>
                  </div>
                  <Badge variant="warning" size="sm">
                    {repair.status}
                  </Badge>
                </div>

                <ProgressBar
                  value={repair.progress}
                  variant="warning"
                  height={8}
                  showPercentage
                  label={`Source: ${repair.sourceNodeName} ➔ Target: ${repair.targetNodeName}`}
                />

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
                  <span>Recovered: <strong style={{ color: 'var(--text-main)' }}>{repair.bytesRecovered}</strong></span>
                  <span>TTR: <strong style={{ color: 'var(--cyan-accent)', fontFamily: 'var(--font-mono)' }}>{repair.elapsedTime}</strong></span>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* 6. RECENT INCIDENTS & FAILURES */}
      <Card>
        <CardHeader>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={18} style={{ color: 'var(--text-muted)' }} />
            <CardTitle>Recent Node Incidents & Self-Healing Telemetry</CardTitle>
          </div>
        </CardHeader>
        <CardContent noPadding>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Timestamp</TableHeader>
                <TableHeader>Affected Node</TableHeader>
                <TableHeader>Failure Type</TableHeader>
                <TableHeader>Affected Objects</TableHeader>
                <TableHeader>Autonomous Response</TableHeader>
                <TableHeader>Recovery Duration (TTR)</TableHeader>
                <TableHeader>Status</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {recentFailures.map((fail) => (
                <TableRow key={fail.id}>
                  <TableCell mono style={{ color: 'var(--text-muted)' }}>{fail.timestamp}</TableCell>
                  <TableCell>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{ fontWeight: '600', color: 'var(--text-main)' }}>{fail.node}</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>({fail.zone})</span>
                    </div>
                  </TableCell>
                  <TableCell style={{ color: '#f87171', fontWeight: '500' }}>{fail.failure}</TableCell>
                  <TableCell mono>{fail.affectedObjects} objects</TableCell>
                  <TableCell>{fail.repairStatus}</TableCell>
                  <TableCell mono style={{ color: 'var(--cyan-accent)' }}>{fail.recoveryTime}</TableCell>
                  <TableCell>
                    <Badge variant={fail.status === 'COMPLETED' ? 'healthy' : 'warning'} size="sm">
                      {fail.status}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* 7. DURABILITY POLICIES & INTEGRITY OVERVIEW */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* Durability Policies */}
        <Card>
          <CardHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} style={{ color: 'var(--primary-light)' }} />
              <CardTitle>Durability Policies & Overhead Ratios</CardTitle>
            </div>
          </CardHeader>
          <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {durabilityPolicies.map((pol, idx) => (
              <div
                key={idx}
                style={{
                  padding: '12px 14px',
                  borderRadius: '8px',
                  background: 'var(--bg-surface-elevated)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-main)' }}>{pol.name}</span>
                    <Badge variant="neutral" size="sm">{pol.overhead}</Badge>
                  </div>
                  <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px', maxWidth: '520px' }}>
                    {pol.concept}
                  </p>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--cyan-accent)', fontFamily: 'var(--font-mono)' }}>
                    {pol.objectsCount} objects
                  </span>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {pol.rawUsed} raw
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Cryptographic Integrity (SHA-256) */}
        <Card>
          <CardHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Binary size={18} style={{ color: '#10b981' }} />
              <CardTitle>SHA-256 Integrity</CardTitle>
            </div>
          </CardHeader>
          <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Objects Verified:</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: '#10b981' }}>
                {integrityOverview?.objectsVerified || 1036}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Bit-Rot / Corruptions:</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: integrityOverview?.corruptReplicas === 0 ? '#10b981' : '#ef4444' }}>
                {integrityOverview?.corruptReplicas || 0}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Replicas Repaired:</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--cyan-accent)' }}>
                {integrityOverview?.replicasRepaired || 18}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Last Cluster Scrub:</span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {integrityOverview?.lastScrub || 'Recent'}
              </span>
            </div>

            <div style={{ padding: '8px 10px', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.2)', fontSize: '11px', color: '#10b981', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={14} />
              <span>Catalog Checksum = Computed Disk SHA-256</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 8. COMPACT LIVE EVENT STREAM */}
      <Card>
        <CardHeader
          action={
            <Button variant="ghost" size="sm" onClick={() => navigate('/admin/events')}>
              Open Full Stream
            </Button>
          }
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Radio size={18} style={{ color: 'var(--primary-light)' }} />
            <CardTitle>Live Control Plane Event Stream</CardTitle>
          </div>
        </CardHeader>
        <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {liveEvents.map((evt) => (
            <div
              key={evt.id}
              style={{
                padding: '8px 12px',
                borderRadius: '6px',
                background: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                fontSize: '12px',
                fontFamily: 'var(--font-mono)',
              }}
            >
              <span style={{ color: 'var(--text-muted)', fontSize: '11px', flexShrink: 0 }}>
                {evt.timestamp}
              </span>

              <span
                style={{
                  color:
                    evt.severity === 'SUCCESS'
                      ? '#10b981'
                      : evt.severity === 'WARN'
                      ? '#f59e0b'
                      : evt.severity === 'ERROR'
                      ? '#ef4444'
                      : '#38bdf8',
                  fontWeight: '700',
                  flexShrink: 0,
                  width: '20px',
                  textAlign: 'center',
                }}
              >
                {evt.icon}
              </span>

              <span style={{ color: 'var(--text-main)', fontFamily: 'var(--font-sans)', fontSize: '12px' }}>
                {evt.message}
              </span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Modals for Interactive Inspection */}
      <NodeDetailsModal
        isOpen={!!selectedNode}
        onClose={() => setSelectedNode(null)}
        node={selectedNode}
      />

      <RepairDetailsModal
        isOpen={!!selectedRepair}
        onClose={() => setSelectedRepair(null)}
        repair={selectedRepair}
      />

      <ObjectDetailsModal
        isOpen={!!selectedObjectForDetails}
        onClose={() => setSelectedObjectForDetails(null)}
        object={selectedObjectForDetails}
      />
    </div>
  );
}
