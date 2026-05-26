/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * WelcomeTour — first-login onboarding flow.
 *
 * Shown once per user account (server-side gate via User.welcome_seen).
 * Replayable from the user menu. Skippable from any step.
 */

import React, { useState } from 'react';
import { Modal, Typography, Space, Button, Progress, Tag } from 'antd';
import { authApi } from '../../api/auth';
import useAuthStore from '../../stores/authStore';
import {
  RocketOutlined,
  FolderOutlined,
  CompassOutlined,
  RobotOutlined,
  AppstoreOutlined,
  CloudServerOutlined,
  QuestionCircleOutlined,
  ThunderboltOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;

interface Slide {
  icon: React.ReactNode;
  title: string;
  body: React.ReactNode;
  /** Optional primary CTA shown only on this slide. */
  primaryCta?: { label: string; to: string };
}

const SLIDES: Slide[] = [
  {
    icon: <RocketOutlined style={{ color: '#049FD9' }} />,
    title: 'Welcome to PacketArch',
    body: (
      <Paragraph style={{ color: '#a8a8c0', fontSize: 14, marginBottom: 0 }}>
        PacketArch generates hyper-realistic OT (Operational Technology) network traffic for
        testing, training, and validating ICS security tools like Cisco Cyber Vision. The next
        few slides cover the main concepts — under a minute total.
      </Paragraph>
    ),
  },
  {
    icon: <FolderOutlined style={{ color: '#5a9fd4' }} />,
    title: 'Scenarios are the building block',
    body: (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Paragraph style={{ color: '#a8a8c0', fontSize: 14, marginBottom: 8 }}>
          A scenario describes a simulated OT site: devices, zones, protocols, and the flows
          between them. Each scenario gets its own <Text code>/16</Text> IP range automatically.
        </Paragraph>
        <Paragraph style={{ color: '#a8a8c0', fontSize: 14, marginBottom: 0 }}>
          You'll spend most of your time creating scenarios and either generating PCAPs from
          them or deploying them to a live agent.
        </Paragraph>
      </Space>
    ),
  },
  {
    icon: <AppstoreOutlined style={{ color: '#5a9fd4' }} />,
    title: 'Three ways to build a scenario',
    body: (
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space align="start">
          <RobotOutlined style={{ fontSize: 18, color: '#5a9fd4', marginTop: 2 }} />
          <div>
            <Text strong style={{ color: '#e0e8f0' }}>AI Wizard</Text>{' '}
            <Tag color="blue">Fastest</Tag>
            <div>
              <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                Describe the environment in plain English; Claude generates a full scenario.
              </Text>
            </div>
          </div>
        </Space>
        <Space align="start">
          <CompassOutlined style={{ fontSize: 18, color: '#5a9fd4', marginTop: 2 }} />
          <div>
            <Text strong style={{ color: '#e0e8f0' }}>Guided Builder</Text>{' '}
            <Tag color="cyan">Template-driven</Tag>
            <div>
              <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                Six-step wizard that starts from a vetted industry template you can customize.
              </Text>
            </div>
          </div>
        </Space>
        <Space align="start">
          <FolderOutlined style={{ fontSize: 18, color: '#5a9fd4', marginTop: 2 }} />
          <div>
            <Text strong style={{ color: '#e0e8f0' }}>Scenario Studio</Text>{' '}
            <Tag color="purple">Full control</Tag>
            <div>
              <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
                Visual canvas — drag devices, draw flows, group into zones.
              </Text>
            </div>
          </div>
        </Space>
      </Space>
    ),
    primaryCta: { label: 'Try the AI Wizard', to: '/scenarios/ai-create' },
  },
  {
    icon: <CloudServerOutlined style={{ color: '#52c41a' }} />,
    title: 'Deploy live or generate PCAPs',
    body: (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <Paragraph style={{ color: '#a8a8c0', fontSize: 14, marginBottom: 8 }}>
          From any scenario you can either:
        </Paragraph>
        <div>
          <Text strong style={{ color: '#e0e8f0' }}>→ Generate a PCAP</Text>
          <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
            {' '}— produce a timed capture file you can replay or hand to a tool.
          </Text>
        </div>
        <div>
          <Text strong style={{ color: '#e0e8f0' }}>→ Deploy to an agent</Text>
          <Text style={{ color: '#8aa4bc', fontSize: 12 }}>
            {' '}— run live, perpetually, on a remote network interface. Watch on the Live Traffic page.
          </Text>
        </div>
      </Space>
    ),
  },
  {
    icon: <QuestionCircleOutlined style={{ color: '#fa8c16' }} />,
    title: "If you get stuck",
    body: (
      <Space direction="vertical" size="small" style={{ width: '100%' }}>
        <div>
          <ThunderboltOutlined style={{ color: '#5a9fd4', marginRight: 8 }} />
          <Text style={{ color: '#a8a8c0' }}>
            Press <Text code>?</Text> anywhere for the keyboard shortcut cheatsheet.
          </Text>
        </div>
        <div>
          <ThunderboltOutlined style={{ color: '#5a9fd4', marginRight: 8 }} />
          <Text style={{ color: '#a8a8c0' }}>
            Press <Text code>Ctrl/⌘+K</Text> to open the command palette.
          </Text>
        </div>
        <div>
          <QuestionCircleOutlined style={{ color: '#5a9fd4', marginRight: 8 }} />
          <Text style={{ color: '#a8a8c0' }}>
            Click the <Text code>?</Text> icon in the header for context-aware help.
            Every page has an inline help icon next to its title.
          </Text>
        </div>
        <Paragraph style={{ color: '#8aa4bc', fontSize: 12, marginTop: 12, marginBottom: 0 }}>
          You can replay this tour anytime from the user menu → "Replay Welcome Tour".
        </Paragraph>
      </Space>
    ),
    primaryCta: { label: 'Get started', to: '/scenarios' },
  },
];

interface WelcomeTourProps {
  open: boolean;
  onClose: () => void;
}

const WelcomeTour: React.FC<WelcomeTourProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const setUser = useAuthStore((s) => s.setUser);
  const [step, setStep] = useState(0);
  const slide = SLIDES[step];
  const isLast = step === SLIDES.length - 1;

  const handleClose = () => {
    // Fire-and-forget: server persists welcome_seen for this account so the
    // tour never reappears on future logins (any browser, any device).
    authApi
      .markWelcomeSeen()
      .then((updated) => setUser(updated))
      .catch(() => {
        // Network/auth failure: tour will reappear next login. Acceptable.
      });
    setStep(0);
    onClose();
  };

  const handleNext = () => {
    if (isLast) {
      handleClose();
    } else {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handlePrimaryCta = () => {
    if (slide.primaryCta) {
      handleClose();
      navigate(slide.primaryCta.to);
    }
  };

  const percent = Math.round(((step + 1) / SLIDES.length) * 100);

  return (
    <Modal
      open={open}
      onCancel={handleClose}
      footer={null}
      width={560}
      maskClosable={false}
      styles={{
        content: { background: '#0d0d1a' },
        header: { background: '#0d0d1a', borderBottom: '1px solid #2d2d52' },
        body: { background: '#0d0d1a', padding: '24px 28px' },
      }}
      title={
        <Space>
          {slide.icon}
          <span style={{ color: '#fff' }}>{slide.title}</span>
        </Space>
      }
    >
      <Progress
        percent={percent}
        showInfo={false}
        strokeColor="#049FD9"
        trailColor="#2d2d52"
        size="small"
        style={{ marginBottom: 20 }}
      />

      <div style={{ minHeight: 180, marginBottom: 24 }}>{slide.body}</div>

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Button type="text" onClick={handleClose} style={{ color: '#6b6b8a' }}>
          {isLast ? 'Close' : 'Skip tour'}
        </Button>

        <Space>
          {step > 0 && <Button onClick={handleBack}>Back</Button>}
          {slide.primaryCta && (
            <Button
              type="default"
              icon={<ArrowRightOutlined />}
              onClick={handlePrimaryCta}
            >
              {slide.primaryCta.label}
            </Button>
          )}
          <Button
            type="primary"
            icon={isLast ? <CheckCircleOutlined /> : <ArrowRightOutlined />}
            onClick={handleNext}
          >
            {isLast ? 'Done' : `Next (${step + 2}/${SLIDES.length})`}
          </Button>
        </Space>
      </div>

      <Text
        style={{
          color: '#6b6b8a',
          fontSize: 11,
          display: 'block',
          marginTop: 12,
          textAlign: 'center',
        }}
      >
        Step {step + 1} of {SLIDES.length}
      </Text>
    </Modal>
  );
};

export default WelcomeTour;
