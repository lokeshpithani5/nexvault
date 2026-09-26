import React from 'react';
import {
  Wrench,
  Activity,
  Server,
  Layers,
  Clock,
  HardDrive,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ShieldCheck,
  Binary,
} from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Badge from '../common/Badge';
import ProgressBar from '../common/ProgressBar';

export default function RepairDetailsModal({ isOpen, onClose, repair }) {
  if (!repair) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#f59e0b',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Wrench size={18} />
          </div>
          <div>
            <span style={{ fontSize: '17px', fontWeight: '600' }}>Active Autonomous Repair Job</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px', fontFamily: 'var(--font-mono)' }}>
              [{repair.id}]
            </span>
          </div>
        </div>
      }
      description="Self-healing engine restoring replica consistency following node outage."
      size="md"
      footer={
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close
        </Button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {/* Progress & Status Card */}
        <div
          style={{
            padding: '16px',
            borderRadius: '10px',
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-glow)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)' }}>
              Reconstruction Progress
            </span>
            <Badge variant="warning" size="sm" pulse>
              {repair.status}
            </Badge>
          </div>

          <ProgressBar
            value={repair.progress}
            variant="gradient"
            height={10}
            showPercentage
            label={`${repair.bytesRecovered} self-healed`}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-muted)' }}>
            <span>Elapsed Time: <strong style={{ color: 'var(--cyan-accent)', fontFamily: 'var(--font-mono)' }}>{repair.elapsedTime}</strong></span>
            <span>Policy: <strong style={{ color: 'var(--text-main)' }}>{repair.policy}</strong></span>
          </div>
        </div>

        {/* Source -> Target Nodes Flow */}
        <div
          style={{
            padding: '16px',
            borderRadius: '10px',
            background: 'rgba(0, 0, 0, 0.25)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-around',
          }}
        >
          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Failed Node</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', fontSize: '14px', color: '#ef4444', marginTop: '2px' }}>
              {repair.failedNodeName}
            </div>
            <span style={{ fontSize: '10px', color: '#ef4444' }}>Outage Detected</span>
          </div>

          <ArrowRight size={20} style={{ color: 'var(--text-muted)' }} />

          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Source Replica</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', fontSize: '14px', color: '#38bdf8', marginTop: '2px' }}>
              {repair.sourceNodeName}
            </div>
            <span style={{ fontSize: '10px', color: '#38bdf8' }}>Streaming Chunks</span>
          </div>

          <ArrowRight size={20} style={{ color: 'var(--text-muted)' }} />

          <div style={{ textAlign: 'center' }}>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Target Node</span>
            <div style={{ fontFamily: 'var(--font-mono)', fontWeight: '700', fontSize: '14px', color: '#10b981', marginTop: '2px' }}>
              {repair.targetNodeName}
            </div>
            <span style={{ fontSize: '10px', color: '#10b981' }}>Writing & Verifying</span>
          </div>
        </div>

        {/* Affected Object & Expected Checksum */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Under-replicated Object</span>
            <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)', marginTop: '2px', wordBreak: 'break-all', fontFamily: 'var(--font-mono)' }}>
              {repair.objectKey}
            </div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Target Checksum Verification (SHA-256)</span>
            <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)', marginTop: '4px', wordBreak: 'break-all', background: 'rgba(0,0,0,0.4)', padding: '6px 8px', borderRadius: '4px' }}>
              {repair.checksumExpected}
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
}
