/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
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
  QuestionCircleOutlined,
  InfoCircleOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
  RocketOutlined,
} from '@ant-design/icons';
import { SearchOutlined } from '@ant-design/icons';
import { healthMonitorApi } from '../../api/healthMonitor';
import { acknowledgmentsApi } from '../../api/acknowledgments';
import { useAuthStore } from '../../stores/authStore';
import { useUIStore } from '../../stores/uiStore';
import { useFeaturesStore } from '../../stores/featuresStore';
import { useFeatures } from '../../hooks/useFeatures';
import ChangePasswordModal from '../modals/ChangePasswordModal';
import AboutModal from '../modals/AboutModal';
import AcknowledgmentModal from '../modals/AcknowledgmentModal';
import AgentVersionBanner from './AgentVersionBanner';
import CommandPalette from '../command-palette/CommandPalette';
import HelpButton from '../help/HelpButton';
import KeyboardShortcutsModal from '../help/KeyboardShortcutsModal';
import WelcomeTour from '../onboarding/WelcomeTour';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { panels, toggleLeftSidebar } = useUIStore();
  const toggleCommandPalette = useUIStore((s) => s.toggleCommandPalette);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [aboutModalOpen, setAboutModalOpen] = useState(false);
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false);
  const [welcomeOpen, setWelcomeOpen] = useState(false);
  const [ackRequired, setAckRequired] = useState(false);
  const [healthAlertCount, setHealthAlertCount] = useState(0);
  const { liveTrafficEnabled } = useFeatures();

  // Global keyboard shortcuts: Ctrl/Cmd+K for command palette, ? for shortcuts cheatsheet.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        toggleCommandPalette();
        return;
      }
      // "?" opens the shortcuts cheatsheet — but never when typing in an input.
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const t = e.target;
        const typing =
          t instanceof HTMLInputElement ||
          t instanceof HTMLTextAreaElement ||
          (t instanceof HTMLElement && t.isContentEditable);
        if (!typing) {
          e.preventDefault();
          setShortcutsModalOpen(true);
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggleCommandPalette]);

  // Load feature flags once after login so AI-gated UI can hide promptly.
  const loadFeatures = useFeaturesStore((s) => s.load);
  useEffect(() => {
    if (!user) return;
    loadFeatures();
  }, [user, loadFeatures]);

  // First-login welcome tour: gated on User.welcome_seen (server-side), so
  // dismissing it sticks across browsers and devices. Suppressed while the
  // blocking EULA modal is up so users aren't hit with two dialogs at once.
  useEffect(() => {
    if (!user || ackRequired) return;
    if (!user.welcome_seen) {
      setWelcomeOpen(true);
    }
  }, [user, ackRequired]);

  // Check whether the current user has accepted the current EULA / license
  // acknowledgment. Blocking modal shows until they either accept or sign out.
  // The setup wizard records the acceptance server-side as part of its
  // completion transaction; if it set the SETUP_ACK_LOCAL_KEY flag we skip
  // the modal once and clear the flag so subsequent logins still gate
  // normally on /acknowledgments/status.
  useEffect(() => {
    if (!user) return;
    try {
      if (localStorage.getItem('packetarch_setup_ack_recorded') === '1') {
        localStorage.removeItem('packetarch_setup_ack_recorded');
        return;
      }
    } catch {
      /* localStorage unavailable — fall through to the normal check. */
    }
    let cancelled = false;
    acknowledgmentsApi
      .getStatus()
      .then((status) => {
        if (!cancelled && !status.accepted) setAckRequired(true);
      })
      .catch(() => {
        // Fail-open: never lock a user out because this endpoint is down.
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  // Poll health status for notification badge. Health monitor only tracks
  // remote agents — skipped in PCAP-only deployments.
  useEffect(() => {
    if (!liveTrafficEnabled) return;
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
  }, [liveTrafficEnabled]);

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
      key: '/fingerprints',
      icon: <DatabaseOutlined />,
      label: 'Device Library',
    },
    ...(liveTrafficEnabled
      ? [
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
        ]
      : []),
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
      key: '/attack-library',
      icon: <ThunderboltOutlined />,
      label: 'Attack Library',
    },
    {
      key: '/cyber-vision',
      icon: <EyeOutlined />,
      label: 'Cyber Vision',
    },
    {
      key: '/architecture',
      icon: <ApartmentOutlined />,
      label: 'Architecture',
    },
    {
      key: '/help',
      icon: <QuestionCircleOutlined />,
      label: 'Help',
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
      key: 'shortcuts',
      icon: <ThunderboltOutlined />,
      label: 'Keyboard Shortcuts',
      onClick: () => setShortcutsModalOpen(true),
    },
    {
      key: 'welcome-tour',
      icon: <RocketOutlined />,
      label: 'Replay Welcome Tour',
      onClick: () => {
        // Open without resetting welcome_seen — replay is transient; the
        // user has already completed it on this account.
        setWelcomeOpen(true);
      },
    },
    {
      key: 'about',
      icon: <InfoCircleOutlined />,
      label: 'About PacketArch',
      onClick: () => setAboutModalOpen(true),
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
              alt="PacketArch"
              style={{
                maxWidth: '100%',
                maxHeight: 48,
                objectFit: 'contain',
              }}
            />
          ) : (
            <img
              src="/sidebar_icon.png"
              alt="PacketArch"
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

            {/* Help — opens contextual drawer, Shift+click for full page */}
            <HelpButton />

            {/* Health Notifications — agent-only, hidden in PCAP-only builds */}
            {liveTrafficEnabled && (
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
            )}

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

        {liveTrafficEnabled && <AgentVersionBanner />}

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

      {/* About Modal */}
      <AboutModal open={aboutModalOpen} onClose={() => setAboutModalOpen(false)} />

      {/* Keyboard Shortcuts Modal */}
      <KeyboardShortcutsModal
        open={shortcutsModalOpen}
        onClose={() => setShortcutsModalOpen(false)}
      />

      {/* First-login welcome tour */}
      <WelcomeTour open={welcomeOpen} onClose={() => setWelcomeOpen(false)} />

      {/* First-run acknowledgment (blocking) */}
      <AcknowledgmentModal
        open={ackRequired}
        onAccepted={() => setAckRequired(false)}
      />

      {/* Command Palette */}
      <CommandPalette />
    </Layout>
  );
};

export default AppLayout;
