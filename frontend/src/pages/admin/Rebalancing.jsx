import React, { useState } from 'react';
import {
  Scale,
  Activity,
  Layers,
  HardDrive,
  Play,
  RotateCw,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import MetricCard from '../../components/common/MetricCard';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import ProgressBar from '../../components/common/ProgressBar';
import { useToast } from '../../context/ToastContext';

export default function Rebalancing() {
  const { showToast } = useToast();
  const [rebalancing, setRebalancing] = useState(false);
  const [threshold, setThreshold] = useState(15); // 15% imbalance threshold

  const nodeLoads = [
    { id: 1, name: 'Node 01', zone: 'Zone A', used: '3.62 GB', percent: 36.2 },
    { id: 2, name: 'Node 02', zone: 'Zone A', used: '3.81 GB', percent: 38.1 },
    { id: 3, name: 'Node 03', zone: 'Zone A', used: '3.49 GB', percent: 34.9 },
    { id: 4, name: 'Node 04', zone: 'Zone B', used: '3.70 GB', percent: 37.0 },
    { id: 5, name: 'Node 05', zone: 'Zone B', used: '3.92 GB', percent: 39.2 },
    { id: 6, name: 'Node 06', zone: 'Zone B', used: '3.51 GB', percent: 35.1 },
  ];

  const handleRunRebalance = () => {
    setRebalancing(true);
    showToast({
      type: 'info',
      title: 'Rebalance Engine Triggered',
      message: 'Evaluating capacity skew across nodes against threshold...',
    });
    setTimeout(() => {
      setRebalancing(false);
      showToast({
        type: 'success',
        title: 'Cluster Optimal',
        message: 'Current capacity delta is 4.3% (below the 15% threshold). No unnecessary data moves performed.',
      });
    }, 1800);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
            Cluster Storage Rebalancer
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Prevents hot-spotting by migrating chunk replicas when capacity distribution exceeds imbalance thresholds.
          </p>
        </div>

        <Button
          variant="primary"
          icon={Play}
          loading={rebalancing}
          onClick={handleRunRebalance}
        >
          Evaluate & Run Rebalance
        </Button>
      </div>

      {/* Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <MetricCard
          label="Current Max Skew"
          value="4.3%"
          subtext="Highest node: 39.2% • Lowest: 34.9%"
          icon={Scale}
          status="healthy"
        />
        <MetricCard
          label="Imbalance Threshold"
          value={`${threshold}%`}
          subtext="Rebalance triggers only when skew > threshold"
          icon={Activity}
          status="info"
        />
        <MetricCard
          label="Zone Balance (A vs B)"
          value="49.8% / 50.2%"
          subtext="Near-perfect cross-zone symmetry"
          icon={Layers}
          status="healthy"
        />
        <MetricCard
          label="Rebalance Mode"
          value="THROTTLED"
          subtext="Preserves client IO bandwidth"
          icon={HardDrive}
          status="default"
        />
      </div>

      {/* Node Utilization Distribution Bars */}
      <Card>
        <CardHeader>
          <CardTitle>Storage Utilization per Node</CardTitle>
        </CardHeader>
        <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {nodeLoads.map((n) => (
            <div key={n.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                <span style={{ fontWeight: '600' }}>
                  {n.name} <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>({n.zone})</span>
                </span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)' }}>
                  {n.used} / 10 GB ({n.percent}%)
                </span>
              </div>
              <ProgressBar
                value={n.percent}
                variant={n.zone === 'Zone A' ? 'primary' : 'cyan'}
                height={8}
              />
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
