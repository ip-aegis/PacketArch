/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * EmptyCanvasOverlay — first-canvas coach mark.
 *
 * Renders centered over the Scenario Studio canvas when a scenario has zero
 * devices. Provides three next steps: drag from the palette, use a template,
 * or generate with AI. Dismissible for the rest of the session.
 */

import React, { useState } from 'react';
import { Card, Typography, Space, Button, Divider } from 'antd';
import {
  DragOutlined,
  CompassOutlined,
  RobotOutlined,
  QuestionCircleOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

const STORAGE_KEY = 'packetarch_studio_onboarding_dismissed';

const EmptyCanvasOverlay: React.FC = () => {
  const navigate = useNavigate();
  const [dismissed, setDismissed] = useState<boolean>(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY) === '1';
    } catch {
      return false;
    }
  });

  const handleDismiss = () => {
    try {
      sessionStorage.setItem(STORAGE_KEY, '1');
    } catch {
      /* sessionStorage unavailable — fall through */
    }
    setDismissed(true);
  };

  if (dismissed) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 5,
        pointerEvents: 'none',
        width: 'min(520px, 90%)',
      }}
    >
      <Card
        style={{
          background: 'rgba(20, 28, 44, 0.96)',
          border: '1px solid #2a3f54',
          boxShadow: '0 12px 40px rgba(0,0,0,0.45)',
          pointerEvents: 'auto',
        }}
        styles={{ body: { padding: 24 } }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={4} style={{ color: '#fff', marginTop: 0, marginBottom: 4 }}>
              This scenario is empty
            </Title>
            <Text style={{ color: '#8aa4bc' }}>
              Pick how you'd like to add devices to start building.
            </Text>
          </div>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={handleDismiss}
            style={{ color: '#6b6b8a' }}
            aria-label="Dismiss"
          />
        </div>

        <Divider style={{ borderColor: '#2a3f54', margin: '16px 0' }} />

        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space align="start">
            <DragOutlined style={{ fontSize: 18, color: '#5a9fd4', marginTop: 2 }} />
            <div>
              <Text strong style={{ color: '#e0e8f0' }}>
                Drag a device from the right panel
              </Text>
              <div>
                <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                  Open the Devices tab on the right, then drag any template onto the canvas.
                </Text>
              </div>
            </div>
          </Space>

          <Space align="start">
            <CompassOutlined style={{ fontSize: 18, color: '#5a9fd4', marginTop: 2 }} />
            <div>
              <Text strong style={{ color: '#e0e8f0' }}>
                Start from a template
              </Text>
              <div>
                <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                  Use the Guided Builder to populate this scenario from an industry template.
                </Text>
              </div>
              <Button
                type="link"
                size="small"
                onClick={() => navigate('/scenarios/guided-builder')}
                style={{ padding: 0, fontSize: 12 }}
              >
                Open Guided Builder →
              </Button>
            </div>
          </Space>

          <Space align="start">
            <RobotOutlined style={{ fontSize: 18, color: '#5a9fd4', marginTop: 2 }} />
            <div>
              <Text strong style={{ color: '#e0e8f0' }}>
                Generate with AI
              </Text>
              <div>
                <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                  Describe the environment in plain English and let Claude wire it up.
                </Text>
              </div>
              <Button
                type="link"
                size="small"
                onClick={() => navigate('/scenarios/ai-create')}
                style={{ padding: 0, fontSize: 12 }}
              >
                Open AI Wizard →
              </Button>
            </div>
          </Space>
        </Space>

        <Divider style={{ borderColor: '#2a3f54', margin: '16px 0 12px' }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button
            type="link"
            size="small"
            icon={<QuestionCircleOutlined />}
            onClick={() => navigate('/help/scenario-studio')}
            style={{ padding: 0, fontSize: 12 }}
          >
            Learn about Scenario Studio
          </Button>
          <Button size="small" onClick={handleDismiss}>
            Got it
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default EmptyCanvasOverlay;
