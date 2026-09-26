import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  Shield,
  LayoutDashboard,
  HardDrive,
  FolderLock,
  ArrowLeftRight,
  Server,
  Wrench,
  Activity,
  Flame,
  Radio,
  Cpu,
} from 'lucide-react';
import StatusIndicator from '../common/StatusIndicator';

export default function Sidebar() {
  const { user, isAdmin } = useAuth();
  const location = useLocation();

  const userNavItems = [
    { name: 'Overview', path: '/user/dashboard', icon: LayoutDashboard },
    { name: 'My Storage', path: '/user/storage', icon: HardDrive },
    { name: 'Buckets', path: '/user/buckets', icon: FolderLock },
    { name: 'Activity', path: '/user/transfers', icon: ArrowLeftRight },
  ];

  const adminNavItems = [
    { name: 'Cluster', path: '/admin/overview', icon: Server },
    { name: 'Nodes', path: '/admin/nodes', icon: Cpu },
    { name: 'Repairs', path: '/admin/repairs', icon: Wrench },
    { name: 'Events', path: '/admin/events', icon: Radio },
    { name: 'Metrics', path: '/admin/metrics', icon: Activity },
    { name: 'Chaos Lab', path: '/admin/chaos', icon: Flame, highlight: true },
  ];

  return (
    <aside
      style={{
        width: '260px',
        height: '100vh',
        backgroundColor: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        zIndex: 50,
      }}
    >
      {/* Brand Header */}
      <div
        style={{
          padding: '24px 20px 20px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '9px',
              background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 0 16px rgba(6, 182, 212, 0.35)',
            }}
          >
            <Shield size={20} />
          </div>
          <div>
            <span
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: '18px',
                fontWeight: '700',
                letterSpacing: '0.04em',
                color: '#ffffff',
                display: 'block',
                lineHeight: 1.1,
              }}
            >
              NEXVAULT
            </span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: '500',
                color: 'var(--text-muted)',
                letterSpacing: '0.02em',
              }}
            >
              FAULT-TOLERANT STORAGE
            </span>
          </div>
        </div>

        <div
          style={{
            fontSize: '11px',
            color: 'var(--cyan-accent)',
            fontStyle: 'italic',
            marginTop: '2px',
          }}
        >
          Storage that survives failure.
        </div>
      </div>

      {/* Role Banner Badge */}
      <div style={{ padding: '12px 16px 4px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: isAdmin ? 'rgba(2, 132, 199, 0.08)' : 'rgba(255, 255, 255, 0.03)',
            borderRadius: '6px',
            padding: '6px 10px',
            border: `1px solid ${isAdmin ? 'rgba(56, 189, 248, 0.25)' : 'var(--border-subtle)'}`,
          }}
        >
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: '500' }}>
            Active Console
          </span>
          <span
            style={{
              fontSize: '10px',
              fontWeight: '700',
              fontFamily: 'var(--font-mono)',
              color: isAdmin ? '#38bdf8' : '#10b981',
              background: isAdmin ? 'rgba(2, 132, 199, 0.2)' : 'rgba(16, 185, 129, 0.15)',
              padding: '2px 8px',
              borderRadius: '4px',
            }}
          >
            {isAdmin ? 'ADMIN CONTROL' : 'USER STORAGE'}
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        {isAdmin ? (
          <>
            <div
              style={{
                fontSize: '10px',
                fontWeight: '600',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                padding: '8px 12px 4px',
              }}
            >
              Cluster Administration
            </div>

            {adminNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path || (item.path === '/admin/overview' && location.pathname.startsWith('/admin/overview'));

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: isActive ? '600' : '500',
                    color: isActive ? '#ffffff' : 'var(--text-secondary)',
                    backgroundColor: isActive
                      ? item.highlight
                        ? 'rgba(239, 68, 68, 0.15)'
                        : 'rgba(2, 132, 199, 0.15)'
                      : 'transparent',
                    border: isActive
                      ? `1px solid ${item.highlight ? 'rgba(239, 68, 68, 0.3)' : 'rgba(14, 165, 233, 0.3)'}`
                      : '1px solid transparent',
                    textDecoration: 'none',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Icon
                    size={18}
                    style={{
                      color: isActive
                        ? item.highlight ? '#f87171' : 'var(--primary-light)'
                        : item.highlight ? '#f87171' : 'var(--text-muted)',
                    }}
                  />
                  <span style={{ flex: 1 }}>{item.name}</span>
                  {item.highlight && (
                    <span
                      style={{
                        fontSize: '9px',
                        fontWeight: '700',
                        background: 'rgba(239, 68, 68, 0.2)',
                        color: '#f87171',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                      }}
                    >
                      LIVE
                    </span>
                  )}
                </NavLink>
              );
            })}

            {/* Quick Link to User Storage for Admin */}
            <div
              style={{
                fontSize: '10px',
                fontWeight: '600',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                padding: '16px 12px 4px',
              }}
            >
              Storage Client
            </div>
            <NavLink
              to="/user/storage"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 12px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: '500',
                color: location.pathname.startsWith('/user/storage') ? '#ffffff' : 'var(--text-secondary)',
                backgroundColor: location.pathname.startsWith('/user/storage') ? 'rgba(2, 132, 199, 0.15)' : 'transparent',
                border: location.pathname.startsWith('/user/storage') ? '1px solid rgba(14, 165, 233, 0.3)' : '1px solid transparent',
                textDecoration: 'none',
              }}
            >
              <HardDrive size={18} style={{ color: 'var(--text-muted)' }} />
              <span>Browse Objects</span>
            </NavLink>
          </>
        ) : (
          <>
            <div
              style={{
                fontSize: '10px',
                fontWeight: '600',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: 'var(--text-muted)',
                padding: '8px 12px 4px',
              }}
            >
              User Storage
            </div>

            {userNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname.startsWith(item.path);

              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: isActive ? '600' : '500',
                    color: isActive ? '#ffffff' : 'var(--text-secondary)',
                    backgroundColor: isActive ? 'rgba(2, 132, 199, 0.15)' : 'transparent',
                    border: isActive ? '1px solid rgba(14, 165, 233, 0.3)' : '1px solid transparent',
                    textDecoration: 'none',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <Icon
                    size={18}
                    style={{
                      color: isActive ? 'var(--primary-light)' : 'var(--text-muted)',
                    }}
                  />
                  <span style={{ flex: 1 }}>{item.name}</span>
                </NavLink>
              );
            })}
          </>
        )}
      </div>

      {/* Footer Cluster Status */}
      <div
        style={{
          padding: '16px',
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
        }}
      >
        <div
          style={{
            background: 'var(--bg-surface-elevated)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '10px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: '500' }}>
              Cluster Health
            </span>
            <StatusIndicator status="HEALTHY" size="sm" label="Online" />
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            6 Nodes • Zone A & B Active
          </div>
        </div>
      </div>
    </aside>
  );
}
