import React, { useState } from 'react';
import {
  ArrowLeftRight,
  UploadCloud,
  DownloadCloud,
  CheckCircle2,
  XCircle,
  Pause,
  Play,
  RotateCcw,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import ProgressBar from '../../components/common/ProgressBar';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';
import FileIcon from '../../components/common/FileIcon';

export default function Transfers() {
  const [activeTransfers] = useState([
    {
      id: 'tx-1',
      type: 'UPLOAD',
      file: 'geo_satellite_imagery_q3.raw',
      bucket: 'production-backups',
      size: '3.2 GB',
      progress: 68,
      speed: '48.2 MB/s',
      chunksDone: 544,
      totalChunks: 800,
      targetNodes: [1, 2, 4],
      status: 'STREAMING',
    },
    {
      id: 'tx-2',
      type: 'DOWNLOAD',
      file: 'q3_sales_aggregate.parquet',
      bucket: 'analytics-warehouse',
      size: '412 MB',
      progress: 92,
      speed: '72.4 MB/s',
      chunksDone: 95,
      totalChunks: 103,
      targetNodes: [2],
      status: 'VERIFYING_CHECKSUM',
    },
  ]);

  const [historyTransfers] = useState([
    {
      id: 'tx-10',
      type: 'UPLOAD',
      file: 'postgres_daily_dump.sql.gz',
      bucket: 'production-backups',
      size: '1.8 GB',
      duration: '38s',
      avgSpeed: '47.3 MB/s',
      status: 'COMPLETED',
      completedAt: '12 mins ago',
    },
    {
      id: 'tx-11',
      type: 'DOWNLOAD',
      file: 'security_access_logs_2026_q3.csv',
      bucket: 'corporate-docs',
      size: '88 MB',
      duration: '2.1s',
      avgSpeed: '41.9 MB/s',
      status: 'COMPLETED',
      completedAt: '45 mins ago',
    },
  ]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
          Transfers & Chunk Streaming
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
          Real-time visibility into active concurrent chunk streams, write quorums, and SHA-256 verifications.
        </p>
      </div>

      {/* Active Streams Card */}
      <Card>
        <CardHeader>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ArrowLeftRight size={18} style={{ color: 'var(--primary-light)' }} />
            <CardTitle>Active Concurrent Operations ({activeTransfers.length})</CardTitle>
          </div>
        </CardHeader>
        <CardContent style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {activeTransfers.map((tx) => (
            <div
              key={tx.id}
              style={{
                padding: '16px',
                borderRadius: '10px',
                background: 'var(--bg-surface-elevated)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {tx.type === 'UPLOAD' ? (
                    <UploadCloud size={20} style={{ color: 'var(--cyan-accent)' }} />
                  ) : (
                    <DownloadCloud size={20} style={{ color: 'var(--primary-light)' }} />
                  )}
                  <div>
                    <span style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text-main)' }}>{tx.file}</span>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                      to [{tx.bucket}]
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--cyan-accent)', fontWeight: '600' }}>
                    {tx.speed}
                  </span>
                  <Badge variant={tx.type === 'UPLOAD' ? 'info' : 'healthy'} size="sm">
                    {tx.status}
                  </Badge>
                </div>
              </div>

              {/* Progress bar */}
              <div>
                <ProgressBar
                  value={tx.progress}
                  variant="gradient"
                  height={8}
                  showPercentage
                  label={`Chunks: ${tx.chunksDone} / ${tx.totalChunks} streamed • Target Nodes: [${tx.targetNodes.map(n => `N${n}`).join(', ')}]`}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Transfer History Table */}
      <Card>
        <CardHeader>
          <CardTitle>Transfer History</CardTitle>
        </CardHeader>
        <CardContent noPadding>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Operation</TableHeader>
                <TableHeader>Object File</TableHeader>
                <TableHeader>Bucket</TableHeader>
                <TableHeader>Size</TableHeader>
                <TableHeader>Duration</TableHeader>
                <TableHeader>Avg Speed</TableHeader>
                <TableHeader>Status</TableHeader>
                <TableHeader>Completed</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {historyTransfers.map((tx) => (
                <TableRow key={tx.id}>
                  <TableCell>
                    <Badge variant={tx.type === 'UPLOAD' ? 'info' : 'neutral'} size="sm">
                      {tx.type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FileIcon filename={tx.file} size={16} />
                      <span style={{ fontWeight: '500' }}>{tx.file}</span>
                    </div>
                  </TableCell>
                  <TableCell style={{ color: 'var(--text-secondary)' }}>{tx.bucket}</TableCell>
                  <TableCell mono>{tx.size}</TableCell>
                  <TableCell mono>{tx.duration}</TableCell>
                  <TableCell mono style={{ color: 'var(--cyan-accent)' }}>{tx.avgSpeed}</TableCell>
                  <TableCell>
                    <Badge variant="healthy" size="sm" icon={CheckCircle2}>
                      SUCCESS
                    </Badge>
                  </TableCell>
                  <TableCell style={{ color: 'var(--text-muted)' }}>{tx.completedAt}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
