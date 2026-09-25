import React, { useState, useRef } from 'react';
import {
  UploadCloud,
  File,
  CheckCircle2,
  AlertTriangle,
  X,
  Server,
  Layers,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import Badge from '../common/Badge';
import ProgressBar from '../common/ProgressBar';
import FileIcon from '../common/FileIcon';
import { formatBytes, storageService } from '../../services/storageService';
import { useToast } from '../../context/ToastContext';

export default function UploadModal({
  isOpen,
  onClose,
  buckets = [],
  defaultBucket = '',
  onUploadSuccess,
}) {
  const { showToast } = useToast();
  const fileInputRef = useRef(null);

  const [selectedFile, setSelectedFile] = useState(null);
  const [targetBucket, setTargetBucket] = useState(defaultBucket || (buckets[0]?.name || 'production-backups'));
  const [objectKey, setObjectKey] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  // Upload States: 'IDLE' | 'UPLOADING' | 'SUCCESS' | 'FAILURE'
  const [uploadStatus, setUploadStatus] = useState('IDLE');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');

  // Synchronize target bucket if defaultBucket changes
  React.useEffect(() => {
    if (defaultBucket) {
      setTargetBucket(defaultBucket);
    } else if (buckets.length > 0 && !targetBucket) {
      setTargetBucket(buckets[0].name);
    }
  }, [defaultBucket, buckets]);

  const handleFileSelect = (file) => {
    if (!file) return;
    setSelectedFile(file);
    if (!objectKey) {
      setObjectKey(file.name);
    }
    setUploadStatus('IDLE');
    setUploadProgress(0);
    setUploadResult(null);
    setErrorMessage('');
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const startUpload = async () => {
    if (!selectedFile) {
      showToast({ type: 'warning', title: 'File Required', message: 'Please select a file to upload.' });
      return;
    }
    if (!objectKey.trim()) {
      showToast({ type: 'warning', title: 'Key Required', message: 'Please provide an object key/path.' });
      return;
    }

    setUploadStatus('UPLOADING');
    setUploadProgress(5);

    try {
      const result = await storageService.uploadObject(
        targetBucket,
        objectKey,
        selectedFile,
        (progress) => setUploadProgress(progress)
      );

      setUploadResult(result);
      setUploadStatus('SUCCESS');
      showToast({
        type: 'success',
        title: 'Upload Successful',
        message: `Object '${objectKey}' replicated across assigned storage nodes.`,
      });

      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      setUploadStatus('FAILURE');
      setErrorMessage(err.message || 'Quorum write failed or node timeout occurred.');
      showToast({
        type: 'error',
        title: 'Upload Failed',
        message: err.message || 'Could not complete object upload.',
      });
    }
  };

  const resetUpload = () => {
    setSelectedFile(null);
    setObjectKey('');
    setUploadStatus('IDLE');
    setUploadProgress(0);
    setUploadResult(null);
    setErrorMessage('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const selectedBucketObj = buckets.find((b) => b.name === targetBucket);

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (uploadStatus !== 'UPLOADING') {
          resetUpload();
          onClose();
        }
      }}
      title="Upload Object to Cluster"
      description="Objects are chunked, checksum-hashed with SHA-256, and concurrently written to storage nodes."
      size="md"
      footer={
        uploadStatus === 'SUCCESS' ? (
          <>
            <Button variant="secondary" size="sm" onClick={resetUpload}>
              Upload Another
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                resetUpload();
                onClose();
              }}
            >
              Done
            </Button>
          </>
        ) : uploadStatus === 'FAILURE' ? (
          <>
            <Button variant="ghost" size="sm" onClick={resetUpload}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" icon={RefreshCw} onClick={startUpload}>
              Retry Upload
            </Button>
          </>
        ) : (
          <>
            <Button
              variant="ghost"
              size="sm"
              disabled={uploadStatus === 'UPLOADING'}
              onClick={() => {
                resetUpload();
                onClose();
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={UploadCloud}
              loading={uploadStatus === 'UPLOADING'}
              disabled={!selectedFile}
              onClick={startUpload}
            >
              Upload to {targetBucket}
            </Button>
          </>
        )
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {/* SUCCESS STATE */}
        {uploadStatus === 'SUCCESS' && uploadResult && (
          <div
            style={{
              padding: '24px 20px',
              borderRadius: '12px',
              background: 'rgba(16, 185, 129, 0.06)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div
              style={{
                width: '52px',
                height: '52px',
                borderRadius: '50%',
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#10b981',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <CheckCircle2 size={30} />
            </div>

            <div>
              <h4 style={{ fontSize: '16px', fontWeight: '600', color: '#ffffff', marginBottom: '4px' }}>
                Upload & Replication Completed
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Object committed to <strong>{uploadResult.bucket}</strong> with version <strong>v{uploadResult.version}</strong>.
              </p>
            </div>

            {/* Checksum & Chunks Details */}
            <div
              style={{
                width: '100%',
                background: 'rgba(0, 0, 0, 0.3)',
                padding: '12px',
                borderRadius: '8px',
                fontSize: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                textAlign: 'left',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Object Key:</span>
                <span style={{ fontWeight: '500', color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>
                  {uploadResult.key}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Logical Size:</span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-main)' }}>
                  {uploadResult.sizeFormatted} ({uploadResult.chunksCount} chunks)
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>SHA-256:</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: '#10b981' }}>
                  {uploadResult.checksum.substring(0, 20)}...
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', marginTop: '2px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Replica Nodes:</span>
                <div style={{ display: 'flex', gap: '6px' }}>
                  {uploadResult.replicas?.map((r) => (
                    <span
                      key={r.node_id}
                      style={{
                        padding: '1px 6px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: '600',
                        background: r.zone === 'Zone A' ? 'rgba(2, 132, 199, 0.2)' : 'rgba(6, 182, 212, 0.2)',
                        color: r.zone === 'Zone A' ? '#38bdf8' : '#22d3ee',
                      }}
                    >
                      N0{r.node_id} ({r.zone})
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* FAILURE STATE */}
        {uploadStatus === 'FAILURE' && (
          <div
            style={{
              padding: '24px 20px',
              borderRadius: '12px',
              background: 'rgba(239, 68, 68, 0.06)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <div
              style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <AlertTriangle size={26} />
            </div>
            <div>
              <h4 style={{ fontSize: '15px', fontWeight: '600', color: '#f87171', marginBottom: '4px' }}>
                Object Upload Failed
              </h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '400px' }}>
                {errorMessage}
              </p>
            </div>
          </div>
        )}

        {/* UPLOADING IN PROGRESS STATE */}
        {uploadStatus === 'UPLOADING' && (
          <div
            style={{
              padding: '24px',
              borderRadius: '12px',
              background: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-glow)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileIcon filename={selectedFile?.name || ''} size={24} />
                <div>
                  <div style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text-main)' }}>
                    {objectKey}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {formatBytes(selectedFile?.size || 0)} • Streaming 4MB chunks
                  </div>
                </div>
              </div>
              <Badge variant="info" size="sm" pulse>
                QUORUM STREAMING
              </Badge>
            </div>

            <ProgressBar
              value={uploadProgress}
              variant="gradient"
              height={10}
              showPercentage
              label="Distributing chunks across Zone A and Zone B storage nodes..."
            />

            <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Calculating SHA-256 checksum in-flight • Verifying write quorum...
            </div>
          </div>
        )}

        {/* IDLE / CONFIGURATION FORM */}
        {uploadStatus === 'IDLE' && (
          <>
            {/* Target Bucket Selector */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                Target Bucket
              </label>
              <select
                value={targetBucket}
                onChange={(e) => setTargetBucket(e.target.value)}
                style={{
                  width: '100%',
                  height: '40px',
                  padding: '0 12px',
                  backgroundColor: 'rgba(255,255,255,0.03)',
                  border: '1px solid var(--border-medium)',
                  borderRadius: '8px',
                  color: 'var(--text-main)',
                  fontSize: '13px',
                  outline: 'none',
                }}
              >
                {buckets.map((b) => (
                  <option key={b.id || b.name} value={b.name} style={{ background: '#0f172a' }}>
                    {b.name} ({b.policy})
                  </option>
                ))}
              </select>
              {selectedBucketObj && (
                <div style={{ fontSize: '11px', color: 'var(--cyan-accent)', marginTop: '4px' }}>
                  Policy: {selectedBucketObj.policy} • Min Write Quorum: {selectedBucketObj.min_write_quorum || 2} nodes
                </div>
              )}
            </div>

            {/* Drag & Drop Zone */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
              style={{ display: 'none' }}
            />

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                padding: '36px 20px',
                border: `2px dashed ${isDragging ? 'var(--cyan-accent)' : 'var(--border-medium)'}`,
                backgroundColor: isDragging ? 'rgba(6, 182, 212, 0.06)' : 'rgba(255, 255, 255, 0.01)',
                borderRadius: '12px',
                textAlign: 'center',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '12px',
                transition: 'all 0.2s ease',
              }}
            >
              <div
                style={{
                  width: '52px',
                  height: '52px',
                  borderRadius: '12px',
                  background: 'rgba(2, 132, 199, 0.12)',
                  color: 'var(--primary-light)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <UploadCloud size={28} />
              </div>

              {selectedFile ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileIcon filename={selectedFile.name} size={24} />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontWeight: '600', fontSize: '13px', color: 'var(--text-main)' }}>
                      {selectedFile.name}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {formatBytes(selectedFile.size)} • Click or drop to replace
                    </div>
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-main)' }}>
                    Drag & drop file here, or click to browse
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Supports any file type. Chunks will be distributed across independent nodes.
                  </div>
                </div>
              )}
            </div>

            {/* Object Key / Path Input */}
            {selectedFile && (
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '500', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Object Key / Storage Path
                </label>
                <input
                  type="text"
                  value={objectKey}
                  onChange={(e) => setObjectKey(e.target.value)}
                  placeholder="e.g. datasets/raw_logs.parquet"
                  style={{
                    width: '100%',
                    height: '40px',
                    padding: '0 12px',
                    backgroundColor: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '13px',
                    outline: 'none',
                    fontFamily: 'var(--font-mono)',
                  }}
                />
                <span style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                  Forward slashes (/) represent logical folders in the bucket.
                </span>
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
