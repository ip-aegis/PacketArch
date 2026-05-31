/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import FeatureGate from './components/FeatureGate';
import SetupGate from './components/SetupGate';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ScenarioStudioPage from './pages/ScenarioStudioPage';
import ScenariosPage from './pages/ScenariosPage';

import IPManagementPage from './pages/IPManagementPage';
import HelpPage from './pages/HelpPage';
import AIScenarioWizardPage from './pages/AIScenarioWizardPage';
import GuidedBuilderPage from './pages/GuidedBuilderPage';
import CyberVisionPage from './pages/CyberVisionPage';
import LibraryHubPage from './pages/LibraryHubPage';
import SettingsPage from './pages/admin/SettingsPage';
import ArchitectureReferencePage from './pages/ArchitectureReferencePage';
import AttackPlaybookDetailPage from './pages/AttackPlaybookDetailPage';
import AgentsHubPage from './pages/AgentsHubPage';
import LiveTrafficPage from './pages/LiveTrafficPage';

function App() {
  return (
    <SetupGate>
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
        <Route path="devices" element={<Navigate to="/libraries?tab=devices" replace />} />

        <Route
          path="agents"
          element={
            <FeatureGate feature="liveTraffic" fallback="/scenarios">
              <AgentsHubPage />
            </FeatureGate>
          }
        />
        {/* Runtime view: live dashboard + deployments (infrastructure stays in the Agents hub). */}
        <Route
          path="live-traffic"
          element={
            <FeatureGate feature="liveTraffic" fallback="/scenarios">
              <LiveTrafficPage />
            </FeatureGate>
          }
        />
        <Route path="deployments" element={<Navigate to="/live-traffic?tab=deployments" replace />} />
        <Route path="ip-management" element={<IPManagementPage />} />
        <Route path="cyber-vision" element={<CyberVisionPage />} />
        <Route path="help" element={<HelpPage />} />
        <Route path="help/:articleId" element={<HelpPage />} />
        <Route path="architecture" element={<ArchitectureReferencePage />} />
        {/* Consolidated reference libraries: CVEs, Attacks, Device Library */}
        <Route path="libraries" element={<LibraryHubPage />} />
        <Route
          path="libraries/attacks/:playbookId"
          element={<AttackPlaybookDetailPage />}
        />

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
    </SetupGate>
  );
}

export default App;
