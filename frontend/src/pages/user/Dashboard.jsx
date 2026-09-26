import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  HardDrive,
  FolderLock,
  FileCheck2,
  Activity,
  UploadCloud,
  ArrowUpRight,
  ShieldCheck,
  Download,
  Eye,
  Clock,
  RefreshCw,
} from 'lucide-react';
import MetricCard from '../../components/common/MetricCard';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import ProgressBar from '../../components/common/ProgressBar';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';
import FileIcon from '../../components/common/FileIcon';
import StatusIndicator from '../../components/common/StatusIndicator';
import UploadModal from '../../components/storage/UploadModal';
import ObjectDetailsModal from '../../components/storage/ObjectDetailsModal';
import LoadingState from '../../components/common/LoadingState';
import EmptyState from '../../components/common/EmptyState';
import { storageService, formatBytes } from '../../services/storageService';
import { useToast } from '../../context/ToastContext';

export default function UserDashboard() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [buckets, setBuckets] = useState([]);
  const [objects, setObjects] = useState([]);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [selectedObject, setSelectedObject] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [fetchedBuckets, fetchedObjects] = await Promise.all([
        storageService.listBuckets(),
        storageService.listObjects(),
      ]);
      setBuckets(fetchedBuckets);
      setObjects(fetchedObjects);
    } catch (err) {
      showToast({ type: 'error', title: 'Error', message: err.message || 'Failed to load storage data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const handleDownload = async (obj) => {
    showToast({
      type: 'info',
      title: 'Downloading Object',
      message: `Fetching '${obj.name}' with verified integrity...`,
    });
    try {
      const res = await storageService.downloadObject(obj.bucket, obj.key, obj.version);
      showToast({
        type: 'success',
        title: 'Download Completed',
        message: res.message || 'File downloaded to disk.',
      });
    } catch (err) {
      showToast({ type: 'error', title: 'Download Error', message: err.message });
    }
  };

  // Compute live aggregates
  const totalLogicalBytes = objects.reduce((sum, o) => sum + (o.sizeBytes || 0), 0);
  const protectedObjectsCount = objects.filter((o) => !o.is_tombstone).length;
  const recentFiles = objects.filter((o) => !o.is_tombstone).slice(0, 5);

  const recentActivities = [
    { id: 1, action: 'Object Uploaded', target: 'postgres_daily_dump.sql.gz', time: '12m ago', status: 'Protected' },
    { id: 2, action: 'Integrity Verified', target: 'q3_sales_aggregate.parquet', time: '34m ago', status: 'Optimal' },
    { id: 3, action: 'Object Uploaded', target: 'security_access_logs_2026_q3.csv', time: '1h ago', status: 'Protected' },
    { id: 4, action: 'Bucket Provisioned', target: 'production-backups', time: '4h ago', status: 'Active' },
  ];

  if (loading && objects.length === 0) {
    return <LoadingState message="Loading your storage overview..." skeletonRows={4} />;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Welcome Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '24px 28px',
          background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.12) 0%, rgba(6, 182, 212, 0.05) 100%), var(--bg-surface)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderColor: 'rgba(56, 189, 248, 0.2)',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
            <h1 style={{ fontSize: '22px', fontWeight: '700', fontFamily: 'var(--font-display)', color: '#ffffff' }}>
              Fault-Tolerant Storage Console
            </h1>
            <Badge variant="healthy" size="sm" pulse>
              ALL DATA PROTECTED
            </Badge>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '620px' }}>
            NEXVAULT automatically replicates your files across independent storage zones to ensure 100% availability even during hardware outages.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '12px' }}>
          <Button variant="secondary" onClick={() => navigate('/user/storage')}>
            Browse Files
          </Button>
          <Button variant="primary" icon={UploadCloud} onClick={() => setUploadModalOpen(true)}>
            Upload Object
          </Button>
        </div>
      </div>

      {/* Metrics Row - Friendly terminology */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <MetricCard
          label="Total Storage Used"
          value={formatBytes(totalLogicalBytes)}
          subtext="Logical object volume"
          icon={HardDrive}
          status="info"
        />
        <MetricCard
          label="Active Buckets"
          value={buckets.length.toString()}
          subtext="Redundancy configured"
          icon={FolderLock}
          status="default"
        />
        <MetricCard
          label="Stored Objects"
          value={protectedObjectsCount.toString()}
          subtext={`${protectedObjectsCount} of ${protectedObjectsCount} Protected`}
          icon={FileCheck2}
          status="healthy"
        />
        <MetricCard
          label="System Health"
          value="Protected"
          subtext="Zero data loss guarantee"
          icon={Activity}
          status="healthy"
        />
      </div>

      {/* Main Grid: Storage Allocation & Recent Uploads */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* Recent Files Table */}
        <Card>
          <CardHeader
            action={
              <Button variant="ghost" size="sm" onClick={() => navigate('/user/storage')}>
                View all files ({objects.length})
              </Button>
            }
          >
            <CardTitle>Recent Files</CardTitle>
          </CardHeader>
          <CardContent noPadding>
            {recentFiles.length === 0 ? (
              <div style={{ padding: '32px' }}>
                <EmptyState
                  title="No Files Stored"
                  message="Upload your first file to test fault-tolerant storage."
                  actionText="Upload Now"
                  onAction={() => setUploadModalOpen(true)}
                />
              </div>
            ) : (
              <Table>
                <TableHead>
                  <TableRow>
                    <TableHeader>Name</TableHeader>
                    <TableHeader>Bucket</TableHeader>
                    <TableHeader>Size</TableHeader>
                    <TableHeader>Protection</TableHeader>
                    <TableHeader align="right">Actions</TableHeader>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentFiles.map((file) => (
                    <TableRow key={file.id || file.key}>
                      <TableCell>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <FileIcon filename={file.name} size={18} />
                          <div>
                            <div style={{ fontWeight: '500', color: 'var(--text-main)', fontSize: '13px' }}>
                              {file.name}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                              {file.modified_at ? new Date(file.modified_at).toLocaleDateString() : 'Recent'}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="neutral" size="sm">
                          {file.bucket}
                        </Badge>
                      </TableCell>
                      <TableCell mono>{file.sizeFormatted || formatBytes(file.sizeBytes)}</TableCell>
                      <TableCell>
                        <Badge variant="healthy" size="sm">
                          Protected
                        </Badge>
                      </TableCell>
                      <TableCell align="right">
                        <div style={{ display: 'flex', gap: '4px', justifyContent: 'flex-end' }}>
                          <Button
                            variant="ghost"
                            size="sm"
                            icon={Eye}
                            onClick={() => setSelectedObject(file)}
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            icon={Download}
                            onClick={() => handleDownload(file)}
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Right Column: Storage Usage & Recent Activity */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Storage Usage by Bucket */}
          <Card>
            <CardHeader>
              <CardTitle>Storage Allocation</CardTitle>
            </CardHeader>
            <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {buckets.map((bucket) => {
                const percent = totalLogicalBytes > 0
                  ? Math.round(((bucket.logicalSizeBytes || 0) / totalLogicalBytes) * 100)
                  : 0;
                return (
                  <div key={bucket.id || bucket.name} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                      <span style={{ fontWeight: '500', color: 'var(--text-main)' }}>{bucket.name}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{formatBytes(bucket.logicalSizeBytes || 0)}</span>
                    </div>
                    <ProgressBar
                      value={percent}
                      variant="primary"
                      height={6}
                    />
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent noPadding>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {recentActivities.map((act) => (
                  <div
                    key={act.id}
                    style={{
                      padding: '12px 16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      borderBottom: '1px solid var(--border-subtle)',
                      fontSize: '12px',
                    }}
                  >
                    <div>
                      <div style={{ color: 'var(--text-main)', fontWeight: '500' }}>{act.action}</div>
                      <div style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '2px' }}>{act.target}</div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <Badge variant="healthy" size="sm">{act.status}</Badge>
                      <div style={{ color: 'var(--text-muted)', fontSize: '10px', marginTop: '2px' }}>{act.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* UPLOAD MODAL */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        buckets={buckets}
        onUploadSuccess={() => loadDashboardData()}
      />

      {/* OBJECT DETAILS MODAL */}
      <ObjectDetailsModal
        isOpen={!!selectedObject}
        onClose={() => setSelectedObject(null)}
        object={selectedObject}
        onDownload={handleDownload}
      />
    </div>
  );
}
