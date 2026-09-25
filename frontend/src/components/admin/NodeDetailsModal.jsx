import React from 'react';
import {
  Server,
  Cpu,
  HardDrive,
  Activity,
  Layers,
  Clock,
  Radio,
  Folder,
  CheckCircle2,
  AlertTriangle,
  X,
} from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Badge from '../common/Badge';
import ProgressBar from '../common/ProgressBar';
import StatusIndicator from '../common/StatusIndicator';
import { formatBytes } from '../../services/storageService';

export default function NodeDetailsModal({ isOpen, onClose, node }) {
  if (!node) return null;

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
              background: node.zone === 'Zone A' ? 'rgba(2, 132, 199, 0.2)' : 'rgba(6, 182, 212, 0.2)',
              color: node.zone === 'Zone A' ? '#38bdf8' : '#22d3ee',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '700',
              fontFamily: 'var(--font-mono)',
            }}
          >
            0{node.id}
          </div>
          <div>
            <span style={{ fontSize: '17px', fontWeight: '600' }}>{node.name}</span>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
              ({node.daemon} • 127.0.0.1:{node.port})
            </span>
          </div>
        </div>
      }
      description={`Independent storage daemon process • ${node.zone} failure domain`}
      size="md"
      footer={
        <Button variant="secondary" size="sm" onClick={onClose}>
          Close
        </Button>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {/* Status & Uptime Header Card */}
        <div
          style={{
            padding: '14px 16px',
            borderRadius: '10px',
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Operational State:</span>
            <div style={{ marginTop: '2px' }}>
              <StatusIndicator status={node.status} size="md" />
            </div>
          </div>

          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Ping Latency:</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', color: 'var(--cyan-accent)', fontWeight: '600' }}>
              {node.pingMs} ms
            </span>
          </div>

          <div>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block' }}>Process Uptime:</span>
            <span style={{ fontSize: '12px', color: 'var(--text-main)', fontWeight: '500' }}>
              {node.uptime || 'Active'}
            </span>
          </div>
        </div>

        {/* Disk Capacity Bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
            <span style={{ color: 'var(--text-secondary)' }}>Physical Disk Utilization</span>
            <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
              {formatBytes(node.usedBytes)} / {formatBytes(node.totalBytes)} ({node.percent}%)
            </span>
          </div>
          <ProgressBar
            value={node.percent}
            variant={node.zone === 'Zone A' ? 'primary' : 'cyan'}
            height={8}
          />
        </div>

        {/* Data Grid: Objects, Replicas, Storage Directory */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Objects Stored</span>
            <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-main)', marginTop: '2px' }}>
              {node.objectsCount}
            </div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Chunk Replicas</span>
            <div style={{ fontSize: '16px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)', marginTop: '2px' }}>
              {node.replicaCount}
            </div>
          </div>

          <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Failure Zone</span>
            <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)', marginTop: '4px' }}>
              <Badge variant={node.zone === 'Zone A' ? 'info' : 'recovering'} size="sm">
                {node.zone}
              </Badge>
            </div>
          </div>
        </div>

        {/* Storage Directory Path */}
        <div style={{ padding: '10px 14px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Folder size={16} style={{ color: 'var(--text-muted)' }} />
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Local Storage Path:</span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--primary-light)' }}>
            {node.storageDir}
          </span>
        </div>

        {/* Recent Node Activity */}
        <div>
          <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-main)', display: 'block', marginBottom: '8px' }}>
            Recent Node Events & Heartbeats
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {node.recentEvents?.map((evt, idx) => (
              <div
                key={idx}
                style={{
                  padding: '8px 12px',
                  borderRadius: '6px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid var(--border-subtle)',
                  fontSize: '11px',
                  display: 'flex',
                  gap: '10px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>{evt.time}</span>
                <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-sans)' }}>{evt.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  );
}
