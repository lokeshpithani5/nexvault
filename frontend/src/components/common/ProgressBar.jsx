import React from 'react';

export default function ProgressBar({
  value = 0,
  max = 100,
  variant = 'primary', // 'primary' | 'healthy' | 'warning' | 'danger' | 'cyan' | 'gradient'
  height = 8,
  showPercentage = false,
  label,
  className = '',
  style = {},
}) {
  const percentage = Math.min(100, Math.max(0, Math.round((value / max) * 100)));

  const variantColors = {
    primary: 'linear-gradient(90deg, #0284c7 0%, #38bdf8 100%)',
    healthy: 'linear-gradient(90deg, #059669 0%, #10b981 100%)',
    warning: 'linear-gradient(90deg, #d97706 0%, #f59e0b 100%)',
    danger: 'linear-gradient(90deg, #dc2626 0%, #ef4444 100%)',
    cyan: 'linear-gradient(90deg, #0891b2 0%, #06b6d4 100%)',
    gradient: 'linear-gradient(90deg, #0284c7 0%, #06b6d4 50%, #10b981 100%)',
  }[variant] || variantColors.primary;

  return (
    <div className={`progress-bar-container ${className}`} style={{ width: '100%', ...style }}>
      {(label || showPercentage) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '12px',
            marginBottom: '6px',
            color: 'var(--text-secondary)',
          }}
        >
          {label && <span>{label}</span>}
          {showPercentage && <span style={{ fontFamily: 'var(--font-mono)' }}>{percentage}%</span>}
        </div>
      )}
      <div
        style={{
          width: '100%',
          height: `${height}px`,
          backgroundColor: 'rgba(255, 255, 255, 0.06)',
          borderRadius: `${height}px`,
          overflow: 'hidden',
          position: 'relative',
        }}
      >
        <div
          style={{
            width: `${percentage}%`,
            height: '100%',
            background: variantColors,
            borderRadius: `${height}px`,
            transition: 'width 0.4s ease-out',
          }}
        />
      </div>
    </div>
  );
}
