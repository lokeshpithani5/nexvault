import React from 'react';
import {
  Layers,
  ShieldCheck,
  Scale,
  Cpu,
  CheckCircle2,
  Info,
  Server,
  Zap,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import Button from '../../components/common/Button';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';

export default function Replication() {
  const policies = [
    {
      name: 'Replication Factor 3 (RF=3)',
      type: 'Full Mirroring',
      faultTolerance: 'Survives 2 Node Failures',
      overhead: '3.0x (300%)',
      readQuorum: 'R = 1 (Fast read from nearest node)',
      writeQuorum: 'W = 2 (Majority ack required)',
      placement: 'Cross-zone: Min 1 replica in Zone A, Min 1 in Zone B',
      status: 'ACTIVE_DEFAULT',
    },
    {
      name: 'Replication Factor 2 (RF=2)',
      type: 'Zone Pair',
      faultTolerance: 'Survives 1 Node Failure',
      overhead: '2.0x (200%)',
      readQuorum: 'R = 1',
      writeQuorum: 'W = 2 (Strict consensus across both)',
      placement: '1 Node in Zone A + 1 Node in Zone B',
      status: 'AVAILABLE',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
          Replication & Durability Policies
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
          Mathematical durability constraints, cross-zone placement matrices, and quorum consensus parameters.
        </p>
      </div>

      {/* Policies Overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
        {policies.map((pol, i) => (
          <Card key={i} elevated>
            <CardHeader
              action={
                <Badge variant={pol.status === 'ACTIVE_DEFAULT' ? 'healthy' : 'neutral'} size="sm">
                  {pol.status}
                </Badge>
              }
            >
              <CardTitle>{pol.name}</CardTitle>
            </CardHeader>
            <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                <strong>Fault Tolerance:</strong> <span style={{ color: '#10b981', fontWeight: '600' }}>{pol.faultTolerance}</span>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                <strong>Storage Overhead:</strong> <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)' }}>{pol.overhead}</span>
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                <strong>Consensus Quorums:</strong>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', background: 'rgba(0,0,0,0.25)', padding: '6px 10px', borderRadius: '6px', marginTop: '4px' }}>
                  {pol.readQuorum}
                  <br />
                  {pol.writeQuorum}
                </div>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)', paddingTop: '10px' }}>
                {pol.placement}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Cross-Zone Placement Anti-Affinity Rules */}
      <Card>
        <CardHeader>
          <CardTitle>Lightweight Failure Domains (Zone Anti-Affinity)</CardTitle>
        </CardHeader>
        <CardContent>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div style={{ padding: '16px', background: 'rgba(2, 132, 199, 0.05)', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Server size={18} style={{ color: 'var(--primary-light)' }} />
                <h4 style={{ fontSize: '14px', fontWeight: '600', color: 'var(--primary-light)' }}>Zone A (Rack 1)</h4>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                Nodes: <strong>Node 1 (5001), Node 2 (5002), Node 3 (5003)</strong>
                <br />
                The coordinator guarantees that writes are never committed strictly to Zone A. At least one replica or parity shard must reside in Zone B to prevent catastrophic correlated failure.
              </p>
            </div>

            <div style={{ padding: '16px', background: 'rgba(6, 182, 212, 0.05)', borderRadius: '8px', border: '1px solid rgba(6, 182, 212, 0.2)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Server size={18} style={{ color: 'var(--cyan-accent)' }} />
                <h4 style={{ fontSize: '14px', fontWeight: '600', color: 'var(--cyan-accent)' }}>Zone B (Rack 2)</h4>
              </div>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                Nodes: <strong>Node 4 (5004), Node 5 (5005), Node 6 (5006)</strong>
                <br />
                Replicas in Zone B provide geographical/electrical isolation. If all 3 nodes in Zone A undergo power loss or maintenance, Zone B nodes continue serving read requests.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
