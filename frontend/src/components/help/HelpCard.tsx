/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
/**
 * HelpCard - Standardized "How X Works" help card component
 *
 * Follows the existing pattern from IPManagementPage
 * for consistent inline help throughout the application.
 */

import React from 'react';
import { Card, Typography, Steps } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

export interface HelpStep {
  title: string;
  description: string;
}

interface HelpCardProps {
  title: string;
  steps: HelpStep[];
  icon?: React.ReactNode;
  style?: React.CSSProperties;
  showIcon?: boolean;
}

const HelpCard: React.FC<HelpCardProps> = ({
  title,
  steps,
  icon,
  style,
  showIcon = true,
}) => {
  return (
    <Card
      style={{
        background: '#1a2734',
        border: '1px solid #2a3f54',
        ...style,
      }}
    >
      <Title
        level={5}
        style={{
          color: '#fff',
          marginBottom: 16,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        {showIcon && (icon || <QuestionCircleOutlined style={{ color: '#049FD9' }} />)}
        {title}
      </Title>
      <Steps
        direction="vertical"
        size="small"
        current={-1}
        items={steps.map((step) => ({
          title: (
            <Text style={{ color: '#fff', fontWeight: 500 }}>
              {step.title}
            </Text>
          ),
          description: (
            <Text style={{ color: '#8aa4bc' }}>
              {step.description}
            </Text>
          ),
          status: 'wait' as const,
        }))}
        style={{
          marginTop: 8,
        }}
      />
    </Card>
  );
};

export default HelpCard;
