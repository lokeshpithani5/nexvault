import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FolderPlus,
  FolderLock,
  HardDrive,
  Trash2,
  FolderOpen,
  RefreshCw,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent, CardFooter } from '../../components/common/Card';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import Modal from '../../components/common/Modal';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import LoadingState from '../../components/common/LoadingState';
import EmptyState from '../../components/common/EmptyState';
import { storageService, formatBytes } from '../../services/storageService';
import { useToast } from '../../context/ToastContext';

export default function Buckets() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [buckets, setBuckets] = useState([]);
  const [loading, setLoading] = useState(true);

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [newBucketName, setNewBucketName] = useState('');
  const [newBucketPolicy, setNewBucketPolicy] = useState('REPLICATION_3');
  const [bucketToDelete, setBucketToDelete] = useState(null);

  const loadBuckets = async () => {
    setLoading(true);
    try {
      const data = await storageService.listBuckets();
      setBuckets(data);
    } catch (err) {
      showToast({ type: 'error', title: 'Error', message: err.message || 'Failed to fetch buckets.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBuckets();
  }, []);

  const handleCreateBucket = async (e) => {
    e.preventDefault();
    const cleanName = newBucketName.trim().toLowerCase().replace(/[^a-z0-9-]/g, '-');
    if (!cleanName) {
      showToast({ type: 'warning', title: 'Validation', message: 'Bucket name cannot be empty.' });
      return;
    }

    try {
      const created = await storageService.createBucket(cleanName, newBucketPolicy);
      showToast({
        type: 'success',
        title: 'Bucket Provisioned',
        message: `Bucket '${created.name}' initialized under policy ${created.policy}.`,
      });
      setNewBucketName('');
      setCreateModalOpen(false);
      loadBuckets();
    } catch (err) {
      showToast({ type: 'error', title: 'Creation Failed', message: err.message });
    }
  };

  const handleDeleteBucket = async () => {
    if (!bucketToDelete) return;
    try {
      await storageService.deleteBucket(bucketToDelete.id || bucketToDelete.name);
      showToast({
        type: 'info',
        title: 'Bucket Removed',
        message: `Bucket '${bucketToDelete.name}' has been deregistered from control plane.`,
      });
      setBucketToDelete(null);
      loadBuckets();
    } catch (err) {
      showToast({ type: 'error', title: 'Deletion Failed', message: err.message });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header and Provision Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
            Storage Buckets & Redundancy Policies
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Isolated namespaces with configurable cross-zone replication and consensus read/write quorums.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={loadBuckets}
          >
            Refresh
          </Button>
          <Button
            variant="primary"
            icon={FolderPlus}
            onClick={() => setCreateModalOpen(true)}
          >
            Create Bucket
          </Button>
        </div>
      </div>

      {/* Buckets Grid */}
      {loading ? (
        <LoadingState message="Loading bucket catalog from control plane..." skeletonRows={3} />
      ) : buckets.length === 0 ? (
        <EmptyState
          title="No Storage Buckets Configured"
          message="Create your first fault-tolerant bucket to begin storing and replicating objects across zones."
          actionText="Create First Bucket"
          onAction={() => setCreateModalOpen(true)}
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
          {buckets.map((bucket) => {
            const overheadMultiplier = bucket.policy === 'REPLICATION_2' ? 2.0 : 3.0;
            const logicalBytes = bucket.logicalSizeBytes || 0;
            const rawBytes = logicalBytes * overheadMultiplier;

            return (
              <Card key={bucket.id || bucket.name} style={{ display: 'flex', flexDirection: 'column' }}>
                <CardHeader
                  action={
                    <Badge
                      variant={bucket.policy === 'REPLICATION_2' ? 'info' : 'healthy'}
                      size="sm"
                    >
                      {bucket.policy === 'REPLICATION_2' ? 'RF=2 (2 Copies)' : 'RF=3 (3 Copies)'}
                    </Badge>
                  }
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <FolderLock size={20} style={{ color: 'var(--primary-light)' }} />
                    <CardTitle>{bucket.name}</CardTitle>
                  </div>
                </CardHeader>

                <CardContent style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Objects</span>
                      <div style={{ fontSize: '16px', fontWeight: '600', color: 'var(--text-main)', marginTop: '2px' }}>
                        {bucket.objectsCount || 0}
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Logical Size</span>
                      <div style={{ fontSize: '16px', fontWeight: '600', fontFamily: 'var(--font-mono)', color: 'var(--text-main)', marginTop: '2px' }}>
                        {formatBytes(logicalBytes)}
                      </div>
                    </div>
                  </div>

                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                      <span>Replication Overhead:</span>
                      <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--cyan-accent)', fontWeight: '600' }}>
                        {formatBytes(rawBytes)} ({overheadMultiplier.toFixed(1)}x overhead)
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Durability Guarantee:</span>
                      <span style={{ color: '#10b981', fontWeight: '500' }}>
                        {bucket.policy === 'REPLICATION_2' ? 'Survives 1 Node Crash' : 'Survives 2 Node Crashes'}
                      </span>
                    </div>
                  </div>
                </CardContent>

                <CardFooter>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Created: {bucket.created_at ? new Date(bucket.created_at).toLocaleDateString() : 'Active'}
                  </span>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Button
                      variant="secondary"
                      size="sm"
                      icon={FolderOpen}
                      onClick={() => navigate(`/user/storage?bucket=${bucket.name}`)}
                    >
                      Open
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={Trash2}
                      onClick={() => setBucketToDelete(bucket)}
                      style={{ color: '#ef4444' }}
                    >
                      Delete
                    </Button>
                  </div>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* CREATE BUCKET MODAL */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create New Bucket"
        description="Provision a new object storage namespace with cross-zone replication invariants."
        size="md"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setCreateModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" onClick={handleCreateBucket}>
              Create Bucket
            </Button>
          </>
        }
      >
        <form onSubmit={handleCreateBucket} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Bucket Identifier
            </label>
            <input
              type="text"
              value={newBucketName}
              onChange={(e) => setNewBucketName(e.target.value)}
              placeholder="e.g., customer-vault or analytics-logs"
              autoFocus
              style={{
                width: '100%',
                height: '40px',
                padding: '0 12px',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid var(--border-medium)',
                borderRadius: '8px',
                color: 'var(--text-main)',
                fontSize: '13px',
                outline: 'none',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)', marginBottom: '8px' }}>
              Durability & Redundancy Policy
            </label>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Option 1: RF=3 */}
              <label
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: `1px solid ${newBucketPolicy === 'REPLICATION_3' ? 'var(--border-glow)' : 'var(--border-subtle)'}`,
                  background: newBucketPolicy === 'REPLICATION_3' ? 'rgba(2, 132, 199, 0.1)' : 'rgba(255,255,255,0.02)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                }}
              >
                <input
                  type="radio"
                  name="policy"
                  value="REPLICATION_3"
                  checked={newBucketPolicy === 'REPLICATION_3'}
                  onChange={() => setNewBucketPolicy('REPLICATION_3')}
                  style={{ marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-main)' }}>
                    Replication Factor 3 (Default Enterprise)
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    3 full copies distributed across Zone A and Zone B. Survives 2 simultaneous node crashes. 3.0x overhead.
                  </div>
                </div>
              </label>

              {/* Option 2: RF=2 */}
              <label
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: `1px solid ${newBucketPolicy === 'REPLICATION_2' ? 'var(--border-glow)' : 'var(--border-subtle)'}`,
                  background: newBucketPolicy === 'REPLICATION_2' ? 'rgba(2, 132, 199, 0.1)' : 'rgba(255,255,255,0.02)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                }}
              >
                <input
                  type="radio"
                  name="policy"
                  value="REPLICATION_2"
                  checked={newBucketPolicy === 'REPLICATION_2'}
                  onChange={() => setNewBucketPolicy('REPLICATION_2')}
                  style={{ marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-main)' }}>
                    Replication Factor 2 (Standard Redundancy)
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                    2 copies placed in separate zones (1 in Zone A, 1 in Zone B). Survives 1 node crash. 2.0x overhead.
                  </div>
                </div>
              </label>
            </div>
          </div>
        </form>
      </Modal>

      {/* CONFIRM DELETE DIALOG */}
      <ConfirmDialog
        isOpen={!!bucketToDelete}
        onClose={() => setBucketToDelete(null)}
        onConfirm={handleDeleteBucket}
        title={`Delete Bucket '${bucketToDelete?.name}'?`}
        message="This operation will deregister the bucket from the control plane catalog. Are you sure you want to proceed?"
        confirmText="Deregister Bucket"
        variant="danger"
      />
    </div>
  );
}
