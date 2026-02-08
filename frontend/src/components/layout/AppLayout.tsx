/**
 * Main application layout with navigation - Cisco inspired dark theme
 */

import React, { useState, useCallback, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Button, Avatar, Dropdown, Space, Typography, Badge, Tooltip } from 'antd';
import type { MenuInfo } from 'rc-menu/lib/interface';
import {
  DashboardOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  BellOutlined,
  DatabaseOutlined,
  FolderOutlined,

  BarChartOutlined,
  CloudServerOutlined,
  GlobalOutlined,
  BugOutlined,
  LockOutlined,
  EyeOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { SearchOutlined } from '@ant-design/icons';
import { healthMonitorApi } from '../../api/healthMonitor';
import { useAuthStore } from '../../stores/authStore';
import { useUIStore } from '../../stores/uiStore';
import ChangePasswordModal from '../modals/ChangePasswordModal';
import AgentVersionBanner from './AgentVersionBanner';
import CommandPalette from '../command-palette/CommandPalette';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { panels, toggleLeftSidebar } = useUIStore();
  const toggleCommandPalette = useUIStore((s) => s.toggleCommandPalette);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [healthAlertCount, setHealthAlertCount] = useState(0);

  // Global Ctrl+K / Cmd+K shortcut for command palette
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleCommandPalette();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleCommandPalette]);

  // Poll health status for notification badge
  useEffect(() => {
    const fetchHealthCount = async () => {
      try {
        const status = await healthMonitorApi.getStatus();
        setHealthAlertCount(status.summary.warning + status.summary.critical);
      } catch {
        // Silently ignore — badge stays at last known count
      }
    };
    fetchHealthCount();
    const interval = setInterval(fetchHealthCount, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Handle menu navigation
  const handleMenuClick = useCallback(
    (info: MenuInfo) => {
      navigate(info.key);
    },
    [navigate]
  );

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/scenarios',
      icon: <FolderOutlined />,
      label: 'Scenarios',
    },
    {
      key: '/devices',
      icon: <DatabaseOutlined />,
      label: 'Device Library',
    },
    {
      key: '/deployments',
      icon: <CloudServerOutlined />,
      label: 'Deployments',
    },
    {
      key: '/live-traffic',
      icon: <BarChartOutlined />,
      label: 'Live Traffic',
    },
    {
      key: '/ip-management',
      icon: <GlobalOutlined />,
      label: 'IP Management',
    },
    {
      key: '/cves',
      icon: <BugOutlined />,
      label: 'CVE Browser',
    },
    {
      key: '/cyber-vision',
      icon: <EyeOutlined />,
      label: 'Cyber Vision',
    },
    {
      key: '/fingerprints',
      icon: <SafetyCertificateOutlined />,
      label: 'Fingerprinting Library',
    },
  ];

  // Add admin menu if user is admin
  if (user?.is_admin) {
    menuItems.push({
      key: '/admin/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    });
  }

  const userMenuItems = [
    {
      key: 'change-password',
      icon: <LockOutlined />,
      label: 'Change Password',
      onClick: () => setPasswordModalOpen(true),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      danger: true,
      onClick: handleLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={!panels.leftSidebarOpen}
        width={panels.leftSidebarWidth}
        theme="dark"
        style={{
          background: '#141428',
          borderRight: '1px solid #2d2d52',
        }}
      >
        {/* Logo Section */}
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: '#0d0d1a',
            borderBottom: '1px solid #2d2d52',
            padding: panels.leftSidebarOpen ? '8px 16px' : '8px',
          }}
        >
          {panels.leftSidebarOpen ? (
            <img
              src="/logo.png"
              alt="Industrial Packet Generator"
              style={{
                maxWidth: '100%',
                maxHeight: 48,
                objectFit: 'contain',
              }}
            />
          ) : (
            <img
              src="/sidebar_icon.png"
              alt="IPG"
              style={{
                width: 32,
                height: 32,
                objectFit: 'contain',
              }}
            />
          )}
        </div>

        <Menu
          mode="inline"
          theme="dark"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            background: 'transparent',
            borderRight: 0,
            marginTop: 8,
          }}
        />

        {/* System Status Indicator */}
        {panels.leftSidebarOpen && (
          <div
            style={{
              position: 'absolute',
              bottom: 16,
              left: 16,
              right: 16,
              padding: '12px 16px',
              background: '#1a1a2e',
              borderRadius: 8,
              border: '1px solid #2d2d52',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: '#6CC04A',
                  boxShadow: '0 0 8px rgba(108, 192, 74, 0.5)',
                }}
              />
              <Text style={{ color: '#6CC04A', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                System Online
              </Text>
            </div>
            <Text style={{ color: '#6b6b8a', fontSize: 10 }}>
              Backend Connected
            </Text>
          </div>
        )}
      </Sider>

      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#0d0d1a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #2d2d52',
            height: 64,
          }}
        >
          <Space>
            <Button
              type="text"
              icon={panels.leftSidebarOpen ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
              onClick={toggleLeftSidebar}
              style={{ color: '#a8a8c0' }}
            />
            <Text style={{ color: '#6b6b8a', fontSize: 12, marginLeft: 8 }}>
              OT Traffic Simulation Platform
            </Text>
          </Space>

          <Space size="large">
            {/* Command Palette trigger */}
            <Tooltip title="Search commands (Ctrl+K)">
              <Button
                type="text"
                icon={<SearchOutlined style={{ fontSize: 16 }} />}
                onClick={toggleCommandPalette}
                style={{ color: '#a8a8c0' }}
              />
            </Tooltip>

            {/* Health Notifications */}
            <Tooltip title={healthAlertCount > 0 ? `${healthAlertCount} agent(s) need attention` : 'All agents healthy'}>
              <Badge count={healthAlertCount} overflowCount={9}>
                <Button
                  type="text"
                  icon={<BellOutlined style={{ fontSize: 18 }} />}
                  style={{ color: healthAlertCount > 0 ? '#fa8c16' : '#a8a8c0' }}
                  onClick={() => navigate('/live-traffic')}
                />
              </Badge>
            </Tooltip>

            {/* User Menu */}
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space
                style={{
                  cursor: 'pointer',
                  padding: '4px 12px',
                  borderRadius: 6,
                  background: '#141428',
                  border: '1px solid #2d2d52',
                }}
              >
                <Avatar
                  size="small"
                  style={{
                    background: 'linear-gradient(135deg, #049FD9 0%, #00BCEB 100%)',
                  }}
                  icon={<UserOutlined />}
                />
                <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
                  <Text style={{ color: '#fff', fontSize: 13 }}>{user?.username}</Text>
                  <Text style={{ color: '#6b6b8a', fontSize: 10 }}>
                    {user?.is_admin ? 'Administrator' : 'User'}
                  </Text>
                </div>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        <AgentVersionBanner />

        <Content
          className="tech-grid-bg"
          style={{
            margin: 0,
            // No padding for studio page to maximize canvas space
            padding: location.pathname === '/studio' ? 0 : 24,
            background: '#1a1a2e',
            height: 'calc(100vh - 64px)',
            overflow: location.pathname === '/studio' ? 'hidden' : 'auto',
          }}
        >
          <Outlet />
        </Content>
      </Layout>

      {/* Change Password Modal */}
      <ChangePasswordModal
        open={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
      />

      {/* Command Palette */}
      <CommandPalette />
    </Layout>
  );
};

export default AppLayout;
