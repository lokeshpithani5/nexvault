import React from 'react';
import { Database } from 'lucide-react';

export default function EmptyState({
  icon: Icon = Database,
  title = 'No data found',
  description = 'There are no records to display at this time.',
  action,
  secondaryAction,
  className = '',
  style = {},
}) {
  return (
    <div
      className={`empty-state-component ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '50px 24px',
        textAlign: 'center',
        background: 'rgba(255, 255, 255, 0.01)',
        borderRadius: '12px',
        border: '1px dashed var(--border-subtle)',
        ...style,
      }}
    >
      <div
        style={{
          width: '56px',
          height: '56px',
          borderRadius: '14px',
          backgroundColor: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-subtle)',
          color: 'var(--text-muted)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
        }}
      >
        <Icon size={26} />
      </div>
      <h4
        style={{
          fontSize: '15px',
          fontWeight: '600',
          color: 'var(--text-main)',
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
          maxWidth: '380px',
          lineHeight: '1.5',
          marginBottom: action || secondaryAction ? '20px' : 0,
        }}
      >
        {description}
      </p>
      {(action || secondaryAction) && (
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}
