import React, { useState, useEffect } from 'react';
import {
  Radio,
  Pause,
  Play,
  Search,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Info,
  RotateCw,
} from 'lucide-react';
import Card, { CardHeader, CardTitle, CardContent } from '../../components/common/Card';
import Button from '../../components/common/Button';
import Badge from '../../components/common/Badge';
import EmptyState from '../../components/common/EmptyState';
import { adminService } from '../../services/adminService';
import { useToast } from '../../context/ToastContext';

export default function LiveEvents() {
  const { showToast } = useToast();
  const [isLive, setIsLive] = useState(true);
  const [selectedSeverity, setSelectedSeverity] = useState('ALL');
  const [searchFilter, setSearchFilter] = useState('');
  const [events, setEvents] = useState([]);

  useEffect(() => {
    // 1. Load initial history
    adminService.getLiveEvents(20).then((history) => {
      setEvents(history);
    }).catch(() => {});

    // 2. Subscribe to real native EventSource (/api/v1/events/stream)
    const unsubscribe = adminService.subscribeEvents(
      (newEvent) => {
        if (!isLive) return;
        setEvents((prev) => {
          // Prevent duplicates
          if (prev.some((e) => e.id === newEvent.id)) return prev;
          const formatted = {
            id: newEvent.id || Date.now() + Math.random(),
            timestamp: newEvent.timestamp || new Date().toLocaleTimeString(),
            severity: newEvent.severity || (newEvent.message?.includes('FAILED') ? 'ERROR' : newEvent.message?.includes('DEGRADED') ? 'WARN' : newEvent.message?.includes('COMPLETED') || newEvent.message?.includes('VERIFIED') ? 'SUCCESS' : 'INFO'),
            category: newEvent.category || 'CLUSTER',
            node: newEvent.node || 'Control Plane',
            message: newEvent.message || JSON.stringify(newEvent),
          };
          return [formatted, ...prev].slice(0, 100);
        });
      },
      (err) => {
        // SSE connection error handled silently with auto-retry
      }
    );

    return () => unsubscribe();
  }, [isLive]);

  const severityConfigs = {
    INFO: { icon: Info, color: '#38bdf8', bg: 'rgba(14, 165, 233, 0.1)', border: 'rgba(14, 165, 233, 0.25)' },
    WARN: { icon: AlertTriangle, color: '#fbbf24', bg: 'rgba(245, 158, 11, 0.1)', border: 'rgba(245, 158, 11, 0.25)' },
    ERROR: { icon: AlertCircle, color: '#f87171', bg: 'rgba(239, 68, 68, 0.1)', border: 'rgba(239, 68, 68, 0.25)' },
    SUCCESS: { icon: CheckCircle2, color: '#34d399', bg: 'rgba(16, 185, 129, 0.1)', border: 'rgba(16, 185, 129, 0.25)' },
  };

  const filteredEvents = events.filter((e) => {
    const matchSeverity = selectedSeverity === 'ALL' || e.severity === selectedSeverity;
    const matchSearch =
      (e.message || '').toLowerCase().includes(searchFilter.toLowerCase()) ||
      (e.category || '').toLowerCase().includes(searchFilter.toLowerCase()) ||
      (e.node || '').toLowerCase().includes(searchFilter.toLowerCase());
    return matchSeverity && matchSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 style={{ fontSize: '20px', fontWeight: '700', fontFamily: 'var(--font-display)', color: 'var(--text-main)' }}>
              Live Operational Event Stream
            </h2>
            <Badge variant={isLive ? 'healthy' : 'neutral'} size="sm" pulse={isLive}>
              {isLive ? 'SSE STREAM ACTIVE' : 'STREAM PAUSED'}
            </Badge>
          </div>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Server-Sent Events (/api/v1/events/stream) streaming real-time node failures, quorum changes, and repair sweeps.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Button
            variant={isLive ? 'secondary' : 'primary'}
            icon={isLive ? Pause : Play}
            onClick={() => {
              setIsLive(!isLive);
              showToast({
                type: 'info',
                title: isLive ? 'Stream Paused' : 'Stream Resumed',
                message: isLive ? 'Live event ingestion suspended.' : 'Listening for real-time cluster state changes.',
              });
            }}
          >
            {isLive ? 'Pause Stream' : 'Resume Stream'}
          </Button>
          <Button
            variant="ghost"
            onClick={() => setEvents([])}
            style={{ fontSize: '12px', color: 'var(--text-muted)' }}
          >
            Clear Feed
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <Card style={{ padding: '16px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Severity:</span>
            {['ALL', 'INFO', 'WARN', 'ERROR', 'SUCCESS'].map((sev) => (
              <button
                key={sev}
                onClick={() => setSelectedSeverity(sev)}
                style={{
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                  fontWeight: '600',
                  border: 'none',
                  cursor: 'pointer',
                  background: selectedSeverity === sev ? 'var(--primary)' : 'rgba(255, 255, 255, 0.04)',
                  color: selectedSeverity === sev ? '#ffffff' : 'var(--text-secondary)',
                  transition: 'all 0.15s',
                }}
              >
                {sev}
              </button>
            ))}
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              padding: '0 12px',
              height: '34px',
              width: '280px',
            }}
          >
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              type="text"
              placeholder="Filter events by text, node, or action..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-main)',
                fontSize: '12px',
                outline: 'none',
                width: '100%',
              }}
            />
          </div>
        </div>
      </Card>

      {/* Event List Feed */}
      <Card>
        <CardHeader
          action={
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Showing {filteredEvents.length} events
            </span>
          }
        >
          <CardTitle>Distributed State Audit Feed</CardTitle>
        </CardHeader>
        <CardContent noPadding>
          {filteredEvents.length === 0 ? (
            <div style={{ padding: '36px' }}>
              <EmptyState
                title="No Events Found"
                message="No operational events match your filter criteria."
              />
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {filteredEvents.map((event) => {
                const config = severityConfigs[event.severity] || severityConfigs.INFO;
                const IconComponent = config.icon;

                return (
                  <div
                    key={event.id}
                    style={{
                      padding: '12px 18px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '14px',
                      borderBottom: '1px solid var(--border-subtle)',
                      transition: 'background 0.15s ease',
                    }}
                  >
                    <div
                      style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '8px',
                        background: config.bg,
                        border: `1px solid ${config.border}`,
                        color: config.color,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <IconComponent size={16} />
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '2px' }}>
                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            fontFamily: 'var(--font-mono)',
                            color: config.color,
                            background: config.bg,
                            padding: '1px 6px',
                            borderRadius: '4px',
                          }}
                        >
                          {event.severity}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                          [{event.category || 'STATE'}]
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '500' }}>
                          {event.node}
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: '13px',
                          color: 'var(--text-main)',
                          fontFamily: event.message?.includes('SHA-256') || event.message?.includes('NODE_') ? 'var(--font-mono)' : 'var(--font-sans)',
                          wordBreak: 'break-word',
                        }}
                      >
                        {event.message}
                      </div>
                    </div>

                    <div
                      style={{
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        fontFamily: 'var(--font-mono)',
                        flexShrink: 0,
                      }}
                    >
                      {event.timestamp}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
