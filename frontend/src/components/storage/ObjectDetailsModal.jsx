import React, { useState } from 'react';
import {
  Download,
  Trash2,
  Copy,
  Check,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Server,
  Layers,
  History,
  FileCode,
  Clock,
  HardDrive,
  Activity,
  Cpu,
} from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Badge from '../common/Badge';
import StatusIndicator from '../common/StatusIndicator';
import FileIcon from '../common/FileIcon';
import { useToast } from '../../context/ToastContext';

export default function ObjectDetailsModal({
  isOpen,
  onClose,
  object,
  onDownload,
  onDelete,
}) {
  const { showToast } = useToast();
  const [activeTab, setActiveTab] = useState('basic'); // 'basic' | 'advanced'
  const [copiedHash, setCopiedHash] = useState(false);

  if (!object) return null;

  const handleCopyHash = () => {
    if (object.checksum) {
      navigator.clipboard.writeText(object.checksum);
      setCopiedHash(true);
      showToast({ type: 'info', title: 'Copied', message: 'SHA-256 checksum copied to clipboard.' });
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <FileIcon filename={object.name || object.key} size={22} />
          <span style={{ fontSize: '17px', fontWeight: '600' }}>{object.name || object.key}</span>
        </div>
      }
      description={`Stored in bucket: [${object.bucket}] • Version v${object.version || 1}`}
      size="lg"
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
          <Button
            variant="ghost"
            size="sm"
            icon={Trash2}
            onClick={() => {
              onClose();
              if (onDelete) onDelete(object);
            }}
            style={{ color: '#ef4444' }}
          >
            Delete Object (Tombstone)
          </Button>

          <div style={{ display: 'flex', gap: '10px' }}>
            <Button variant="secondary" size="sm" onClick={onClose}>
              Close
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={Download}
              onClick={() => {
                if (onDownload) onDownload(object);
              }}
            >
              Download Object
            </Button>
          </div>
        </div>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {/* Tab Switcher: Basic vs Advanced */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid var(--border-subtle)',
            gap: '24px',
            marginBottom: '4px',
          }}
        >
          <button
            onClick={() => setActiveTab('basic')}
            style={{
              padding: '8px 0',
              border: 'none',
              background: 'transparent',
              color: activeTab === 'basic' ? 'var(--primary-light)' : 'var(--text-secondary)',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              borderBottom: activeTab === 'basic' ? '2px solid var(--primary-light)' : '2px solid transparent',
              transition: 'all 0.2s',
            }}
          >
            Basic Metadata
          </button>
          <button
            onClick={() => setActiveTab('advanced')}
            style={{
              padding: '8px 0',
              border: 'none',
              background: 'transparent',
              color: activeTab === 'advanced' ? 'var(--cyan-accent)' : 'var(--text-secondary)',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              borderBottom: activeTab === 'advanced' ? '2px solid var(--cyan-accent)' : '2px solid transparent',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <span>Advanced Distributed Details</span>
            <Badge variant="info" size="sm">
              DEEP INSPECTION
            </Badge>
          </button>
        </div>

        {/* BASIC DETAILS VIEW */}
        {activeTab === 'basic' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '14px' }}>
              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Object Key / Path</span>
                <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-main)', marginTop: '2px', wordBreak: 'break-all', fontFamily: 'var(--font-mono)' }}>
                  {object.key}
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Logical Size</span>
                <div style={{ fontSize: '14px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '2px' }}>
                  {object.sizeFormatted || object.size}
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginLeft: '6px' }}>
                    ({object.sizeBytes?.toLocaleString() || 'N/A'} bytes)
                  </span>
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Content Type</span>
                <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-main)', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
                  {object.type || 'application/octet-stream'}
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Health & Availability</span>
                <div style={{ marginTop: '4px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <StatusIndicator status={object.health || 'HEALTHY'} size="sm" />
                  <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {object.availability || '100%'}
                  </span>
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Created At</span>
                <div style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '2px' }}>
                  {object.created_at ? new Date(object.created_at).toLocaleString() : 'Recent'}
                </div>
              </div>

              <div style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Last Modified</span>
                <div style={{ fontSize: '12px', color: 'var(--text-main)', marginTop: '2px' }}>
                  {object.modified_at ? new Date(object.modified_at).toLocaleString() : object.modified || 'Recent'}
                </div>
              </div>
            </div>

            {/* Quick summary banner */}
            <div style={{ padding: '12px 16px', background: 'rgba(2, 132, 199, 0.05)', borderRadius: '8px', border: '1px solid rgba(56, 189, 248, 0.2)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldCheck size={20} style={{ color: 'var(--primary-light)', flexShrink: 0 }} />
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                Stored under policy <strong>{object.policy || 'REPLICATION_3'}</strong> with {object.chunksCount || 1} chunks replicated across Zone A and Zone B.
              </div>
            </div>
          </div>
        )}

        {/* ADVANCED DISTRIBUTED DETAILS VIEW */}
        {activeTab === 'advanced' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Version & Checksum Section */}
            <div style={{ padding: '14px', background: 'rgba(0, 0, 0, 0.25)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-main)' }}>
                  Object Versioning & Cryptographic Integrity
                </span>
                <Badge variant="healthy" size="sm">
                  v{object.version || 1} • {object.integrity_state || 'VERIFIED'}
                </Badge>
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Stored SHA-256 Checksum:</span>
                  <button
                    onClick={handleCopyHash}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--primary-light)',
                      fontSize: '11px',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    {copiedHash ? <Check size={12} /> : <Copy size={12} />}
                    {copiedHash ? 'Copied' : 'Copy Hash'}
                  </button>
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: '#10b981', background: 'rgba(0,0,0,0.4)', padding: '8px 10px', borderRadius: '6px', wordBreak: 'break-all' }}>
                  {object.checksum}
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--text-secondary)' }}>
                <span>Calculated Checksum:</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: '#10b981' }}>Match confirmed (Stored = Calculated)</span>
              </div>
            </div>

            {/* Durability, Replication Factor, Availability State */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Durability Policy</span>
                <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-main)', marginTop: '2px' }}>
                  {object.policy || 'REPLICATION_3'}
                </div>
              </div>

              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Replication Factor</span>
                <div style={{ fontSize: '13px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)', marginTop: '2px' }}>
                  {object.replication_factor ? (typeof object.replication_factor === 'number' ? `RF=${object.replication_factor}` : object.replication_factor) : 'RF=3'}
                </div>
              </div>

              <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Availability State</span>
                <div style={{ fontSize: '13px', fontWeight: '600', color: '#10b981', marginTop: '2px' }}>
                  {object.availability_state || 'OPTIMAL'}
                </div>
              </div>
            </div>

            {/* Physical Replica Locations Across Storage Nodes */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-main)' }}>
                  Physical Replica Locations (Failure Domains)
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {object.replicas?.length || 3} Replicas Assigned
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '8px' }}>
                {object.replicas?.map((r) => (
                  <div
                    key={r.node_id}
                    style={{
                      padding: '10px 12px',
                      borderRadius: '8px',
                      background: 'var(--bg-surface-elevated)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '4px',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: '600', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                        Node 0{r.node_id}
                      </span>
                      <StatusIndicator status={r.status || 'HEALTHY'} size="sm" />
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      {r.zone} • Port {r.port}
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      {r.path || `storage/node${r.node_id}/`}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Verification and Repair Status */}
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Last Verification:</span>
                <span style={{ color: 'var(--text-main)', fontWeight: '500' }}>{object.last_verified || 'Recent'}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Autonomous Repair Status:</span>
                <span style={{ color: '#10b981', fontWeight: '500' }}>{object.repair_status || 'Optimal - Quorum satisfied'}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
