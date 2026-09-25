import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCw,
  Search,
  ShieldCheck,
  FileCheck,
  Binary,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import MetricCard from '../../components/common/MetricCard';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';
import StatusIndicator from '../../components/common/StatusIndicator';
import { useToast } from '../../context/ToastContext';

export default function Integrity() {
  const { showToast } = useToast();
  const [scrubbing, setScrubbing] = useState(false);

  const [auditedReplicas, setAuditedReplicas] = useState([
    {
      id: 'rep-01',
      objectKey: 'database/postgres_daily_dump.sql.gz',
      chunkIndex: 0,
      nodeId: 1,
      zone: 'Zone A',
      storedChecksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      calculatedChecksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      status: 'HEALTHY',
      lastScrubbed: '3 mins ago',
    },
    {
      id: 'rep-02',
      objectKey: 'models/sentiment_transformer_v4.onnx',
      chunkIndex: 12,
      nodeId: 5,
      zone: 'Zone B',
      storedChecksum: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      calculatedChecksum: '7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069',
      status: 'HEALTHY',
      lastScrubbed: '5 mins ago',
    },
    {
      id: 'rep-03',
      objectKey: 'telemetry/flight_sensor_stream.parquet',
      chunkIndex: 4,
      nodeId: 3,
      zone: 'Zone A',
      storedChecksum: 'a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e',
      calculatedChecksum: 'a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e',
      status: 'HEALTHY',
      lastScrubbed: '8 mins ago',
    },
    {
      id: 'rep-04',
      objectKey: 'audit/security_access_logs_2026_q3.csv',
      chunkIndex: 1,
      nodeId: 4,
      zone: 'Zone B',
      storedChecksum: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
      calculatedChecksum: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
      status: 'HEALTHY',
      lastScrubbed: '11 mins ago',
    },
  ]);

  const handleTriggerScrub = () => {
    setScrubbing(true);
    showToast({
      type: 'info',
      title: 'Scrub Initiated',
      message: 'Background Scrubber dispatching SHA-256 verification workers to storage nodes...',
    });
    setTimeout(() => {
      setScrubbing(false);
      showToast({
        type: 'success',
        title: 'Scrub Completed',
        message: '1,428 object chunks verified against PostgreSQL stored checksums. 0 silent corruptions detected.',
      });
    }, 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
            Cryptographic Integrity Scrubber
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Continuous end-to-end SHA-256 verification to detect and heal bit-rot and silent disk corruptions.
          </p>
        </div>

        <Button
          variant="primary"
          icon={Play}
          loading={scrubbing}
          onClick={handleTriggerScrub}
        >
          Trigger Full Integrity Scrub
        </Button>
      </div>

      {/* Telemetry Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        <MetricCard
          label="Replicas Verified"
          value="4,284"
          subtext="100% SHA-256 matched"
          icon={ShieldCheck}
          status="healthy"
        />
        <MetricCard
          label="Bit-Rot Corruptions"
          value="0"
          subtext="No silent corruptions active"
          icon={CheckCircle2}
          status="healthy"
        />
        <MetricCard
          label="Scrub Frequency"
          value="Every 1 Hour"
          subtext="Background worker active"
          icon={RotateCw}
          status="default"
        />
        <MetricCard
          label="Auto-Healing Rate"
          value="< 850 ms"
          subtext="Mean time to rebuild corrupt chunk"
          icon={Binary}
          status="info"
        />
      </div>

      {/* Scrub Audit Log */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Verified Replicas (SHA-256 Catalog)</CardTitle>
        </CardHeader>
        <CardContent noPadding>
          <Table>
            <TableHead>
              <TableRow>
                <TableHeader>Object Key & Chunk</TableHeader>
                <TableHeader>Storage Node</TableHeader>
                <TableHeader>Zone</TableHeader>
                <TableHeader>Stored vs Calculated Checksum</TableHeader>
                <TableHeader>Integrity Status</TableHeader>
                <TableHeader>Scrubbed</TableHeader>
              </TableRow>
            </TableHead>
            <TableBody>
              {auditedReplicas.map((rep) => (
                <TableRow key={rep.id}>
                  <TableCell>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontWeight: '500', color: 'var(--text-main)' }}>{rep.objectKey}</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Chunk #{rep.chunkIndex}</span>
                    </div>
                  </TableCell>
                  <TableCell mono>Node 0{rep.nodeId}</TableCell>
                  <TableCell>
                    <Badge variant={rep.zone === 'Zone A' ? 'info' : 'recovering'} size="sm">
                      {rep.zone}
                    </Badge>
                  </TableCell>
                  <TableCell mono>
                    <div style={{ fontSize: '11px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                      <span style={{ color: '#10b981' }}>S: {rep.storedChecksum.substring(0, 16)}...</span>
                      <span style={{ color: '#10b981' }}>C: {rep.calculatedChecksum.substring(0, 16)}...</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <StatusIndicator status={rep.status} size="sm" />
                  </TableCell>
                  <TableCell style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                    {rep.lastScrubbed}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
