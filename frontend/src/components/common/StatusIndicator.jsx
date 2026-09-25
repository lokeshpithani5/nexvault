import React from 'react';

export default function StatusIndicator({
  status = 'HEALTHY',
  label,
  showDot = true,
  size = 'md', // 'sm' | 'md'
  className = '',
}) {
  const normStatus = String(status).toUpperCase();

  const config = {
    HEALTHY: { color: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', pulseClass: 'pulse-healthy', text: 'Healthy' },
    DEGRADED: { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', pulseClass: 'pulse-degraded', text: 'Degraded' },
    FAILED: { color: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', pulseClass: 'pulse-failed', text: 'Failed' },
    RECOVERING: { color: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)', pulseClass: 'pulse-recovering', text: 'Recovering' },
    ISOLATED: { color: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)', pulseClass: 'pulse-failed', text: 'Partitioned' },
    OFFLINE: { color: '#64748b', bg: 'rgba(100, 116, 139, 0.15)', pulseClass: '', text: 'Offline' },
  }[normStatus] || { color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)', pulseClass: '', text: normStatus };

  const dotSize = size === 'sm' ? '6px' : '8px';
  const fontSize = size === 'sm' ? '11px' : '12px';

  return (
    <div
      className={`status-indicator ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        fontSize,
        fontWeight: '500',
        color: config.color,
      }}
    >
      {showDot && (
        <span
          style={{
            width: dotSize,
            height: dotSize,
            borderRadius: '50%',
            backgroundColor: config.color,
            display: 'inline-block',
            flexShrink: 0,
          }}
          className={config.pulseClass}
        />
      )}
      <span>{label || config.text}</span>
    </div>
  );
}
