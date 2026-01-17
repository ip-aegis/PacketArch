import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ScenarioStudioPage from './pages/ScenarioStudioPage';
import DeviceLibraryPage from './pages/DeviceLibraryPage';
import ScenariosPage from './pages/ScenariosPage';
import LearningPage from './pages/LearningPage';
import DeploymentsPage from './pages/DeploymentsPage';
import IPManagementPage from './pages/IPManagementPage';
import CVEBrowserPage from './pages/CVEBrowserPage';
import HelpPage from './pages/HelpPage';
import AIScenarioWizardPage from './pages/AIScenarioWizardPage';
import CyberVisionPage from './pages/CyberVisionPage';
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
        <Route path="scenarios/ai-create" element={<AIScenarioWizardPage />} />
        <Route path="devices" element={<DeviceLibraryPage />} />
        <Route path="learning" element={<LearningPage />} />
        <Route path="deployments" element={<DeploymentsPage />} />
        <Route path="ip-management" element={<IPManagementPage />} />
        <Route path="cves" element={<CVEBrowserPage />} />
        <Route path="cyber-vision" element={<CyberVisionPage />} />
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
