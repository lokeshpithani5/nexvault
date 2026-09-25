import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import TopNavigation from './TopNavigation';

export default function AppLayout() {
  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-wrapper">
        <TopNavigation />
        <main className="content-scrollable">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
