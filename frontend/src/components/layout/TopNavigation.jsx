import React, { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import {
  Bell,
  User as UserIcon,
  LogOut,
  ChevronDown,
  ShieldAlert,
  HardDrive,
  RefreshCw,
  Search,
  CheckCircle2,
} from 'lucide-react';
import Badge from '../common/Badge';

export default function TopNavigation() {
  const { user, isAdmin, switchRole, logout } = useAuth();
  const { showToast } = useToast();
  const location = useLocation();
  const navigate = useNavigate();

  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const menuRef = useRef(null);
  const notifRef = useRef(null);

  // Close menus on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getPageTitle = () => {
    const path = location.pathname;
    if (path.includes('/user/dashboard')) return 'User Dashboard';
    if (path.includes('/user/storage')) return 'My Storage';
    if (path.includes('/user/buckets')) return 'Buckets & Policies';
    if (path.includes('/user/transfers')) return 'Transfers & Progress';
    if (path.includes('/admin/overview')) return 'Cluster Overview';
    if (path.includes('/admin/nodes')) return 'Storage Nodes Registry';
    if (path.includes('/admin/replication')) return 'Replication & Placement';
    if (path.includes('/admin/integrity')) return 'Integrity & Verification';
    if (path.includes('/admin/repairs')) return 'Autonomous Repair Engine';
    if (path.includes('/admin/rebalancing')) return 'Cluster Rebalancing';
    if (path.includes('/admin/metrics')) return 'Distributed Metrics';
    if (path.includes('/admin/events')) return 'Live Backend Event Stream';
    if (path.includes('/admin/chaos')) return 'Chaos Engineering Lab';
    return 'NEXVAULT';
  };

  const handleLogout = () => {
    logout();
    showToast({ type: 'info', title: 'Signed Out', message: 'You have been safely signed out.' });
    navigate('/login');
  };

  return (
    <header
      style={{
        height: '64px',
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 28px',
        position: 'relative',
        zIndex: 40,
      }}
    >
      {/* Left: Breadcrumb / Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <h2
          style={{
            fontSize: '17px',
            fontWeight: '600',
            color: 'var(--text-main)',
            fontFamily: 'var(--font-display)',
            letterSpacing: '-0.01em',
          }}
        >
          {getPageTitle()}
        </h2>

        <div style={{ height: '18px', width: '1px', backgroundColor: 'var(--border-subtle)' }} />

        <Badge variant="healthy" size="sm" pulse>
          RF=3 Quorum Active
        </Badge>
      </div>

      {/* Right: Actions, Notifications, User Menu */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Quick Search Placeholder */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '6px 12px',
            width: '220px',
            color: 'var(--text-muted)',
            fontSize: '12px',
          }}
        >
          <Search size={14} />
          <span>Search buckets or objects...</span>
        </div>

        {/* Notifications Popover */}
        <div style={{ position: 'relative' }} ref={notifRef}>
          <button
            onClick={() => setNotifOpen(!notifOpen)}
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '8px',
              background: notifOpen ? 'var(--bg-surface-hover)' : 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              position: 'relative',
            }}
          >
            <Bell size={17} />
            <span
              style={{
                position: 'absolute',
                top: '7px',
                right: '7px',
                width: '7px',
                height: '7px',
                borderRadius: '50%',
                backgroundColor: '#0ea5e9',
              }}
            />
          </button>

          {notifOpen && (
            <div
              className="glass-panel-elevated"
              style={{
                position: 'absolute',
                top: '46px',
                right: 0,
                width: '320px',
                padding: '12px',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 100,
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '4px 6px 10px',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <span style={{ fontSize: '13px', fontWeight: '600' }}>Recent Events</span>
                <span style={{ fontSize: '11px', color: 'var(--primary-light)', cursor: 'pointer' }} onClick={() => navigate('/admin/events')}>
                  View all
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
                <div style={{ padding: '8px', borderRadius: '6px', background: 'rgba(16, 185, 129, 0.08)', fontSize: '12px' }}>
                  <div style={{ color: '#10b981', fontWeight: '500' }}>Heartbeat Verified</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>All 6 nodes responding under 5ms</div>
                </div>
                <div style={{ padding: '8px', borderRadius: '6px', background: 'rgba(14, 165, 233, 0.08)', fontSize: '12px' }}>
                  <div style={{ color: '#38bdf8', fontWeight: '500' }}>Replication Policy Verified</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>Durability targets met across Zone A & B</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Menu Dropdown */}
        <div style={{ position: 'relative' }} ref={menuRef}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '6px 10px',
              borderRadius: '8px',
              background: userMenuOpen ? 'var(--bg-surface-hover)' : 'rgba(255, 255, 255, 0.03)',
              border: '1px solid var(--border-subtle)',
              cursor: 'pointer',
              color: 'var(--text-main)',
            }}
          >
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                background: isAdmin ? 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)' : '#334155',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '12px',
                fontWeight: '600',
                color: '#ffffff',
              }}
            >
              {user?.username ? user.username.charAt(0).toUpperCase() : 'U'}
            </div>
            <div style={{ textAlign: 'left', lineHeight: 1.2 }}>
              <div style={{ fontSize: '12px', fontWeight: '600' }}>{user?.username || 'Guest'}</div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{user?.role || 'USER'}</div>
            </div>
            <ChevronDown size={14} style={{ color: 'var(--text-muted)' }} />
          </button>

          {userMenuOpen && (
            <div
              className="glass-panel-elevated"
              style={{
                position: 'absolute',
                top: '46px',
                right: 0,
                width: '210px',
                padding: '6px',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '8px 10px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '4px' }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-main)' }}>{user?.username}</div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{user?.email}</div>
              </div>

              <div
                style={{
                  padding: '8px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  borderRadius: '6px',
                }}
              >
                <span>Role Permission</span>
                <Badge variant={isAdmin ? 'primary' : 'healthy'} size="sm">
                  {user?.role || 'USER'}
                </Badge>
              </div>

              <div
                style={{
                  padding: '8px 10px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '12px',
                  color: '#ef4444',
                  cursor: 'pointer',
                  borderRadius: '6px',
                  marginTop: '4px',
                  borderTop: '1px solid var(--border-subtle)',
                }}
                onClick={handleLogout}
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
