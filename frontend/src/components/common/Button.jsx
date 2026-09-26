import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost' | 'success'
  size = 'md',        // 'sm' | 'md' | 'lg' | 'icon'
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  onClick,
  className = '',
  type = 'button',
  title,
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontWeight: '500',
    fontFamily: 'var(--font-sans)',
    borderRadius: '8px',
    transition: 'all var(--transition-fast)',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.45 : 1,
    border: '1px solid transparent',
    outline: 'none',
    whiteSpace: 'nowrap',
    userSelect: 'none',
  };

  const sizeStyles = {
    sm: { padding: '6px 12px', fontSize: '12px', height: '32px' },
    md: { padding: '8px 16px', fontSize: '13px', height: '38px' },
    lg: { padding: '10px 20px', fontSize: '14px', height: '44px' },
    icon: { width: '38px', height: '38px', padding: '0', borderRadius: '8px' }
  }[size] || sizeStyles.md;

  const variantStyles = {
    primary: {
      background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)',
      color: '#ffffff',
      borderColor: 'rgba(56, 189, 248, 0.4)',
      boxShadow: '0 2px 8px rgba(2, 132, 199, 0.25)',
    },
    secondary: {
      background: 'var(--bg-surface-elevated)',
      color: 'var(--text-main)',
      borderColor: 'var(--border-medium)',
    },
    outline: {
      background: 'transparent',
      color: 'var(--text-main)',
      borderColor: 'var(--border-medium)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--text-secondary)',
      borderColor: 'transparent',
    },
    danger: {
      background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
      color: '#ffffff',
      borderColor: 'rgba(239, 68, 68, 0.4)',
      boxShadow: '0 2px 8px rgba(220, 38, 38, 0.25)',
    },
    success: {
      background: 'linear-gradient(135deg, #059669 0%, #047857 100%)',
      color: '#ffffff',
      borderColor: 'rgba(16, 185, 129, 0.4)',
      boxShadow: '0 2px 8px rgba(5, 150, 105, 0.25)',
    },
  }[variant] || variantStyles.primary;

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      title={title}
      className={`btn-component ${className}`}
      style={{
        ...baseStyles,
        ...sizeStyles,
        ...variantStyles,
      }}
      {...props}
    >
      {loading ? (
        <Loader2 size={size === 'sm' ? 14 : 16} style={{ animation: 'spin 1s linear infinite' }} />
      ) : (
        Icon && iconPosition === 'left' && <Icon size={size === 'sm' ? 14 : 16} />
      )}
      {children}
      {!loading && Icon && iconPosition === 'right' && <Icon size={size === 'sm' ? 14 : 16} />}
    </button>
  );
}
