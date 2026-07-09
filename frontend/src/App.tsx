/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import { Routes, Route, Navigate, useParams, useSearchParams } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import FeatureGate from './components/FeatureGate';
import SetupGate from './components/SetupGate';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ScenarioStudioPage from './pages/ScenarioStudioPage';
import Studio2Page from './studio2/Studio2Page';
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

// Preserve the playbook id when redirecting the old attack-library detail route.
function LegacyAttackDetailRedirect() {
  const { playbookId } = useParams();
  return <Navigate to={`/libraries/attacks/${playbookId}`} replace />;
}

// /studio2 was the v2 preview route; v2 is now the default /studio.
// Preserve ?scenario= for old bookmarks.
function Studio2Redirect() {
  const [searchParams] = useSearchParams();
  const qs = searchParams.toString();
  return <Navigate to={`/studio${qs ? `?${qs}` : ''}`} replace />;
}

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
        {/* Studio v2 is the default; v1 stays reachable while it's driven
            side by side. Old /studio2 preview links redirect. */}
        <Route path="studio" element={<Studio2Page />} />
        <Route path="studio-legacy" element={<ScenarioStudioPage />} />
        <Route path="studio2" element={<Studio2Redirect />} />
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
        {/* Legacy-route redirects (post-consolidation): keep old bookmarks/deep
            links coherent instead of silently dumping them on the dashboard. */}
        <Route path="settings" element={<Navigate to="/admin/settings" replace />} />
        <Route path="cves" element={<Navigate to="/libraries?tab=cves" replace />} />
        <Route path="fingerprints" element={<Navigate to="/libraries?tab=devices" replace />} />
        <Route path="attack-library" element={<Navigate to="/libraries?tab=attacks" replace />} />
        <Route path="attack-library/:playbookId" element={<LegacyAttackDetailRedirect />} />

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
