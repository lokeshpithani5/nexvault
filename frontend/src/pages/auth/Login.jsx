import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../context/ToastContext';
import { Shield, Lock, User, ArrowRight, CheckCircle2 } from 'lucide-react';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';

export default function Login() {
  const [identifier, setIdentifier] = useState('admin@nexvault.io');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!identifier.trim()) {
      showToast({ type: 'warning', title: 'Validation', message: 'Please enter your username or email.' });
      return;
    }

    setLoading(true);
    try {
      const res = await login(identifier.trim(), password);
      showToast({
        type: 'success',
        title: 'Authentication Successful',
        message: `Signed in as ${res.user.role}: ${res.user.email || res.user.username}`,
      });
      if (res.user.role === 'ADMIN') {
        navigate('/admin/overview');
      } else {
        navigate('/user/dashboard');
      }
    } catch (err) {
      showToast({ type: 'error', title: 'Login Failed', message: err.message || 'Invalid credentials' });
    } finally {
      setLoading(false);
    }
  };

  const handleQuickDemo = async (role) => {
    const demoId = role === 'ADMIN' ? 'admin@nexvault.io' : 'demo@nexvault.io';
    const demoPass = role === 'ADMIN' ? 'admin123' : 'demo123';
    setIdentifier(demoId);
    setPassword(demoPass);
    setLoading(true);
    try {
      const res = await login(demoId, demoPass);
      showToast({
        type: 'success',
        title: 'Demo Session Active',
        message: `Signed in as ${role} (${demoId}) for live evaluation.`,
      });
      navigate(role === 'ADMIN' ? '/admin/overview' : '/user/dashboard');
    } catch (err) {
      showToast({ type: 'error', title: 'Login Failed', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100vw',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'radial-gradient(circle at 50% 20%, rgba(14, 165, 233, 0.12) 0%, transparent 60%), #080c14',
        padding: '24px',
      }}
    >
      <div style={{ width: '100%', maxWidth: '440px' }}>
        {/* Brand Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '14px',
              background: 'linear-gradient(135deg, #0284c7 0%, #06b6d4 100%)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#ffffff',
              boxShadow: '0 0 25px rgba(6, 182, 212, 0.4)',
              marginBottom: '16px',
            }}
          >
            <Shield size={30} />
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: '28px',
              fontWeight: '700',
              letterSpacing: '-0.02em',
              color: '#ffffff',
              marginBottom: '6px',
            }}
          >
            NEXVAULT
          </h1>
          <p style={{ color: 'var(--cyan-accent)', fontSize: '14px', fontWeight: '500' }}>
            Storage that survives failure.
          </p>
        </div>

        {/* Login Card */}
        <Card style={{ padding: '32px 28px' }}>
          <div style={{ marginBottom: '24px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-main)', marginBottom: '6px' }}>
              Sign in to NEXVAULT
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Enter your credentials to access the distributed storage control plane.
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: '500',
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                }}
              >
                Username or Email
              </label>
              <div style={{ position: 'relative' }}>
                <User
                  size={16}
                  style={{
                    position: 'absolute',
                    left: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                />
                <input
                  type="text"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="admin@nexvault.io or demo@nexvault.io"
                  style={{
                    width: '100%',
                    height: '42px',
                    padding: '0 12px 0 38px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <div>
              <label
                style={{
                  display: 'block',
                  fontSize: '12px',
                  fontWeight: '500',
                  color: 'var(--text-secondary)',
                  marginBottom: '8px',
                }}
              >
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock
                  size={16}
                  style={{
                    position: 'absolute',
                    left: '12px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    color: 'var(--text-muted)',
                  }}
                />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="admin123 or demo123"
                  style={{
                    width: '100%',
                    height: '42px',
                    padding: '0 12px 0 38px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--border-medium)',
                    borderRadius: '8px',
                    color: 'var(--text-main)',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              icon={ArrowRight}
              iconPosition="right"
              style={{ marginTop: '8px' }}
            >
              Sign In
            </Button>
          </form>

          {/* Quick Demo Access */}
          <div
            style={{
              marginTop: '24px',
              paddingTop: '20px',
              borderTop: '1px solid var(--border-subtle)',
            }}
          >
            <div
              style={{
                fontSize: '11px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                color: 'var(--text-muted)',
                marginBottom: '10px',
                textAlign: 'center',
                fontWeight: '600',
              }}
            >
              Live Evaluation Demo Accounts
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleQuickDemo('ADMIN')}
                disabled={loading}
              >
                Admin (admin@nexvault.io)
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleQuickDemo('USER')}
                disabled={loading}
              >
                User (demo@nexvault.io)
              </Button>
            </div>
          </div>
        </Card>

        {/* Footer Link */}
        <div style={{ textAlign: 'center', marginTop: '20px', fontSize: '13px', color: 'var(--text-secondary)' }}>
          Don't have an account?{' '}
          <Link to="/signup" style={{ color: 'var(--primary-light)', textDecoration: 'none', fontWeight: '500' }}>
            Create one
          </Link>
        </div>
      </div>
    </div>
  );
}
