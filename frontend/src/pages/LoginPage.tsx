/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * Login page component - Cisco inspired dark theme
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Alert, Space } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import { aboutApi, type AboutResponse } from '../api/about';
import type { LoginCredentials } from '../types';

const { Text } = Typography;

interface LocationState {
  from?: { pathname: string };
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();
  const [form] = Form.useForm();
  const [about, setAbout] = useState<AboutResponse | null>(null);

  // Load product/ownership info for the footer (unauthenticated endpoint).
  useEffect(() => {
    let cancelled = false;
    aboutApi
      .get()
      .then((data) => {
        if (!cancelled) setAbout(data);
      })
      .catch(() => {
        // Footer falls back to static text if the endpoint is unreachable.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as LocationState)?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // Clear error when component unmounts
  useEffect(() => {
    return () => {
      clearError();
    };
  }, [clearError]);

  const handleSubmit = async (values: LoginCredentials) => {
    try {
      await login(values);
      const from = (location.state as LocationState)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch {
      // Error is handled by the store
    }
  };

  return (
    <div
      className="tech-grid-bg"
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 50%, #141428 100%)',
        padding: 24,
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative network lines */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundImage: `
            radial-gradient(ellipse at top left, rgba(4, 159, 217, 0.15) 0%, transparent 50%),
            radial-gradient(ellipse at bottom right, rgba(0, 188, 235, 0.1) 0%, transparent 50%)
          `,
          pointerEvents: 'none',
        }}
      />

      <Card
        style={{
          width: '100%',
          maxWidth: 420,
          background: 'rgba(35, 35, 66, 0.95)',
          backdropFilter: 'blur(10px)',
          border: '1px solid #2d2d52',
          borderTop: '3px solid #049FD9',
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(4, 159, 217, 0.1)',
        }}
        styles={{
          body: { padding: '40px 32px' }
        }}
      >
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          {/* Brand lockup — mark image + HTML wordmark so the text
              stays crisp and readable at the card's compact width. */}
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 14,
              paddingTop: 4,
            }}
          >
            <img
              src="/dashboard_logo.png"
              alt="PacketArch"
              style={{
                width: 110,
                height: 110,
                objectFit: 'contain',
                filter: 'drop-shadow(0 6px 18px rgba(0, 212, 255, 0.18))',
              }}
            />
            <div style={{ textAlign: 'center' }}>
              <div
                style={{
                  fontSize: 36,
                  fontWeight: 700,
                  letterSpacing: '0.5px',
                  background: 'linear-gradient(180deg, #FFFFFF 0%, #C5E6F4 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                  lineHeight: 1.1,
                }}
              >
                PacketArch
              </div>
              <div
                style={{
                  width: '70%',
                  height: 2,
                  margin: '8px auto 10px',
                  background:
                    'linear-gradient(90deg, transparent 0%, rgba(0,212,255,0.9) 30%, rgba(0,212,255,0.9) 70%, transparent 100%)',
                  borderRadius: 1,
                }}
              />
              <div
                style={{
                  color: '#7FB3CE',
                  fontSize: 13,
                  letterSpacing: '2px',
                  textTransform: 'none',
                  marginBottom: 4,
                }}
              >
                OT Traffic Simulation Platform
              </div>
              <div
                style={{
                  color: '#4A7896',
                  fontSize: 9.5,
                  letterSpacing: '2.2px',
                  textTransform: 'uppercase',
                }}
              >
                Protocol Accurate · Vendor Realistic · Attack Ready
              </div>
            </div>
          </div>

          {error && (
            <Alert
              message="Authentication Failed"
              description={error}
              type="error"
              showIcon
              closable
              onClose={clearError}
              style={{
                background: 'rgba(207, 32, 48, 0.1)',
                border: '1px solid rgba(207, 32, 48, 0.3)',
              }}
            />
          )}

          <Form
            form={form}
            name="login"
            onFinish={handleSubmit}
            layout="vertical"
            requiredMark={false}
            style={{ marginTop: 8 }}
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: 'Please enter your username' }]}
            >
              <Input
                prefix={<UserOutlined style={{ color: '#6b6b8a' }} />}
                placeholder="Username"
                size="large"
                autoFocus
                style={{
                  background: '#1a1a2e',
                  border: '1px solid #3d3d6b',
                  borderRadius: 6,
                  height: 48,
                }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: 'Please enter your password' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#6b6b8a' }} />}
                placeholder="Password"
                size="large"
                style={{
                  background: '#1a1a2e',
                  border: '1px solid #3d3d6b',
                  borderRadius: 6,
                  height: 48,
                }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, marginTop: 24 }}>
              <Button
                type="primary"
                htmlType="submit"
                size="large"
                block
                loading={isLoading}
                style={{
                  height: 48,
                  fontSize: 14,
                  fontWeight: 600,
                  background: 'linear-gradient(135deg, #049FD9 0%, #00BCEB 100%)',
                  border: 'none',
                  borderRadius: 6,
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                }}
              >
                {isLoading ? 'Authenticating...' : 'Sign In'}
              </Button>
            </Form.Item>
          </Form>

          {/* Footer info */}
          {import.meta.env.DEV && (
            <div
              style={{
                textAlign: 'center',
                paddingTop: 16,
                borderTop: '1px solid #2d2d52',
              }}
            >
              <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
                Default: <span style={{ color: '#a8a8c0' }}>admin</span> / <span style={{ color: '#a8a8c0' }}>C!sco123</span>
              </Text>
            </div>
          )}
        </Space>
      </Card>

      {/* Footer: version + ownership attribution */}
      <div
        style={{
          position: 'absolute',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          textAlign: 'center',
          color: '#6b6b8a',
          fontSize: 11,
          letterSpacing: '0.5px',
          lineHeight: 1.6,
        }}
      >
        <div>
          {about
            ? `${about.name} v${about.version} | Industrial Network Traffic Simulation`
            : 'PacketArch | Industrial Network Traffic Simulation'}
        </div>
        <div style={{ fontSize: 10, color: '#555577' }}>
          {about
            ? `${about.owner.copyright} <${about.owner.email}> · Licensed under ${about.license.id}`
            : '© 2026 Rocky Smith · Licensed under GPL-3.0'}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
