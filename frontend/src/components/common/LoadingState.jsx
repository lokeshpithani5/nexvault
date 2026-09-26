import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingState({
  message = 'Loading data...',
  skeletonRows = 0,
  className = '',
  style = {},
}) {
  if (skeletonRows > 0) {
    return (
      <div
        className={`loading-skeleton-container ${className}`}
        style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%', padding: '16px', ...style }}
      >
        {Array.from({ length: skeletonRows }).map((_, i) => (
          <div
            key={i}
            className="shimmer"
            style={{
              height: '44px',
              borderRadius: '8px',
              width: '100%',
            }}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={`loading-state-component ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px 24px',
        gap: '14px',
        color: 'var(--text-secondary)',
        ...style,
      }}
    >
      <Loader2
        size={32}
        style={{
          color: 'var(--primary-light)',
          animation: 'spin 1.2s linear infinite',
        }}
      />
      <span style={{ fontSize: '13px', fontWeight: '500' }}>{message}</span>
    </div>
  );
}
