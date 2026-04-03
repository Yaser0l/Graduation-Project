import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './store/AppContext';
import Layout from './components/Layout';

// Pages
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import Diagnostics from './pages/Diagnostics';
import Maintenance from './pages/Maintenance';
import Chat from './pages/Chat';
import ScannerOverlay from './components/ScannerOverlay';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/onboarding" element={<Onboarding />} />
          <Route element={<Layout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/diagnostics" element={<Diagnostics />} />
            <Route path="/maintenance" element={<Maintenance />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="*" element={<Navigate to="/onboarding" replace />} />
          </Route>
        </Routes>
        <ScannerOverlay />
      </BrowserRouter>
    </AppProvider>
  );
}
