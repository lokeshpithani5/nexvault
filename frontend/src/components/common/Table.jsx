import React from 'react';

export function Table({ children, className = '', style = {}, ...props }) {
  return (
    <div
      style={{
        width: '100%',
        overflowX: 'auto',
        borderRadius: '10px',
        border: '1px solid var(--border-subtle)',
        background: 'var(--bg-surface)',
        ...style,
      }}
      className={`table-wrapper ${className}`}
    >
      <table
        style={{
          width: '100%',
          borderCollapse: 'collapse',
          textAlign: 'left',
          fontSize: '13px',
        }}
        {...props}
      >
        {children}
      </table>
    </div>
  );
}

export function TableHead({ children, className = '', style = {}, ...props }) {
  return (
    <thead
      style={{
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
        borderBottom: '1px solid var(--border-medium)',
        ...style,
      }}
      className={`table-head ${className}`}
      {...props}
    >
      {children}
    </thead>
  );
}

export function TableHeader({ children, className = '', align = 'left', style = {}, ...props }) {
  return (
    <th
      style={{
        padding: '14px 18px',
        fontWeight: '600',
        color: 'var(--text-secondary)',
        fontSize: '12px',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        textAlign: align,
        whiteSpace: 'nowrap',
        ...style,
      }}
      className={`table-header-cell ${className}`}
      {...props}
    >
      {children}
    </th>
  );
}

export function TableBody({ children, className = '', style = {}, ...props }) {
  return (
    <tbody className={`table-body ${className}`} style={style} {...props}>
      {children}
    </tbody>
  );
}

export function TableRow({ children, className = '', interactive = false, onClick, style = {}, ...props }) {
  return (
    <tr
      onClick={onClick}
      style={{
        borderBottom: '1px solid var(--border-subtle)',
        transition: 'background-color var(--transition-fast)',
        cursor: interactive ? 'pointer' : 'default',
        ...style,
      }}
      className={`table-row ${className}`}
      onMouseEnter={(e) => {
        if (interactive) e.currentTarget.style.backgroundColor = 'var(--bg-surface-hover)';
      }}
      onMouseLeave={(e) => {
        if (interactive) e.currentTarget.style.backgroundColor = 'transparent';
      }}
      {...props}
    >
      {children}
    </tr>
  );
}

export function TableCell({ children, className = '', align = 'left', mono = false, style = {}, ...props }) {
  return (
    <td
      style={{
        padding: '14px 18px',
        color: 'var(--text-main)',
        textAlign: align,
        fontFamily: mono ? 'var(--font-mono)' : 'inherit',
        verticalAlign: 'middle',
        ...style,
      }}
      className={`table-cell ${className}`}
      {...props}
    >
      {children}
    </td>
  );
}

export default Table;
