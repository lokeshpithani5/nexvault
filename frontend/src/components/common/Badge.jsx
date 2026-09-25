import React from 'react';

export default function Badge({
  children,
  variant = 'neutral', // 'healthy' | 'degraded' | 'failed' | 'recovering' | 'info' | 'warning' | 'neutral'
  pulse = false,
  size = 'md',        // 'sm' | 'md'
  className = '',
  icon: Icon,
  ...props
}) {
  const variantStyles = {
    healthy: {
      bg: 'rgba(16, 185, 129, 0.12)',
      color: '#10b981',
      border: '1px solid rgba(16, 185, 129, 0.25)',
      dot: '#10b981',
    },
    degraded: {
      bg: 'rgba(245, 158, 11, 0.12)',
      color: '#f59e0b',
      border: '1px solid rgba(245, 158, 11, 0.25)',
      dot: '#f59e0b',
    },
    failed: {
      bg: 'rgba(239, 68, 68, 0.12)',
      color: '#ef4444',
      border: '1px solid rgba(239, 68, 68, 0.25)',
      dot: '#ef4444',
    },
    recovering: {
      bg: 'rgba(139, 92, 246, 0.12)',
      color: '#a78bfa',
      border: '1px solid rgba(139, 92, 246, 0.25)',
      dot: '#8b5cf6',
    },
    info: {
      bg: 'rgba(14, 165, 233, 0.12)',
      color: '#38bdf8',
      border: '1px solid rgba(14, 165, 233, 0.25)',
      dot: '#0ea5e9',
    },
    warning: {
      bg: 'rgba(245, 158, 11, 0.12)',
      color: '#fbbf24',
      border: '1px solid rgba(245, 158, 11, 0.25)',
      dot: '#fbbf24',
    },
    neutral: {
      bg: 'rgba(148, 163, 184, 0.1)',
      color: '#94a3b8',
      border: '1px solid rgba(148, 163, 184, 0.2)',
      dot: '#64748b',
    },
  }[variant] || {
    bg: 'rgba(148, 163, 184, 0.1)',
    color: '#94a3b8',
    border: '1px solid rgba(148, 163, 184, 0.2)',
    dot: '#64748b',
  };

  const isSmall = size === 'sm';

  return (
    <span
      className={`badge-component ${className}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: isSmall ? '2px 8px' : '4px 10px',
        fontSize: isSmall ? '11px' : '12px',
        fontWeight: '500',
        borderRadius: '9999px',
        backgroundColor: variantStyles.bg,
        color: variantStyles.color,
        border: variantStyles.border,
        letterSpacing: '0.02em',
        whiteSpace: 'nowrap',
      }}
      {...props}
    >
      {pulse ? (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: variantStyles.dot,
            display: 'inline-block',
          }}
          className={variant === 'healthy' ? 'pulse-healthy' : variant === 'failed' ? 'pulse-failed' : 'pulse-recovering'}
        />
      ) : Icon ? (
        <Icon size={isSmall ? 12 : 14} />
      ) : null}
      {children}
    </span>
  );
}
