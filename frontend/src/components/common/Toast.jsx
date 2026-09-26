import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

export default function Toast({
  id,
  type = 'info', // 'success' | 'error' | 'warning' | 'info'
  title,
  message,
  onDismiss,
}) {
  const configs = {
    success: {
      icon: CheckCircle2,
      color: '#10b981',
      bg: 'rgba(16, 185, 129, 0.1)',
      border: 'rgba(16, 185, 129, 0.3)',
    },
    error: {
      icon: AlertCircle,
      color: '#ef4444',
      bg: 'rgba(239, 68, 68, 0.1)',
      border: 'rgba(239, 68, 68, 0.3)',
    },
    warning: {
      icon: AlertTriangle,
      color: '#f59e0b',
      bg: 'rgba(245, 158, 11, 0.1)',
      border: 'rgba(245, 158, 11, 0.3)',
    },
    info: {
      icon: Info,
      color: '#38bdf8',
      bg: 'rgba(14, 165, 233, 0.1)',
      border: 'rgba(14, 165, 233, 0.3)',
    },
  }[type] || {
    icon: Info,
    color: '#38bdf8',
    bg: 'rgba(14, 165, 233, 0.1)',
    border: 'rgba(14, 165, 233, 0.3)',
  };

  const Icon = configs.icon;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '12px',
        padding: '14px 16px',
        borderRadius: '10px',
        background: '#0f172a',
        border: `1px solid ${configs.border}`,
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 0 12px rgba(0, 0, 0, 0.4)',
        minWidth: '300px',
        maxWidth: '420px',
        animation: 'slideInRight 0.25s ease-out',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          color: configs.color,
          flexShrink: 0,
          marginTop: '2px',
        }}
      >
        <Icon size={18} />
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        {title && (
          <h5
            style={{
              fontSize: '13px',
              fontWeight: '600',
              color: 'var(--text-main)',
              marginBottom: message ? '2px' : 0,
            }}
          >
            {title}
          </h5>
        )}
        {message && (
          <p
            style={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              lineHeight: 1.4,
            }}
          >
            {message}
          </p>
        )}
      </div>

      <button
        onClick={() => onDismiss(id)}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          padding: '2px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <X size={14} />
      </button>
    </div>
  );
}
