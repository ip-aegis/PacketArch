/*
 * PacketArch — OT Traffic Simulation Platform
 * Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
 * Licensed under GPL-3.0. See LICENSE at the repo root.
 */
import React from 'react';
import { Empty, Typography, Button, Space } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { TEXT_PARAGRAPH, TEXT_MUTED } from '../../constants/theme';
import { getArticle } from '../../content/help';

const { Text } = Typography;

export interface EmptyStateAction {
  label: string;
  icon?: React.ReactNode;
  primary?: boolean;
  onClick?: () => void;
  /** Route to navigate to. Ignored if onClick is provided. */
  to?: string;
}

export interface EmptyStateProps {
  /** Icon rendered at 48px. Pass a bare icon element (e.g. <ExperimentOutlined />) */
  icon?: React.ReactNode;
  /** Primary message (13px, TEXT_PARAGRAPH color) */
  message: string;
  /** Optional secondary hint (11px, TEXT_MUTED color) */
  hint?: string;
  /** Action buttons. First with primary=true gets primary styling. */
  actions?: EmptyStateAction[];
  /** Help article ID — renders a "Learn more" link under the actions. */
  helpArticleId?: string;
  /** Top margin in px. Default: 60 */
  marginTop?: number;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon,
  message,
  hint,
  actions,
  helpArticleId,
  marginTop = 60,
}) => {
  const navigate = useNavigate();
  const helpArticle = helpArticleId ? getArticle(helpArticleId) : undefined;

  return (
    <Empty
      image={
        icon ? (
          <span style={{ fontSize: 48, color: '#4a6a8a' }}>{icon}</span>
        ) : (
          Empty.PRESENTED_IMAGE_SIMPLE
        )
      }
      description={
        <div>
          <Text style={{ fontSize: 13, color: TEXT_PARAGRAPH }}>
            {message}
          </Text>
          {hint && (
            <div style={{ marginTop: 8 }}>
              <Text style={{ fontSize: 11, color: TEXT_MUTED }}>
                {hint}
              </Text>
            </div>
          )}
          {actions && actions.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Space wrap>
                {actions.map((action, idx) => (
                  <Button
                    key={idx}
                    type={action.primary ? 'primary' : 'default'}
                    icon={action.icon}
                    onClick={() => {
                      if (action.onClick) action.onClick();
                      else if (action.to) navigate(action.to);
                    }}
                  >
                    {action.label}
                  </Button>
                ))}
              </Space>
            </div>
          )}
          {helpArticle && (
            <div style={{ marginTop: actions && actions.length > 0 ? 12 : 16 }}>
              <Button
                type="link"
                size="small"
                icon={<QuestionCircleOutlined />}
                onClick={() => navigate(`/help/${helpArticleId}`)}
                style={{ padding: 0, fontSize: 12 }}
              >
                Learn more: {helpArticle.title}
              </Button>
            </div>
          )}
        </div>
      }
      style={{ marginTop }}
    />
  );
};

export default EmptyState;
