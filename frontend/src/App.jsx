import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/common/ProtectedRoute';

// Auth Pages
import Login from './pages/auth/Login';
import Signup from './pages/auth/Signup';

// User Pages
import UserDashboard from './pages/user/Dashboard';
import MyStorage from './pages/user/MyStorage';
import Buckets from './pages/user/Buckets';
import Transfers from './pages/user/Transfers';

// Admin Pages
import ClusterOverview from './pages/admin/ClusterOverview';
import Nodes from './pages/admin/Nodes';
import Replication from './pages/admin/Replication';
import Integrity from './pages/admin/Integrity';
import Repairs from './pages/admin/Repairs';
import Rebalancing from './pages/admin/Rebalancing';
import Metrics from './pages/admin/Metrics';
import LiveEvents from './pages/admin/LiveEvents';
import ChaosLab from './pages/admin/ChaosLab';

function RootRedirect() {
  const { user, isAdmin } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={isAdmin ? "/admin/overview" : "/user/dashboard"} replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* Public Auth Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />

            {/* Authenticated Root Application Shell */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route index element={<RootRedirect />} />

                {/* USER Routes */}
                <Route path="user/dashboard" element={<UserDashboard />} />
                <Route path="user/storage" element={<MyStorage />} />
                <Route path="user/buckets" element={<Buckets />} />
                <Route path="user/transfers" element={<Transfers />} />

                {/* ADMIN Protected Routes */}
                <Route element={<ProtectedRoute requireAdmin />}>
                  <Route path="admin/overview" element={<ClusterOverview />} />
                  <Route path="admin/nodes" element={<Nodes />} />
                  <Route path="admin/replication" element={<Replication />} />
                  <Route path="admin/integrity" element={<Integrity />} />
                  <Route path="admin/repairs" element={<Repairs />} />
                  <Route path="admin/rebalancing" element={<Rebalancing />} />
                  <Route path="admin/metrics" element={<Metrics />} />
                  <Route path="admin/events" element={<LiveEvents />} />
                  <Route path="admin/chaos" element={<ChaosLab />} />
                </Route>
              </Route>
            </Route>

            {/* Catch-all fallback */}
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
