import React from 'react';
import Card from './Card';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function MetricCard({
  label,
  value,
  subtext,
  icon: Icon,
  trend,         // { direction: 'up' | 'down' | 'neutral', value: '+12%' }
  status = 'default', // 'default' | 'healthy' | 'warning' | 'danger' | 'info'
  className = '',
  onClick,
}) {
  const statusColors = {
    default: { iconBg: 'rgba(255, 255, 255, 0.05)', iconColor: '#94a3b8', border: 'var(--border-subtle)' },
    healthy: { iconBg: 'rgba(16, 185, 129, 0.12)', iconColor: '#10b981', border: 'rgba(16, 185, 129, 0.25)' },
    warning: { iconBg: 'rgba(245, 158, 11, 0.12)', iconColor: '#f59e0b', border: 'rgba(245, 158, 11, 0.25)' },
    danger: { iconBg: 'rgba(239, 68, 68, 0.12)', iconColor: '#ef4444', border: 'rgba(239, 68, 68, 0.25)' },
    info: { iconBg: 'rgba(14, 165, 233, 0.12)', iconColor: '#38bdf8', border: 'rgba(14, 165, 233, 0.25)' },
  }[status] || statusColors.default;

  return (
    <Card
      interactive={!!onClick}
      onClick={onClick}
      className={`metric-card ${className}`}
      style={{
        padding: '20px 22px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        position: 'relative',
        borderColor: statusColors.border,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
        <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-secondary)' }}>
          {label}
        </span>
        {Icon && (
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              backgroundColor: statusColors.iconBg,
              color: statusColors.iconColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Icon size={18} />
          </div>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px' }}>
        <span
          style={{
            fontSize: '28px',
            fontWeight: '700',
            fontFamily: 'var(--font-display)',
            color: 'var(--text-main)',
            letterSpacing: '-0.02em',
          }}
        >
          {value}
        </span>
        {trend && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '2px',
              fontSize: '12px',
              fontWeight: '600',
              color: trend.direction === 'up' ? '#10b981' : trend.direction === 'down' ? '#ef4444' : '#94a3b8',
            }}
          >
            {trend.direction === 'up' && <ArrowUpRight size={14} />}
            {trend.direction === 'down' && <ArrowDownRight size={14} />}
            {trend.direction === 'neutral' && <Minus size={14} />}
            {trend.value}
          </span>
        )}
      </div>

      {subtext && (
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {subtext}
        </span>
      )}
    </Card>
  );
}
