import React, { useState, useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  UploadCloud,
  Download,
  Trash2,
  Info,
  RefreshCw,
  Search,
  Filter,
  Grid,
  List,
  FolderLock,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Layers,
  ShieldCheck,
  ShieldAlert,
  Server,
  FileCode,
  HardDrive,
  Copy,
  Check,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import Table, { TableHead, TableHeader, TableBody, TableRow, TableCell } from '../../components/common/Table';
import FileIcon from '../../components/common/FileIcon';
import StatusIndicator from '../../components/common/StatusIndicator';
import ConfirmDialog from '../../components/common/ConfirmDialog';
import EmptyState from '../../components/common/EmptyState';
import LoadingState from '../../components/common/LoadingState';
import UploadModal from '../../components/storage/UploadModal';
import ObjectDetailsModal from '../../components/storage/ObjectDetailsModal';
import { storageService, formatBytes } from '../../services/storageService';
import { useToast } from '../../context/ToastContext';

export default function MyStorage() {
  const [searchParams] = useSearchParams();
  const initialBucket = searchParams.get('bucket') || 'all';

  const { showToast } = useToast();

  const [buckets, setBuckets] = useState([]);
  const [objects, setObjects] = useState([]);
  const [loading, setLoading] = useState(true);

  // Filter & Search States
  const [selectedBucket, setSelectedBucket] = useState(initialBucket);
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [healthFilter, setHealthFilter] = useState('ALL');
  const [durabilityFilter, setDurabilityFilter] = useState('ALL');

  // Sorting
  const [sortBy, setSortBy] = useState('modified'); // 'name' | 'size' | 'modified' | 'version'
  const [sortOrder, setSortOrder] = useState('desc'); // 'asc' | 'desc'

  // View Mode: 'table' | 'grid'
  const [viewMode, setViewMode] = useState('table');

  // Modals & Drawers
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [detailsObject, setDetailsObject] = useState(null);
  const [objectToDelete, setObjectToDelete] = useState(null);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  // Load Buckets and Objects
  const loadData = async () => {
    setLoading(true);
    try {
      const [fetchedBuckets, fetchedObjects] = await Promise.all([
        storageService.listBuckets(),
        storageService.listObjects(selectedBucket === 'all' ? null : selectedBucket),
      ]);
      setBuckets(fetchedBuckets);
      setObjects(fetchedObjects);
    } catch (err) {
      showToast({ type: 'error', title: 'Sync Error', message: err.message || 'Failed to synchronize objects.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedBucket]);

  // Filtering & Sorting Logic
  const filteredAndSortedObjects = useMemo(() => {
    return objects
      .filter((obj) => {
        // Search
        const matchesSearch =
          obj.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          obj.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
          obj.bucket.toLowerCase().includes(searchQuery.toLowerCase());

        // Type Filter
        let matchesType = true;
        if (typeFilter !== 'ALL') {
          const ext = obj.name.split('.').pop().toLowerCase();
          if (typeFilter === 'ARCHIVES') matchesType = ['zip', 'tar', 'gz', '7z', 'rar'].includes(ext);
          else if (typeFilter === 'DOCS') matchesType = ['pdf', 'doc', 'docx', 'txt', 'csv'].includes(ext);
          else if (typeFilter === 'DATA') matchesType = ['parquet', 'db', 'sql', 'json'].includes(ext);
          else if (typeFilter === 'MODELS') matchesType = ['bin', 'onnx', 'pt', 'safetensors'].includes(ext);
        }

        // Health Filter
        const matchesHealth = healthFilter === 'ALL' || obj.health === healthFilter;

        // Durability Filter
        const matchesDurability = durabilityFilter === 'ALL' || obj.policy === durabilityFilter;

        return matchesSearch && matchesType && matchesHealth && matchesDurability;
      })
      .sort((a, b) => {
        let comp = 0;
        if (sortBy === 'name') {
          comp = a.name.localeCompare(b.name);
        } else if (sortBy === 'size') {
          comp = a.sizeBytes - b.sizeBytes;
        } else if (sortBy === 'version') {
          comp = a.version - b.version;
        } else if (sortBy === 'modified') {
          comp = new Date(a.modified_at || a.created_at || 0) - new Date(b.modified_at || b.created_at || 0);
        }
        return sortOrder === 'asc' ? comp : -comp;
      });
  }, [objects, searchQuery, typeFilter, healthFilter, durabilityFilter, sortBy, sortOrder]);

  const toggleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  const handleDownload = async (obj) => {
    showToast({
      type: 'info',
      title: 'Quorum Read Initiated',
      message: `Assembling chunks for '${obj.name}' from storage nodes with SHA-256 verification...`,
    });

    try {
      const res = await storageService.downloadObject(obj.bucket, obj.key, obj.version);
      showToast({
        type: 'success',
        title: 'Download Successful',
        message: res.message || `File '${res.filename || obj.name}' downloaded successfully.`,
      });
    } catch (err) {
      showToast({ type: 'error', title: 'Download Error', message: err.message || 'Quorum read failed.' });
    }
  };

  const handleDeletePrompt = (obj) => {
    setObjectToDelete(obj);
    setDeleteConfirmOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!objectToDelete) return;
    try {
      await storageService.deleteObject(objectToDelete.bucket, objectToDelete.key);
      showToast({
        type: 'success',
        title: 'Tombstone Version Created',
        message: `Object '${objectToDelete.key}' marked as deleted. Audit history and versions preserved.`,
      });
      setDeleteConfirmOpen(false);
      setObjectToDelete(null);
      loadData();
    } catch (err) {
      showToast({ type: 'error', title: 'Delete Failed', message: err.message });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Top Header & Fast Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '14px' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
            My Storage Explorer
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Store, retrieve, inspect versions, and verify cryptographic integrity across distributed nodes.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant="secondary"
            icon={RefreshCw}
            onClick={loadData}
          >
            Refresh Catalog
          </Button>
          <Button
            variant="primary"
            icon={UploadCloud}
            onClick={() => setUploadModalOpen(true)}
          >
            Upload Object
          </Button>
        </div>
      </div>

      {/* Filter and Control Toolbar */}
      <Card style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Top Row: Bucket Select, Search, and View Mode */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, minWidth: '320px' }}>
              {/* Bucket Selector */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FolderLock size={16} style={{ color: 'var(--text-muted)' }} />
                <select
                  value={selectedBucket}
                  onChange={(e) => setSelectedBucket(e.target.value)}
                  style={{
                    height: '38px',
                    padding: '0 12px',
                    backgroundColor: 'rgba(255,255,255,0.03)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '13px',
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  <option value="all" style={{ background: '#0f172a' }}>All Buckets ({buckets.length})</option>
                  {buckets.map((b) => (
                    <option key={b.id || b.name} value={b.name} style={{ background: '#0f172a' }}>
                      {b.name} ({b.policy})
                    </option>
                  ))}
                </select>
              </div>

              {/* Search Bar */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  backgroundColor: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '0 12px',
                  height: '38px',
                  flex: 1,
                }}
              >
                <Search size={15} style={{ color: 'var(--text-muted)' }} />
                <input
                  type="text"
                  placeholder="Search by object name, key path, or bucket..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-main)',
                    fontSize: '13px',
                    outline: 'none',
                    width: '100%',
                  }}
                />
              </div>
            </div>

            {/* View Mode Toggle: Table vs Cards */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(0,0,0,0.3)', padding: '3px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
              <button
                onClick={() => setViewMode('table')}
                title="Table View"
                style={{
                  padding: '6px 10px',
                  border: 'none',
                  borderRadius: '6px',
                  background: viewMode === 'table' ? 'var(--primary)' : 'transparent',
                  color: viewMode === 'table' ? '#ffffff' : 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  fontWeight: '500',
                }}
              >
                <List size={15} />
                <span>Table</span>
              </button>
              <button
                onClick={() => setViewMode('grid')}
                title="Card Grid View"
                style={{
                  padding: '6px 10px',
                  border: 'none',
                  borderRadius: '6px',
                  background: viewMode === 'grid' ? 'var(--primary)' : 'transparent',
                  color: viewMode === 'grid' ? '#ffffff' : 'var(--text-muted)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  fontWeight: '500',
                }}
              >
                <Grid size={15} />
                <span>Cards</span>
              </button>
            </div>
          </div>

          {/* Bottom Row: Detailed Filters & Sort Pills */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
            {/* Quick Filters */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
              {/* Type Filter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Type:</span>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  style={{
                    height: '28px',
                    padding: '0 8px',
                    backgroundColor: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                >
                  <option value="ALL" style={{ background: '#0f172a' }}>All Types</option>
                  <option value="DATA" style={{ background: '#0f172a' }}>Data (.parquet, .sql)</option>
                  <option value="MODELS" style={{ background: '#0f172a' }}>Models (.onnx, .bin)</option>
                  <option value="ARCHIVES" style={{ background: '#0f172a' }}>Archives (.zip, .gz)</option>
                  <option value="DOCS" style={{ background: '#0f172a' }}>Documents (.pdf, .csv)</option>
                </select>
              </div>

              {/* Health Filter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Health:</span>
                <select
                  value={healthFilter}
                  onChange={(e) => setHealthFilter(e.target.value)}
                  style={{
                    height: '28px',
                    padding: '0 8px',
                    backgroundColor: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                >
                  <option value="ALL" style={{ background: '#0f172a' }}>All States</option>
                  <option value="HEALTHY" style={{ background: '#0f172a' }}>Healthy</option>
                  <option value="DEGRADED" style={{ background: '#0f172a' }}>Degraded</option>
                </select>
              </div>

              {/* Durability Filter */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Durability:</span>
                <select
                  value={durabilityFilter}
                  onChange={(e) => setDurabilityFilter(e.target.value)}
                  style={{
                    height: '28px',
                    padding: '0 8px',
                    backgroundColor: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                >
                  <option value="ALL" style={{ background: '#0f172a' }}>All Policies</option>
                  <option value="REPLICATION_3" style={{ background: '#0f172a' }}>RF=3 (3 Copies)</option>
                  <option value="REPLICATION_2" style={{ background: '#0f172a' }}>RF=2 (2 Copies)</option>
                </select>
              </div>
            </div>

            {/* Results Count & Sorting Shortcut */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12px' }}>
              <span style={{ color: 'var(--text-muted)' }}>
                Showing <strong>{filteredAndSortedObjects.length}</strong> objects
              </span>

              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--text-muted)' }}>Sort:</span>
                <select
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [f, o] = e.target.value.split('-');
                    setSortBy(f);
                    setSortOrder(o);
                  }}
                  style={{
                    height: '28px',
                    padding: '0 8px',
                    backgroundColor: 'rgba(255,255,255,0.04)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '6px',
                    color: 'var(--text-main)',
                    fontSize: '12px',
                    outline: 'none',
                  }}
                >
                  <option value="modified-desc" style={{ background: '#0f172a' }}>Modified: Newest First</option>
                  <option value="modified-asc" style={{ background: '#0f172a' }}>Modified: Oldest First</option>
                  <option value="name-asc" style={{ background: '#0f172a' }}>Name: A to Z</option>
                  <option value="name-desc" style={{ background: '#0f172a' }}>Name: Z to A</option>
                  <option value="size-desc" style={{ background: '#0f172a' }}>Size: Largest First</option>
                  <option value="size-asc" style={{ background: '#0f172a' }}>Size: Smallest First</option>
                  <option value="version-desc" style={{ background: '#0f172a' }}>Version: Highest First</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Content: Table or Card Grid */}
      {loading ? (
        <LoadingState message="Synchronizing distributed object metadata catalog..." skeletonRows={5} />
      ) : filteredAndSortedObjects.length === 0 ? (
        <EmptyState
          title="No objects found"
          description={searchQuery ? 'No objects matched your search and filter criteria.' : 'This bucket currently has no stored objects.'}
          action={
            <Button variant="primary" icon={UploadCloud} onClick={() => setUploadModalOpen(true)}>
              Upload First Object
            </Button>
          }
        />
      ) : viewMode === 'table' ? (
        /* TABLE VIEW */
        <Card>
          <CardContent noPadding>
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeader onClick={() => toggleSort('name')} style={{ cursor: 'pointer' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>Name & Key</span>
                      {sortBy === 'name' && (sortOrder === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                    </div>
                  </TableHeader>
                  <TableHeader>Type</TableHeader>
                  <TableHeader onClick={() => toggleSort('size')} style={{ cursor: 'pointer' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>Size</span>
                      {sortBy === 'size' && (sortOrder === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                    </div>
                  </TableHeader>
                  <TableHeader onClick={() => toggleSort('modified')} style={{ cursor: 'pointer' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>Modified</span>
                      {sortBy === 'modified' && (sortOrder === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                    </div>
                  </TableHeader>
                  <TableHeader>Health</TableHeader>
                  <TableHeader>Availability</TableHeader>
                  <TableHeader>Durability</TableHeader>
                  <TableHeader onClick={() => toggleSort('version')} style={{ cursor: 'pointer' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span>Version</span>
                      {sortBy === 'version' && (sortOrder === 'asc' ? <ArrowUp size={12} /> : <ArrowDown size={12} />)}
                    </div>
                  </TableHeader>
                  <TableHeader align="right">Actions</TableHeader>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredAndSortedObjects.map((obj) => (
                  <TableRow key={obj.id} interactive onClick={() => setDetailsObject(obj)}>
                    {/* Name & Key */}
                    <TableCell>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <FileIcon filename={obj.name} size={20} />
                        <div>
                          <div style={{ fontWeight: '600', color: 'var(--text-main)' }}>{obj.name}</div>
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                            [{obj.bucket}] {obj.key}
                          </div>
                        </div>
                      </div>
                    </TableCell>

                    {/* Type */}
                    <TableCell mono style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      {obj.name.split('.').pop().toUpperCase()}
                    </TableCell>

                    {/* Size */}
                    <TableCell mono style={{ fontWeight: '500' }}>
                      {obj.sizeFormatted || obj.size}
                    </TableCell>

                    {/* Modified */}
                    <TableCell style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {obj.modified_at ? new Date(obj.modified_at).toLocaleDateString() : obj.modified || 'Recent'}
                    </TableCell>

                    {/* Health */}
                    <TableCell>
                      <StatusIndicator status={obj.health} size="sm" />
                    </TableCell>

                    {/* Availability */}
                    <TableCell>
                      <span style={{ fontSize: '12px', color: obj.health === 'HEALTHY' ? '#10b981' : '#f59e0b', fontWeight: '500' }}>
                        {obj.availability}
                      </span>
                    </TableCell>

                    {/* Durability */}
                    <TableCell>
                      <Badge variant={obj.policy === 'ERASURE_CODING_4_2' ? 'recovering' : 'info'} size="sm">
                        {obj.durability}
                      </Badge>
                    </TableCell>

                    {/* Version */}
                    <TableCell>
                      <Badge variant="neutral" size="sm">
                        v{obj.version}
                      </Badge>
                    </TableCell>

                    {/* Actions */}
                    <TableCell align="right">
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '6px' }} onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Download Object"
                          icon={Download}
                          onClick={() => handleDownload(obj)}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Inspect Details"
                          icon={Info}
                          onClick={() => setDetailsObject(obj)}
                        />
                        <Button
                          variant="ghost"
                          size="icon"
                          title="Delete (Tombstone)"
                          icon={Trash2}
                          onClick={() => handleDeletePrompt(obj)}
                          style={{ color: '#ef4444' }}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        /* CARD / GRID VIEW */
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(310px, 1fr))', gap: '16px' }}>
          {filteredAndSortedObjects.map((obj) => (
            <Card
              key={obj.id}
              interactive
              onClick={() => setDetailsObject(obj)}
              style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '18px 20px' }}
            >
              {/* Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                  <FileIcon filename={obj.name} size={24} />
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {obj.name}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      in {obj.bucket}
                    </div>
                  </div>
                </div>

                <Badge variant="neutral" size="sm">
                  v{obj.version}
                </Badge>
              </div>

              {/* Key path */}
              <div style={{ background: 'rgba(0,0,0,0.25)', padding: '6px 10px', borderRadius: '6px', fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {obj.key}
              </div>

              {/* Status & Availability row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'block' }}>Health:</span>
                  <StatusIndicator status={obj.health} size="sm" />
                </div>
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '11px', display: 'block' }}>Size:</span>
                  <span style={{ fontFamily: 'var(--font-mono)', fontWeight: '600' }}>{obj.sizeFormatted}</span>
                </div>
              </div>

              {/* Durability Policy & Replica Badges */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '11px', color: 'var(--cyan-accent)', fontWeight: '500' }}>
                  {obj.durability}
                </span>

                <div style={{ display: 'flex', gap: '4px' }}>
                  {obj.replicas?.map((r) => (
                    <span
                      key={r.node_id}
                      title={`Node ${r.node_id} (${r.zone})`}
                      style={{
                        padding: '1px 5px',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: '600',
                        background: r.zone === 'Zone A' ? 'rgba(2, 132, 199, 0.2)' : 'rgba(6, 182, 212, 0.2)',
                        color: r.zone === 'Zone A' ? '#38bdf8' : '#22d3ee',
                      }}
                    >
                      N{r.node_id}
                    </span>
                  ))}
                </div>
              </div>

              {/* Card Footer Actions */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '10px',
                  marginTop: 'auto',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {obj.modified_at ? new Date(obj.modified_at).toLocaleDateString() : obj.modified || 'Recent'}
                </span>

                <div style={{ display: 'flex', gap: '4px' }}>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Download}
                    onClick={() => handleDownload(obj)}
                  >
                    Download
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Trash2}
                    onClick={() => handleDeletePrompt(obj)}
                    style={{ color: '#ef4444' }}
                  />
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Upload Modal Component */}
      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        buckets={buckets}
        defaultBucket={selectedBucket === 'all' ? (buckets[0]?.name || '') : selectedBucket}
        onUploadSuccess={() => loadData()}
      />

      {/* Object Details Modal Component (Basic + Advanced) */}
      <ObjectDetailsModal
        isOpen={!!detailsObject}
        onClose={() => setDetailsObject(null)}
        object={detailsObject}
        onDownload={handleDownload}
        onDelete={handleDeletePrompt}
      />

      {/* Tombstone Soft-Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Stored Object"
        message={`Are you sure you want to delete '${objectToDelete?.key}'? In accordance with NEXVAULT consistency specifications, a tombstone version will be created to preserve audit trails.`}
        confirmText="Write Tombstone Version"
        danger
      />
    </div>
  );
}
