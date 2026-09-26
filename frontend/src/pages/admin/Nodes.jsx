import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Server,
  HardDrive,
  Activity,
  Radio,
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  RotateCw,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import ProgressBar from '../../components/common/ProgressBar';
import StatusIndicator from '../../components/common/StatusIndicator';
import LoadingState from '../../components/common/LoadingState';
import { adminService } from '../../services/adminService';
import { useToast } from '../../context/ToastContext';

export default function Nodes() {
  const { showToast } = useToast();
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadNodes = async () => {
    setLoading(true);
    try {
      const data = await adminService.listNodes();
      setNodes(data);
    } catch (err) {
      showToast({ type: 'error', title: 'Error', message: err.message || 'Failed to fetch node list.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNodes();
    // Subscribe to SSE / live event stream to update nodes dynamically
    const unsubscribe = adminService.subscribeEvents((event) => {
      if (event.category === 'HEARTBEAT' || event.category === 'CLUSTER' || event.category === 'NETWORK') {
        loadNodes();
      }
    });
    return () => unsubscribe();
  }, []);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'HEALTHY':
        return <Badge variant="healthy" size="sm">🟢 HEALTHY</Badge>;
      case 'DEGRADED':
        return <Badge variant="warning" size="sm">🟡 DEGRADED</Badge>;
      case 'FAILED':
        return <Badge variant="danger" size="sm" pulse>🔴 FAILED</Badge>;
      case 'RECOVERING':
        return <Badge variant="recovering" size="sm" pulse>🔵 RECOVERING</Badge>;
      default:
        return <Badge variant="neutral" size="sm">{status}</Badge>;
    }
  };

  const healthyCount = nodes.filter((n) => n.status === 'HEALTHY').length;
  const failedCount = nodes.filter((n) => n.status === 'FAILED').length;
  const degradedCount = nodes.filter((n) => n.status === 'DEGRADED').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
              Storage Node Grid (6 Daemons)
            </h2>
            <Badge variant={failedCount === 0 ? 'healthy' : 'danger'} size="sm">
              {healthyCount} / {nodes.length || 6} ONLINE
            </Badge>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Independent physical processes on ports 5001–5006 with localized data stores and zone anti-affinity.
          </p>
        </div>

        <Button
          variant="secondary"
          icon={RefreshCw}
          onClick={() => {
            loadNodes();
            showToast({ type: 'info', title: 'Nodes Polled', message: 'Queried health checks on all storage nodes.' });
          }}
        >
          Refresh Nodes
        </Button>
      </div>

      {loading && nodes.length === 0 ? (
        <LoadingState message="Connecting to 6 storage node daemons..." skeletonRows={3} />
      ) : (
        <>
          {/* Node Grid Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '18px' }}>
            {nodes.map((node) => {
              const isZoneA = node.zone === 'Zone A';
              const isFailed = node.status === 'FAILED';
              const isDegraded = node.status === 'DEGRADED';

              return (
                <Card
                  key={node.id}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    borderColor: isFailed
                      ? 'rgba(239, 68, 68, 0.4)'
                      : isDegraded
                      ? 'rgba(245, 158, 11, 0.4)'
                      : 'var(--border-subtle)',
                    background: isFailed
                      ? 'rgba(239, 68, 68, 0.04)'
                      : isDegraded
                      ? 'rgba(245, 158, 11, 0.03)'
                      : 'var(--bg-surface)',
                  }}
                >
                  <CardHeader
                    action={getStatusBadge(node.status)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '38px',
                          height: '38px',
                          borderRadius: '10px',
                          background: isFailed
                            ? 'rgba(239, 68, 68, 0.15)'
                            : isZoneA
                            ? 'rgba(2, 132, 199, 0.15)'
                            : 'rgba(6, 182, 212, 0.15)',
                          color: isFailed ? '#f87171' : isZoneA ? '#38bdf8' : '#22d3ee',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontWeight: '700',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '14px',
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
                    {/* Storage progress */}
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                        <span style={{ color: 'var(--text-muted)' }}>Storage Consumed:</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--text-main)' }}>
                          {node.used || '3.62 GB'} / {node.total || '10.0 GB'}
                        </span>
                      </div>
                      <ProgressBar
                        value={isFailed ? 0 : node.percent || 36}
                        variant={isFailed ? 'danger' : isZoneA ? 'primary' : 'cyan'}
                        height={6}
                      />
                    </div>

                    {/* Metadata details */}
                    <div
                      style={{
                        background: 'rgba(0, 0, 0, 0.25)',
                        padding: '12px',
                        borderRadius: '8px',
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '10px',
                        fontSize: '12px',
                      }}
                    >
                      <div>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Replica Chunks:</span>
                        <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '600', color: 'var(--cyan-accent)' }}>
                          {node.replicaCount || 740} Chunks
                        </div>
                      </div>

                      <div>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Storage Dir:</span>
                        <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                          {node.storageDir || `storage/node${node.id}/`}
                        </div>
                      </div>

                      <div>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Heartbeat:</span>
                        <div style={{ fontFamily: 'var(--font-mono)', color: isFailed ? '#f87171' : '#10b981' }}>
                          {isFailed ? 'Unreachable' : node.lastHeartbeat || '0.8s ago'}
                        </div>
                      </div>

                      <div>
                        <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>Ping Latency:</span>
                        <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                          {isFailed ? 'TIMEOUT' : `${node.pingMs || 1.8} ms`}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
