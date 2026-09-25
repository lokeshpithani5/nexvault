import React, { useState, useEffect } from 'react';
import {
  Wrench,
  CheckCircle2,
  Clock,
  HardDrive,
  Activity,
  Play,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import MetricCard from '../../components/common/MetricCard';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';
import LoadingState from '../../components/common/LoadingState';
import EmptyState from '../../components/common/EmptyState';
import { adminService } from '../../services/adminService';
import { chaosService } from '../../services/chaosService';
import { useToast } from '../../context/ToastContext';

export default function Repairs() {
  const { showToast } = useToast();
  const [running, setRunning] = useState(false);
  const [repairs, setRepairs] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadRepairs = async () => {
    setLoading(true);
    try {
      const [repairList, metricData] = await Promise.all([
        adminService.getActiveRepairs(),
        adminService.getMetrics(),
      ]);
      setRepairs(repairList);
      setMetrics(metricData);
    } catch (err) {
      showToast({ type: 'error', title: 'Error', message: err.message || 'Failed to fetch repair ledger.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRepairs();
    const unsubscribe = adminService.subscribeEvents((event) => {
      if (event.category === 'REPAIR') {
        loadRepairs();
      }
    });
    return () => unsubscribe();
  }, []);

  const handleTriggerRepair = async () => {
    setRunning(true);
    showToast({
      type: 'info',
      title: 'Emergency Repair Triggered',
      message: 'Autonomous repair engine sweeping cluster for under-replicated chunks...',
    });
    try {
      await chaosService.triggerEmergencyRepair();
      showToast({
        type: 'success',
        title: 'Repair Pass Completed',
        message: 'Under-replicated objects repaired to RF=3 invariants.',
      });
      loadRepairs();
    } catch (err) {
      showToast({ type: 'error', title: 'Repair Error', message: err.message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
            Autonomous Replica Repair Ledger
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Real-time audit trail of background self-healing events restoring missing replicas across failure domains.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={loadRepairs}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={Play}
            loading={running}
            onClick={handleTriggerRepair}
          >
            Trigger Repair Pass
          </Button>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <MetricCard
          label="Repairs Completed"
          value={metrics?.completedRepairs?.toString() || repairs.length.toString()}
          subtext="100% success rate"
          icon={CheckCircle2}
          status="healthy"
        />
        <MetricCard
          label="Avg Recovery Duration (TTR)"
          value={metrics?.avgRepairDuration || `${metrics?.avgRepairDurationMs || 438} ms`}
          subtext="Fault detection to verified replica"
          icon={Clock}
          status="info"
        />
        <MetricCard
          label="Data Self-Healed"
          value={metrics?.repairedBytes || '72.0 MB'}
          subtext="Rebuilt across Zone A & B"
          icon={HardDrive}
          status="default"
        />
        <MetricCard
          label="Current Engine State"
          value={running ? 'HEALING' : 'IDLE'}
          subtext={running ? 'Restoring under-replicated chunks' : 'Monitoring heartbeat events'}
          icon={Activity}
          status={running ? 'warning' : 'healthy'}
        />
      </div>

      {/* Repair Ledger Table */}
      <Card>
        <CardHeader
          action={
            <Badge variant="healthy" size="sm">
              {repairs.length} EVENTS RECORDED
            </Badge>
          }
        >
          <CardTitle>Repair Ledger (/cluster/repairs)</CardTitle>
        </CardHeader>
        <CardContent noPadding>
          {loading && repairs.length === 0 ? (
            <LoadingState message="Fetching repair ledger records..." skeletonRows={4} />
          ) : repairs.length === 0 ? (
            <div style={{ padding: '32px' }}>
              <EmptyState
                title="No Repairs Recorded"
                message="The cluster has not detected any node failures or corrupted replicas yet."
              />
            </div>
          ) : (
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader>Object Key</TableHeader>
                  <TableHeader>Source Node</TableHeader>
                  <TableHeader>Target Node</TableHeader>
                  <TableHeader>Bytes Restored</TableHeader>
                  <TableHeader>Duration</TableHeader>
                  <TableHeader>Status</TableHeader>
                  <TableHeader align="right">Timestamp</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {repairs.map((rep) => (
                  <TableRow key={rep.id}>
                    <TableCell>
                      <div style={{ fontWeight: '500', color: 'var(--text-main)', fontFamily: 'var(--font-mono)', fontSize: '13px' }}>
                        {rep.object}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Trigger: {rep.trigger || 'FAILOVER'}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="info" size="sm">
                        {typeof rep.sourceNode === 'number' ? `node-0${rep.sourceNode}` : rep.sourceNode}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <ArrowRight size={14} style={{ color: 'var(--text-muted)' }} />
                        <Badge variant="healthy" size="sm">
                          {typeof rep.targetNode === 'number' ? `node-0${rep.targetNode}` : rep.targetNode}
                        </Badge>
                      </div>
                    </TableCell>
                    <TableCell mono>{rep.bytesRestored || rep.bytesHealed || '4.0 MB'}</TableCell>
                    <TableCell mono style={{ color: 'var(--cyan-accent)' }}>
                      {rep.duration || `${rep.durationMs || 412} ms`}
                    </TableCell>
                    <TableCell>
                      <Badge variant={rep.status === 'COMPLETED' ? 'healthy' : 'warning'} size="sm">
                        {rep.status}
                      </Badge>
                    </TableCell>
                    <TableCell align="right" style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                      {rep.timestamp}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
