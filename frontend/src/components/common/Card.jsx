import React from 'react';

export function Card({
  children,
  className = '',
  elevated = false,
  interactive = false,
  glow = false,
  onClick,
  style = {},
  ...props
}) {
  const baseStyle = {
    background: elevated ? 'var(--bg-surface-elevated)' : 'var(--bg-surface)',
    border: `1px solid ${glow ? 'var(--border-glow)' : 'var(--border-subtle)'}`,
    borderRadius: '12px',
    backdropFilter: 'blur(12px)',
    transition: 'all var(--transition-smooth)',
    cursor: interactive ? 'pointer' : 'default',
    overflow: 'hidden',
    boxShadow: glow ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
    ...style,
  };

  return (
    <div
      className={`card-component ${className}`}
      onClick={onClick}
      style={baseStyle}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '', action, style = {}, ...props }) {
  return (
    <div
      style={{
        padding: '20px 24px',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        ...style,
      }}
      className={`card-header ${className}`}
      {...props}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', minWidth: 0 }}>
        {children}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

export function CardTitle({ children, className = '', style = {}, ...props }) {
  return (
    <h3
      style={{
        fontSize: '16px',
        fontWeight: '600',
        color: 'var(--text-main)',
        fontFamily: 'var(--font-display)',
        letterSpacing: '-0.01em',
        ...style,
      }}
      className={`card-title ${className}`}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardDescription({ children, className = '', style = {}, ...props }) {
  return (
    <p
      style={{
        fontSize: '13px',
        color: 'var(--text-secondary)',
        lineHeight: 1.4,
        ...style,
      }}
      className={`card-description ${className}`}
      {...props}
    >
      {children}
    </p>
  );
}

export function CardContent({ children, className = '', noPadding = false, style = {}, ...props }) {
  return (
    <div
      style={{
        padding: noPadding ? 0 : '24px',
        ...style,
      }}
      className={`card-content ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardFooter({ children, className = '', style = {}, ...props }) {
  return (
    <div
      style={{
        padding: '16px 24px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'rgba(0, 0, 0, 0.15)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '12px',
        ...style,
      }}
      className={`card-footer ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export default Card;
