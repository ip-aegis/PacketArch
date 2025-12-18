/**
 * Login page component - Cisco inspired dark theme
 */

import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Alert, Space } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import type { LoginCredentials } from '../types';

const { Text } = Typography;

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuthStore();
  const [form] = Form.useForm();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || '/';
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
      const from = (location.state as any)?.from?.pathname || '/';
      navigate(from, { replace: true });
    } catch (err) {
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
          {/* Logo */}
          <div style={{ textAlign: 'center' }}>
            <img
              src="/logo.png"
              alt="Industrial Packet Generator"
              style={{
                maxWidth: 280,
                width: '100%',
                objectFit: 'contain',
              }}
            />
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
          <div
            style={{
              textAlign: 'center',
              paddingTop: 16,
              borderTop: '1px solid #2d2d52',
            }}
          >
            <Text style={{ color: '#6b6b8a', fontSize: 12 }}>
              Default: <span style={{ color: '#a8a8c0' }}>admin</span> / <span style={{ color: '#a8a8c0' }}>changeme123</span>
            </Text>
          </div>
        </Space>
      </Card>

      {/* Version badge */}
      <div
        style={{
          position: 'absolute',
          bottom: 24,
          left: '50%',
          transform: 'translateX(-50%)',
          color: '#6b6b8a',
          fontSize: 11,
          letterSpacing: '0.5px',
        }}
      >
        PacketArch v0.1.0 | Industrial Network Traffic Simulation
      </div>
    </div>
  );
};

export default LoginPage;
