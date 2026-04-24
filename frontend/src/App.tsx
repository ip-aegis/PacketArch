/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import FeatureGate from './components/FeatureGate';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ScenarioStudioPage from './pages/ScenarioStudioPage';
import ScenariosPage from './pages/ScenariosPage';

import DeploymentsPage from './pages/DeploymentsPage';
import IPManagementPage from './pages/IPManagementPage';
import CVEBrowserPage from './pages/CVEBrowserPage';
import HelpPage from './pages/HelpPage';
import AIScenarioWizardPage from './pages/AIScenarioWizardPage';
import GuidedBuilderPage from './pages/GuidedBuilderPage';
import CyberVisionPage from './pages/CyberVisionPage';
import FingerprintingLibraryPage from './pages/FingerprintingLibraryPage';
import LiveTrafficDashboardPage from './pages/LiveTrafficDashboardPage';
import SettingsPage from './pages/admin/SettingsPage';

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected routes with layout */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="dashboard" element={<Navigate to="/" replace />} />
        <Route path="studio" element={<ScenarioStudioPage />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route
          path="scenarios/ai-create"
          element={
            <FeatureGate feature="ai" fallback="/scenarios">
              <AIScenarioWizardPage />
            </FeatureGate>
          }
        />
        <Route path="scenarios/guided-builder" element={<GuidedBuilderPage />} />
        <Route path="devices" element={<Navigate to="/fingerprints" replace />} />

        <Route path="deployments" element={<DeploymentsPage />} />
        <Route path="live-traffic" element={<LiveTrafficDashboardPage />} />
        <Route path="ip-management" element={<IPManagementPage />} />
        <Route path="cves" element={<CVEBrowserPage />} />
        <Route path="cyber-vision" element={<CyberVisionPage />} />
        <Route path="fingerprints" element={<FingerprintingLibraryPage />} />
        <Route path="help" element={<HelpPage />} />
        <Route path="help/:articleId" element={<HelpPage />} />

        {/* Admin routes */}
        <Route
          path="admin/settings"
          element={
            <ProtectedRoute requireAdmin>
              <SettingsPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Catch-all redirect */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
