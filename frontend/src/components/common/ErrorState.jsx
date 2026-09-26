import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import Button from './Button';

export default function ErrorState({
  title = 'Failed to load data',
  message = 'An error occurred while communicating with the NEXVAULT control plane.',
  details,
  onRetry,
  className = '',
  style = {},
}) {
  return (
    <div
      className={`error-state-component ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '50px 24px',
        textAlign: 'center',
        background: 'rgba(239, 68, 68, 0.04)',
        borderRadius: '12px',
        border: '1px solid rgba(239, 68, 68, 0.2)',
        ...style,
      }}
    >
      <div
        style={{
          width: '52px',
          height: '52px',
          borderRadius: '12px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.25)',
          color: '#ef4444',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
        }}
      >
        <AlertTriangle size={26} />
      </div>
      <h4
        style={{
          fontSize: '15px',
          fontWeight: '600',
          color: '#f87171',
          marginBottom: '6px',
          fontFamily: 'var(--font-display)',
        }}
      >
        {title}
      </h4>
      <p
        style={{
          fontSize: '13px',
          color: 'var(--text-secondary)',
          maxWidth: '420px',
          lineHeight: '1.5',
          marginBottom: onRetry || details ? '16px' : 0,
        }}
      >
        {message}
      </p>

      {details && (
        <pre
          style={{
            background: 'rgba(0, 0, 0, 0.4)',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            color: '#fca5a5',
            maxWidth: '500px',
            overflowX: 'auto',
            marginBottom: onRetry ? '16px' : 0,
          }}
        >
          {details}
        </pre>
      )}

      {onRetry && (
        <Button variant="secondary" size="sm" icon={RefreshCw} onClick={onRetry}>
          Try Again
        </Button>
      )}
    </div>
  );
}
